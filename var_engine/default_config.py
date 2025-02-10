# This file gives all default_data needed
import pandas as pd

# Shock Type Mapping
"""
DEFAULT MAPPING
Type	ShockType
EQ	REL
IR	ABS
CMD	REL
"""
SHOCK_MAPPING = {"EQ": "REL", "IR": "ABS", "CMD": "REL"}

# Historical window
WINDOW = pd.Timedelta(days=365)

# Defautl percentile
PERCENTILE = 0.95

# Adjustemt for returns next to 0
ADJUSTMENT_REL = 1e-6
