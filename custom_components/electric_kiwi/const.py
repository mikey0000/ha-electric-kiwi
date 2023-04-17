"""Constants for the Electric Kiwi integration."""

NAME = "Electric Kiwi"
DOMAIN = "electric_kiwi"
ATTRIBUTION = "Data provided by the Juice Hacker API"

OAUTH2_AUTHORIZE = "https://welcome.electrickiwi.co.nz/oauth/authorize"
OAUTH2_TOKEN = "https://welcome.electrickiwi.co.nz/oauth/token"
API_BASE_URL = "https://api.electrickiwi.co.nz"

SCOPE_VALUES = "read_connection_detail read_billing_frequency read_account_running_balance read_consumption_summary read_consumption_averages read_hop_intervals_config read_hop_connection save_hop_connection read_session"


ATTR_TOTAL_RUNNING_BALANCE = "total_running_balance"
ATTR_TOTAL_CURRENT_BALANCE = "total_account_balance"
ATTR_NEXT_BILLING_DATE = "next_billing_date"
ATTR_HOP_PERCENTAGE = "hop_percentage"

ATTR_EK_HOP_SELECT = "hop_select"
ATTR_EK_HOP = "hop_sensor"
