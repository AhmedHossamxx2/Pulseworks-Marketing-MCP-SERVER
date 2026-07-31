from typing import Dict, Any, Callable


# ======================================================
# 1. Core MCP-style Elicitation Function (Reusable Layer)
# ======================================================

def elicitation_create(
    event_type: str,
    payload: Dict[str, Any],
    input_func: Callable = input,
) -> Dict[str, Any]:
    """
    Generic MCP-style elicitation handler over stdio transport.

    Simulates:
    {
        "type": "elicitation/create",
        "event": event_type,
        "payload": {...}
    }

    Returns structured approval response.
    """

    print("\n" + "=" * 60)
    print(f"⚠️  MCP ELICITATION EVENT: {event_type}")
    print("=" * 60)

    # Print payload بشكل منظم
    for key, value in payload.items():
        print(f"{key:<20}: {value}")

    print("=" * 60)

    # Input validation loop
    while True:
        user_input = input_func("👉 Approve? (yes/no): ").strip().lower()

        if user_input in ("yes", "y"):
            approved = True
            break
        elif user_input in ("no", "n"):
            approved = False
            break
        else:
            print("❌ Invalid input. Please enter 'yes' or 'no'.")

    # Build structured response
    response = {
        "event_type": event_type,
        "approved": approved,
        "approver_id": payload.get("director_id")
        or payload.get("reviewer_id")
        or "unknown_approver",
    }

    # Audit log
    print("\n[AUDIT LOG]")
    print(response)
    print("=" * 60)

    return response


# ======================================================
# 2. Budget Approval (Elicitation Wrapper)
# ======================================================

def request_budget_approval(
    campaign_id: str,
    current_budget: float,
    requested_budget: float,
    currency: str,
    input_func: Callable = input,
) -> Dict[str, Any]:
    """
    Wrapper for budget approval using elicitation_create.
    """

    payload = {
        "campaign_id": campaign_id,
        "current_budget": f"{current_budget:,.2f} {currency}",
        "requested_budget": f"{requested_budget:,.2f} {currency}",
        "reviewer_id": "finance_reviewer_001",
    }

    return elicitation_create(
        event_type="budget_increase_approval",
        payload=payload,
        input_func=input_func,
    )


# ======================================================
# 3. Director Approval for Publishing Creative
# ======================================================

def request_director_approval(
    creative_id: str,
    campaign_id: str,
    director_id: str,
    input_func: Callable = input,
) -> Dict[str, Any]:
    """
    Wrapper for creative publishing approval using elicitation_create.
    """

    payload = {
        "creative_id": creative_id,
        "campaign_id": campaign_id,
        "director_id": director_id,
        "action": "publish_creative_live",
    }

    return elicitation_create(
        event_type="publish_creative_approval",
        payload=payload,
        input_func=input_func,
    )