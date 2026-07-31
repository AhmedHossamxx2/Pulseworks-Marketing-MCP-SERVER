@mcp.prompt("draft_monthly_client_report")
def draft_monthly_client_report(client_name: str, reporting_month: str) -> str:
    """
    Returns a structured prompt template for drafting a monthly marketing performance report.
    """
    return f"""
You are drafting an executive marketing report for **{client_name}** covering **{reporting_month}**.

Please structure the report using the following format:
1. Executive Summary
2. Active Campaigns Performance (Impressions, Clicks, Conversions)
3. Budget Utilization & Spend Analysis
4. Recommendations for Next Month

Ensure all generated ad recommendations adhere to the brand safety guidelines available at `guidelines://brand_safety`.
"""