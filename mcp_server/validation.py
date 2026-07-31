from jsonschema import validate, ValidationError

# Strict JSON Schema for budget update requests
BUDGET_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_id": {
            "type": "integer",
            "minimum": 1
        },
        "new_daily_limit": {
            "type": "number",
            "minimum": 10.0,
            "maximum": 10000.0
        },
        "currency": {
            "type": "string",
            "enum": ["USD", "EUR", "GBP"]
        }
    },
    "required": ["campaign_id", "new_daily_limit", "currency"],
    "additionalProperties": False
}

def validate_budget_update_payload(payload: dict) -> tuple[bool, str]:
    """
    Validates tool execution parameters against strict schema guardrails.
    Returns (True, "") if valid, or (False, error_message) if invalid.
    """
    try:
        validate(instance=payload, schema=BUDGET_UPDATE_SCHEMA)
        return True, ""
    except ValidationError as err:
        return False, f"Defensive Validation Error: {err.message}"