import logging
import asyncio

from fastmcp import FastMCP, Context

from .validation import validate_budget_update_payload
from .database import get_db


logger = logging.getLogger("PulseworksMCPServer")


# ----------------------------------------------------------------------
# 1. REQUEST BUDGET UPDATE TOOL
# ----------------------------------------------------------------------
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

            if campaign["status"] == "archived":
                return {
                    "status": "REJECTED_BUSINESS_LOGIC",
                    "error": "CAMPAIGN_ARCHIVED",
                    "reason": f"Cannot modify budget for archived campaign '{campaign['campaign_name']}' (ID {campaign_id})."
                }

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


# ----------------------------------------------------------------------
# 2. PROGRESS TRACKING TOOL
# ----------------------------------------------------------------------
async def pull_audience_demographics(
    segment_id: str,
    sample_size: int = 1000,
    ctx: Context = None
) -> dict:

    batch_size = 250
    total_fetched = 0

    if sample_size <= 0:
        return {
            "status": "success",
            "segment_id": segment_id,
            "total_records_retrieved": 0,
            "demographic_summary": {},
            "is_long_running": False,
        }

    for start in range(0, sample_size, batch_size):
        await asyncio.sleep(0.4)
        end = min(start + batch_size, sample_size)
        total_fetched = end

        if getattr(ctx, "report_progress", None):
            try:
                await ctx.report_progress(
                    progress=total_fetched,
                    total=sample_size
                )
                await ctx.info(
                    f"Fetched {total_fetched}/{sample_size}"
                )
            except Exception as e:
                logger.warning(f"Progress error: {e}")

    return {
        "status": "success",
        "segment_id": segment_id,
        "total_records_retrieved": total_fetched,
        "demographic_summary": {
            "primary_age_group": "25-34",
            "top_geography": "North America"
        },
        "is_long_running": True,
    }


# ----------------------------------------------------------------------
# 3. SAMPLING TOOL
# ----------------------------------------------------------------------
async def analyze_ad_performance_and_recommend(
    campaign_id: int,
    ctx: Context = None
) -> dict:

    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT campaign_id, campaign_name, budget, status FROM Campaigns WHERE campaign_id = %s",
                (campaign_id,)
            )
            campaign = cursor.fetchone()

            if not campaign:
                return {
                    "status": "error",
                    "message": f"Campaign ID {campaign_id} not found in database."
                }

            campaign_name = campaign["campaign_name"]

    except Exception as db_err:
        logger.error("Database connection error in sampling tool: %s", db_err)
        return {
            "status": "error",
            "message": f"Database error: {str(db_err)}"
        }

    reasoning = "Recommendation: Maintain current daily budget and expand audience targeting."

    if ctx and hasattr(ctx, "session") and ctx.session:
        try:
            response = await ctx.session.create_message(
                messages=[
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Evaluate campaign performance for: {campaign_name}"
                        }
                    }
                ],
                system_prompt="You are a marketing analyst. Provide a 1-sentence budget recommendation.",
                max_tokens=100
            )

            if response and response.content:
                reasoning = response.content.text.strip()

        except Exception as e:
            logger.warning(f"Sampling execution failed, falling back to default reasoning: {e}")

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "recommendation": reasoning
    }


# ----------------------------------------------------------------------
# REGISTRATION FUNCTION
# ----------------------------------------------------------------------
def register_defensive_tools(mcp: FastMCP):
    """Registers all module-level tools onto the FastMCP server instance."""
    
    mcp.tool(
        name="request_budget_update",
        description="Validates, authorizes, and registers a campaign budget update using strict defensive schemas."
    )(request_budget_update)

    mcp.tool(
        name="pull_audience_demographics",
        description="Fetch audience data in batches with real-time progress tracking."
    )(pull_audience_demographics)

    mcp.tool(
        name="analyze_ad_performance_and_recommend",
        description="Fetches campaign metrics from MySQL and invokes LLM sampling to generate strategic recommendations."
    )(analyze_ad_performance_and_recommend)