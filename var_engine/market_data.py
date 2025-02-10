from datetime import datetime

import pandas as pd
import pandas_market_calendars as mcal
from dateutil.parser import parse

from var_engine.default_config import ADJUSTMENT_REL, SHOCK_MAPPING
from var_engine.model import RiskFactor


def generate_shock(s: pd.Series, is_rel=False):
    df = pd.DataFrame(s)
    df = df.sort_index(ascending=False)
    df.columns = ["value"]
    df["shift"] = df["value"].shift(-1)
    df["new_value"] = df["value"] - df["shift"]
    if is_rel:
        df.loc[df["shift"] == 0.0, "shift"] = (
            df.loc[df["shift"] == 0.0, "shift"] + ADJUSTMENT_REL
        )
        df["new_value"] = df["new_value"] / df["shift"]
    return df["new_value"]


def prepare_market_data(
    df_md: pd.DataFrame,
    df_mapping: pd.DataFrame,
    current_date: str = datetime.now().strftime("%Y-%m-%d"),
):
    print("\nPrepare Market Data")
    # Output
    dict_res = {}

    # Parse current date
    current_date = parse(current_date, dayfirst=True)

    # Parse index min date
    current_index = df_md.index.to_list()
    min_date = min(current_index)

    # Generate dates from start to end
    lse = mcal.get_calendar("LSE")
    early = lse.schedule(
        start_date=min_date.strftime("%Y-%m-%d"),
        end_date=current_date.strftime("%Y-%m-%d"),
    )

    new_date_list = mcal.date_range(early, frequency='1D')

    df_md = pd.DataFrame(new_date_list.tz_localize(None).date).set_index(0).join(df_md)

    for rf_name in df_md.columns:
        print("\tTreating ", rf_name)

        # Forward fill (flat interpolation)
        df_md["quality"] = 1
        df_md.loc[df_md[rf_name].isna(), "quality"] = 0
        df_md[rf_name] = df_md[rf_name].ffill()
        original_serie = df_md[rf_name]

        # Define the type of returns computation
        type_of_product = df_mapping.loc[rf_name].Type
        shock_type = df_mapping.loc[rf_name].ShockType

        if shock_type not in ("REL", "ABS"):
            print("\t\tUsing default value for ", type_of_product)
            shock_type = SHOCK_MAPPING[type_of_product]

        # Compute the returns
        is_rel_flag = True if shock_type == "REL" else False
        rf_serie = generate_shock(original_serie, is_rel_flag)

        # Create the RiskFactor Object
        rf_dataframe = pd.DataFrame(rf_serie).join(df_md[[rf_name, "quality"]])
        rf_dataframe.columns = ["returns", "market_data", "quality"]
        rf_object = RiskFactor(rf_name, rf_dataframe, type_of_product, shock_type)

        # Add to output dictionnary
        dict_res[rf_name] = rf_object

    # Output
    return dict_res
