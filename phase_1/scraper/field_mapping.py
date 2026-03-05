"""
Label-to-field mapping for INDMoney scheme page parsing.
Match page labels (as seen in Fund Overview / Key Facts) to normalized field names.
"""

# Map page label text (substring match) -> list of target fields.
# For "Min Lumpsum/SIP" we extract both min_sip and min_lumpsum from the same value (e.g. "₹100/₹100").
LABEL_TO_FIELDS = {
    "Expense ratio": ["expense_ratio"],
    "expense ratio": ["expense_ratio"],
    "Benchmark": ["benchmark"],
    "benchmark": ["benchmark"],
    "Exit Load": ["exit_load"],
    "exit load": ["exit_load"],
    "Min Lumpsum/SIP": ["min_lumpsum", "min_sip"],
    "Min SIP": ["min_sip"],
    "Min Lumpsum": ["min_lumpsum"],
    "Lock In": ["lock_in"],
    "Lock-in": ["lock_in"],
    "Lock in": ["lock_in"],
    "Risk": ["risk_level"],
    "risk": ["risk_level"],
    "AUM": ["aum"],
    "aum": ["aum"],
    "Inception Date": ["inception_date"],
    "inception date": ["inception_date"],
    "Fund Manager": ["fund_manager"],
    "fund manager": ["fund_manager"],
    "TurnOver": [],   # optional, skip or add if needed
}

# Fields that expect a single value (string or number)
SINGLE_VALUE_FIELDS = {
    "expense_ratio", "benchmark", "exit_load", "lock_in", "risk_level",
    "aum", "inception_date", "fund_manager"
}

# Fields that may be parsed from one label (e.g. "₹100/₹100" -> min_lumpsum, min_sip)
SPLIT_VALUE_FIELDS = {"min_sip", "min_lumpsum"}

# All normalized field names used in scheme record
SCHEME_FIELD_NAMES = [
    "scheme_name", "amc_name", "category", "plan_type", "option_type",
    "expense_ratio", "exit_load", "min_sip", "min_sip_raw", "min_lumpsum", "min_lumpsum_raw",
    "lock_in", "risk_level", "benchmark", "aum", "inception_date", "fund_manager",
    "source_url", "scraped_at",
]
