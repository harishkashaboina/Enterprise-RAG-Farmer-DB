from typing import Dict, List

# ── View schema registry (used for prompt building & guardrails) ──────────────
VIEWS: Dict[str, Dict] = {
    "vw_booth": {
        "description": "Booth information at the farmers market including price level, type and description.",
        "columns": ["booth_number", "booth_price_level", "booth_description", "booth_type"],
        "sample_questions": ["How many booths are there?", "What booth types exist?"],
    },
    "vw_customer": {
        "description": "Customer details with masked zip codes.",
        "columns": ["customer_id", "customer_first_name", "customer_last_name", "customer_zip_masked"],
        "sample_questions": ["How many customers are registered?", "List customers by first name"],
    },
    "vw_customer_purchases": {
        "description": "Customer purchase transactions including product, vendor, quantity, cost and total.",
        "columns": [
            "product_id", "vendor_id", "market_date", "customer_id",
            "quantity", "cost_to_customer_per_qty", "total_cost", "transaction_time"
        ],
        "sample_questions": [
            "What is the total revenue by vendor?",
            "Which products were purchased most?",
            "Show purchases on a specific date",
        ],
    },
    "vw_market_date_info": {
        "description": "Market calendar with day, week, season, temperature and weather flags.",
        "columns": [
            "market_date", "market_day", "market_week", "market_year",
            "market_start_time", "market_end_time", "market_season",
            "market_min_temp", "market_max_temp", "market_rain_flag", "market_snow_flag"
        ],
        "sample_questions": ["How many market days in 2023?", "Which dates had rain?"],
    },
    "vw_product": {
        "description": "Products with their category names, size and quantity type.",
        "columns": [
            "product_id", "product_name", "product_size",
            "product_qty_type", "product_category_id", "product_category_name"
        ],
        "sample_questions": ["List all products by category", "What fresh produce is available?"],
    },
    "vw_product_category": {
        "description": "Product categories available at the market.",
        "columns": ["product_category_id", "product_category_name"],
        "sample_questions": ["What product categories exist?"],
    },
    "vw_vendor": {
        "description": "Vendor details including name, type and owner information.",
        "columns": [
            "vendor_id", "vendor_name", "vendor_type",
            "vendor_owner_first_name", "vendor_owner_last_name"
        ],
        "sample_questions": ["List all vendors", "How many vendors by type?"],
    },
    "vw_vendor_booth_assignments": {
        "description": "Which vendor is assigned to which booth on each market date.",
        "columns": ["vendor_id", "vendor_name", "booth_number", "market_date"],
        "sample_questions": ["Which booth was vendor X at on date Y?"],
    },
    "vw_vendor_inventory": {
        "description": "Vendor inventory per market date showing product quantities and prices.",
        "columns": [
            "market_date", "vendor_id", "vendor_name",
            "product_id", "product_name", "quantity", "original_price"
        ],
        "sample_questions": ["What inventory did vendor X bring on date Y?", "Cheapest products by vendor"],
    },
    "vw_vendor_market": {
        "description": "Vendor market summary with total amount sold per market date.",
        "columns": [
            "market_date", "market_day", "market_week", "market_year",
            "vendor_id", "vendor_name", "vendor_type", "tot_amt"
        ],
        "sample_questions": ["Top vendors by total sales", "Weekly revenue by vendor type"],
    },
    "vw_zip_data": {
        "description": "Zip code demographic data including income, age distribution and population density.",
        "columns": [
            "zip_code_5", "median_household_income", "percent_high_income",
            "percent_under_18", "percent_over_65", "people_per_sq_mile", "latitude", "longitude"
        ],
        "sample_questions": ["What is the median income for zip 12345?"],
    },
}

ALLOWED_VIEWS: List[str] = list(VIEWS.keys())

def get_schema_prompt() -> str:
    lines = ["=== Farmers Market Database Views ===\n"]
    for view, meta in VIEWS.items():
        lines.append(f"VIEW: {view}")
        lines.append(f"  Description: {meta['description']}")
        lines.append(f"  Columns: {', '.join(meta['columns'])}")
        lines.append("")
    return "\n".join(lines)