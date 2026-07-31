import jsonschema

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
    "required": ["campaign_id", "new_daily_limit"],
    "additionalProperties": False  # Blocks unexpected extra fields
}

def validate_budget_update_payload(payload: dict) -> tuple[bool, str]:
    """Validates payload against BUDGET_UPDATE_SCHEMA."""
    try:
        jsonschema.validate(instance=payload, schema=BUDGET_UPDATE_SCHEMA)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, e.message
    except jsonschema.SchemaError as e:
        return False, f"Schema error: {e.message}"