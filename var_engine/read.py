from pathlib import Path
from typing import Union

import pandas as pd


def read_input_file(filepath: Union[str, Path]):
    """
    Read .xlsx input file and returns 4 main dataframes

    Note: Output is untreated raw data
    -----

    List Output:
    ------------

       - MarketData dataframe
       - Mapping MD dataframe (for market data shock)
       - Tree dataframe to build aggregation tree
       - Sensitivities dataframe
    """
    print("\nRead Input File")
    # Check for expected tabs
    xls = pd.ExcelFile(filepath)
    expected_tabs = set(['MD', 'Mapping', 'PF', 'Risk'])
    read_tabs = set(xls.sheet_names)
    assert (
        len(expected_tabs - read_tabs) == 0
    ), f"Missing tabs : {','.join(list(expected_tabs - read_tabs))}"

    # Parse each sheet into a dataframe by name
    market_data_df = pd.read_excel(xls, sheet_name='MD')
    mapping_md_df = pd.read_excel(xls, sheet_name='Mapping')
    tree_df = pd.read_excel(xls, sheet_name='PF')
    sensitivities_df = pd.read_excel(xls, sheet_name='Risk')

    # Checks on MD
    assert "Date" in market_data_df.columns, "'Date' column is missing in 'MD' tab"
    market_data_df["Date"] = pd.to_datetime(market_data_df["Date"])
    market_data_df = market_data_df.set_index('Date', drop=True)
    market_data_df = market_data_df.astype(float, copy=False, errors='raise')

    # Checks on Mapping df
    expected_MD = set(market_data_df.columns)
    assert "Md" in mapping_md_df.columns, "'Md' column is missing in 'Mapping' tab"
    assert "Type" in mapping_md_df.columns, "'Type' column is missing in 'Mapping' tab"
    assert (
        "ShockType" in mapping_md_df.columns
    ), "'ShockType' column is missing in 'Mapping' tab"
    mapping_md_df = mapping_md_df.fillna("")
    mapping_md_df = mapping_md_df.astype(str, copy=False, errors='raise')
    mapping_md_df = mapping_md_df.set_index("Md", drop=True)
    read_MD = set(mapping_md_df.index)
    assert (
        len(expected_MD - read_MD) == 0
    ), f"Missing market data: {','.join(list(expected_MD - read_MD))}"

    # Checks on PF
    assert "NodeName" in tree_df.columns, "'NodeName' column is missing in 'PF' tab"
    assert "Parent" in tree_df.columns, "'Parent' column is missing in 'PF' tab"
    assert "Child" in tree_df.columns, "'Child' column is missing in 'PF' tab"
    for col in ("NodeName", "Parent", "Child"):
        tree_df[col] = tree_df[col].fillna("").astype(str, copy=False, errors='raise')

    # Checks on Risk
    read_nodename = set(tree_df.NodeName.unique())
    read_MD = set(market_data_df.columns)
    assert (
        "NodeName" in sensitivities_df.columns
    ), "'NodeName' column is missing in 'Risk' tab"
    assert "RF" in sensitivities_df.columns, "'RF' column is missing in 'Risk' tab"
    assert "Type" in sensitivities_df.columns, "'Type' column is missing in 'Risk' tab"
    assert "Val" in sensitivities_df.columns, "'Val' column is missing in 'Risk' tab"
    sensitivities_df["Val"] = sensitivities_df["Val"].astype(float)
    for col in ('NodeName', 'RF', 'Type'):
        sensitivities_df[col] = sensitivities_df[col].fillna("").astype(str)
    expected_nodename = set(sensitivities_df.NodeName.unique())
    assert (
        len(expected_nodename - read_nodename) == 0
    ), f"Missing Node: {','.join(list(expected_nodename - read_nodename))} in PF tab"
    expected_md = set(sensitivities_df.RF.unique())
    assert (
        len(expected_md - read_MD) == 0
    ), f"Missing Node: {','.join(list(expected_md - read_MD))} in  tab MD"

    print("\tAll checks passed, data successfully read.")
    return market_data_df, mapping_md_df, tree_df, sensitivities_df
