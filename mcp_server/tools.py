from validation import validate_budget_update_payload

@mcp.tool(
    name="request_budget_update",
    description="Validates and registers a campaign budget update request using strict defensive schemas."
)
async def request_budget_update(campaign_id: int, new_daily_limit: float, currency: str = "USD") -> dict:
    payload = {
        "campaign_id": campaign_id,
        "new_daily_limit": new_daily_limit,
        "currency": currency
    }
    
    # Run defensive guardrail checks
    is_valid, error_msg = validate_budget_update_payload(payload)
    if not is_valid:
        return {
            "status": "REJECTED_BY_GUARDRAILS",
            "reason": error_msg
        }

    return {
        "status": "VALIDATED",
        "campaign_id": campaign_id,
        "proposed_limit": new_daily_limit,
        "currency": currency,
        "message": "Input passed defensive validation schemas."
    }