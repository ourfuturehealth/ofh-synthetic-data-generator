"""Shared synthetic date and year range constants."""
from datetime import datetime
from dateutil.relativedelta import relativedelta  

SYNTHETIC_YEAR_MIN = 2021
SYNTHETIC_YEAR_MAX = datetime.now().year

# maximum participant age is 94
BIRTH_YEAR_MIN = (datetime.now() - relativedelta(years=94)).year
# ensuring each participant is at least 18 years old
BIRTH_YEAR_MAX = (datetime.now() - relativedelta(years=18)).year

CORE_TIMELINE_YEAR_MIN = 2021
CORE_TIMELINE_YEAR_MAX = datetime.now().year

# SUGGESTED_REFERENCE_YEAR = 3100
SYNTHETIC_DATE_DAY_MIN = 1
SYNTHETIC_DATE_DAY_MAX = 28
