from pathlib import Path
from typing import Union

import pandas as pd

from var_engine.aggregation import build_aggregation_tree
from var_engine.market_data import prepare_market_data
from var_engine.model import Graph
from var_engine.read import read_input_file


class VaRStudy:
    def __init__(self, filepath: Union[str, Path]):
        self.filepath = filepath

    def compute(self, start_date: str, end_date: str, window=None, percentile=None):
        """
        Run the VaR model process
        """

        # 1. Data Processing
        (
            market_data_df,
            mapping_market_data_df,
            graph_tree_df,
            sensitivities_df,
        ) = read_input_file(self.filepath)

        # 2. Sensitivity Feeds and Mapping
        market_data_dict = prepare_market_data(market_data_df, mapping_market_data_df)

        # 3. Scenario Generation
        var_tree: Graph = build_aggregation_tree(
            market_data_dict, graph_tree_df, sensitivities_df
        )
        var_tree.set_parameters(percentile, window)

        # 4. PnL aggregation
        print("\nCompute PnL")
        var_tree.root.compute_PnL()  # Lauch PnL computation (maybe time consuming)
        self.var_tree = var_tree  # Save result to the main class

        # 5. VaR calculation
        var: pd.Series = var_tree.compute_VaR_between(
            start_date,
            end_date,
        )

        return var

    def get_graph(self):
        return self.var_tree
