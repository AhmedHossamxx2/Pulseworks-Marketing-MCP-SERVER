import logging
from fastmcp import FastMCP, Context
from validation import validate_budget_update_payload
from database import get_db

logger = logging.getLogger("PulseworksMCPServer")

def register_defensive_tools(mcp: FastMCP):
    
    @mcp.tool(
        name="request_budget_update",
        description="Validates, authorizes, and registers a campaign budget update using strict defensive schemas."
    )
    async def request_budget_update(
        campaign_id: int, 
        new_daily_limit: float, 
        currency: str = "USD",
        ctx: Context = None
    ) -> dict:
        
        # Assemble payload for schema validation
        payload = {
            "campaign_id": campaign_id,
            "new_daily_limit": new_daily_limit,
            "currency": currency
        }

        # ----------------------------------------------------------------------
        # LAYER 1: Defensive JSON Schema Validation
        # ----------------------------------------------------------------------
        is_valid, schema_error = validate_budget_update_payload(payload)
        if not is_valid:
            logger.warning("Schema validation failed: %s", schema_error)
            return {
                "status": "REJECTED_BY_SCHEMA_GUARDRAILS",
                "error": "INVALID_PAYLOAD_SCHEMA",
                "reason": schema_error
            }

        # ----------------------------------------------------------------------
        # LAYER 2: Handler-Level Authorization Check
        # ----------------------------------------------------------------------
        # Import session_state here to prevent circular import issues
        from server import session_state
        
        active_role = session_state.get("emp_role_in_campaign", "Viewer")
        if active_role != "Director":
            logger.warning("Unauthorized budget update attempted by role: %s", active_role)
            return {
                "status": "REJECTED_UNAUTHORIZED",
                "error": "FORBIDDEN_ROLE",
                "reason": f"Role '{active_role}' is not authorized to alter campaign budgets. Required role: 'Director'."
            }

        # ----------------------------------------------------------------------
        # LAYER 3: Independent Database State Validation (MySQL)
        # ----------------------------------------------------------------------
        try:
            with get_db() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # Check 3A: Does campaign exist in DB?
                cursor.execute(
                    "SELECT campaign_id, campaign_name, status FROM Campaigns WHERE campaign_id = %s", 
                    (campaign_id,)
                )
                campaign = cursor.fetchone()

                if not campaign:
                    return {
                        "status": "REJECTED_DB_VALIDATION",
                        "error": "CAMPAIGN_NOT_FOUND",
                        "reason": f"Campaign ID {campaign_id} does not exist in the database."
                    }

                # Check 3B: Business Logic Check (Is campaign archived?)
                if campaign["status"] == "archived":
                    return {
                        "status": "REJECTED_BUSINESS_LOGIC",
                        "error": "CAMPAIGN_ARCHIVED",
                        "reason": f"Cannot modify budget for archived campaign '{campaign['campaign_name']}' (ID {campaign_id})."
                    }

                # --------------------------------------------------------------
                # All 3 Layers Passed -> Execute State Change / Return Success
                # --------------------------------------------------------------
                return {
                    "status": "VALIDATED_AND_AUTHORIZED",
                    "campaign_id": campaign_id,
                    "campaign_name": campaign["campaign_name"],
                    "proposed_limit": new_daily_limit,
                    "currency": currency,
                    "authorized_by_role": active_role,
                    "message": "Input passed JSON schema validation, handler role check, and MySQL database verification."
                }

        except Exception as db_err:
            logger.error("Database connection error during budget check: %s", db_err)
            return {
                "status": "ERROR_DATABASE_UNAVAILABLE",
                "reason": f"Database check failed: {str(db_err)}"
            }