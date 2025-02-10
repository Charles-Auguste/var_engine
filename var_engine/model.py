from datetime import timedelta
from typing import Dict, List, Literal, Tuple, Type, Union

import pandas as pd
from dateutil.parser import parse

from var_engine.default_config import PERCENTILE, WINDOW
from var_engine.utils import save_mmd


class RiskFactor:
    def __init__(self, _name, _md_df, _type, _shock_type):
        self.name: str = _name

        # Market Data
        self.MarketD: pd.DataFrame = _md_df

        # Type and Shock type
        self.type: str = _type  # EQ, COM, ...
        self.shock_type: Literal["REL", "ABS"] = _shock_type

    def get_data(self):
        return self.MarketD


class Sensitivity:
    def __init__(self, _name):
        self.name: str = ""

        # Sensitivities
        # Format:
        #    (MarketD, type of sensibility, exposure)
        # Ex:
        #    (MarketD<>, "Delta", 500)
        self.sensitivities: List[Tuple[RiskFactor, dict, float]] = []

    def add_risk_factor(self, rf, dict_metadata, val):
        new_value = [rf, dict_metadata, val]
        self.sensitivities.append(new_value)

    def __str__(self):
        msg = f"Sensitivity: {self.name}\n"
        for sensitivity in self.sensitivities:
            msg += f"- {sensitivity[0].name} --> {sensitivity[2]}\n"
        return msg


class Node:
    def __init__(
        self,
        _name: str,
        _children: list,
        _sensitivities: Sensitivity,
    ):
        self.name: str = _name

        # Profit and Loss Vector
        self.PnL: pd.DataFrame = None

        # Childrens
        self.children: List[Node] = _children

        # Own sensitivities
        self.sensitivities: Sensitivity = _sensitivities

    # Getter
    def get_children(self):
        return self.children

    def get_sensitivity(self):
        return self.sensitivities

    def get_mermaid(self):
        msg = ""
        for child in self.children:
            msg += f"{self.name} --> {child.name}\n"
        return msg

    # Print
    def __str__(self):
        # Name
        msg = f"Node: {self.name}\n"
        # Children
        if len(self.children) > 0:
            msg += "List of children:\n"
            for child in self.children:
                msg += f" - {child.name}\n"
        else:
            msg += "No children\n"
        # Sensitivities
        if not self.sensitivities:
            msg += "No sensitivities\n"
        return msg

    # Computation
    def compute_PnL(self, re_compute: bool = False) -> pd.Series:
        if self.PnL is not None and not re_compute:
            return self.PnL
        else:

            # Take into account its owns sensitivities
            # + the one of its children
            list_PnL = []
            # Own sensitivity part
            if self.sensitivities:
                for sensitivity in self.sensitivities.sensitivities:
                    rf_data = sensitivity[0].get_data()
                    val = sensitivity[2]
                    PnL_data = rf_data
                    PnL_data["PnL"] = PnL_data["returns"] * val
                    PnL_data["qt"] = 1
                    PnL_data = PnL_data.drop(["returns"], axis=1)
                    list_PnL.append(PnL_data)

            # Children part
            for child in self.children:
                list_PnL.append(child.compute_PnL())

            max_len = max([el.shape[0] for el in list_PnL])
            df_PnL_quality = pd.concat(
                [el[["quality"]] for el in list_PnL], axis=1
            ).sum(axis=1)
            df_PnL_value = (
                pd.concat([el[["PnL"]] for el in list_PnL], axis=1)
                .dropna(how='any')
                .sum(axis=1)
            )
            df_PnL_qt = pd.concat([el[["qt"]] for el in list_PnL], axis=1).sum(axis=1)

            df_PnL = pd.concat(
                [df_PnL_value, df_PnL_quality, df_PnL_qt], axis=1
            ).dropna(how='any')

            df_PnL.columns = ["PnL", "quality", "qt"]

            loss_rate = (1 - (df_PnL.shape[0] / max_len)) * 100
            print("\tNode ", self.name, " loss rate : ", loss_rate)

            self.PnL = df_PnL

            return df_PnL


class Graph:
    def __init__(self, _name: str, _root: Node, _nodes: dict):
        self.name: str = ""

        # List of nodes
        self.nodes: Dict[str, Node] = _nodes

        # Root node
        self.root: Node = _root

        # Set default parameters
        self.set_parameters(None, None)

    def set_parameters(self, percentile: float, window: int):
        if percentile:
            msg_alert = "Percentile must be a float between 0 and 1"
            assert isinstance(percentile, float), msg_alert
            assert percentile > 0, msg_alert
            assert percentile < 1, msg_alert
            self.percentile: float = percentile
        else:
            self.percentile: float = PERCENTILE
        if window:
            assert isinstance(
                window, int
            ), "Window parameter must be an int (nb of days)"
            assert window > 1, "Window parameter must be >= 1"
            window = pd.Timedelta(days=window)
            self.window: pd.Timedelta = window
        else:
            self.window = WINDOW

    # Getters
    def get_node(self, name: str) -> Node:
        assert name in self.nodes.keys(), f"{name} not in list of nodes"
        return self.nodes[name]

    def get_root(self):
        return self.root

    # Access Subgraph to compute Var on a smaller level of aggregation
    def get_subgraph_from(self, node: Union[Type[Node], str]):
        # Important if we want to compute the VaR at smaller aggregation levels
        if isinstance(node, str):
            root = self.get_node(node)
        else:
            root = node

        # Build sub-node dict
        list_children = root.get_children().copy()
        memory_temp_1 = list_children
        memory_temp_2 = []
        is_stationnary = False
        iter = 0  # Protection against an infinite loop
        while not is_stationnary and iter <= 1000:
            memory_temp_2 = []
            for child in memory_temp_1:
                memory_temp_2 += child.get_children()
            memory_temp_1 = memory_temp_2
            list_children += memory_temp_2
            if len(memory_temp_1) == 0:
                is_stationnary = True
            iter += 1
        assert iter != 1000, "Graph Fatal error (for dev)"
        dict_nodes = {node.name: node for node in list_children}
        dict_nodes[root.name] = root
        new_name = f"Graph of '{root.name}' from '{self.name}'"
        return Graph(new_name, root, dict_nodes)

    def show_graph(self, save: bool = False):
        mermaid_graph = "graph LR\n"

        # Nodes
        for node_name in self.nodes.keys():
            if self.nodes[node_name].sensitivities:
                msg_style = "with_sensi"
            else:
                msg_style = "without_sensi"
            mermaid_graph += f"{node_name}({node_name}):::{msg_style}\n"

        # Links
        for node in self.nodes.values():
            mermaid_graph += node.get_mermaid()

        # Style
        mermaid_graph += (
            "classDef with_sensi fill:#DDEBF7,stroke-width:2px,stroke:#7AADDC;\n"
        )
        mermaid_graph += (
            "classDef without_sensi fill:#A9D08E,stroke-width:2px,stroke:#548235;\n"
        )

        if save:
            path = f"{self.name.replace(' ','_')}.svg"
        else:
            path = None
        return save_mmd(mermaid_graph, path)

    # VaR computation
    def compute_VaR_on_date(self, date: str):
        # Compute PnL
        assert self.root.PnL is not None, "Compute PnL on root node before !!!!"

        if isinstance(date, str):
            date = parse(date, dayfirst=True)

        # Filter PnL Series on date (with intrapolation)
        # + get previous values according to window
        date += timedelta(days=1)
        PnL_filter = self.root.PnL[
            (self.root.PnL.index <= date) & (self.root.PnL.index > date - self.window)
        ]

        PnL_filter_serie = PnL_filter["PnL"].sort_values(ascending=False)

        if len(PnL_filter_serie) > 1:
            # VaR
            step = 100 / (len(PnL_filter_serie) - 1)
            PnL_filter_serie.index = PnL_filter_serie.reset_index().index * step
            PnL_filter_serie[self.percentile * 100] = None
            PnL_filter_serie = PnL_filter_serie.interpolate(method="index")
            VaR = max(-float(PnL_filter_serie[self.percentile * 100]), 0)

            # Confidence
            confidence_data = float(
                PnL_filter["quality"].sum() / PnL_filter["qt"].sum()
            )
            confidence_size = min(len(PnL_filter_serie), 100) / 100
            confidence = (confidence_data + confidence_size) / 2

        elif len(PnL_filter_serie) > 0:
            VaR = max(-float(PnL_filter_serie.iloc[0]), 0)
            confidence = 0

        else:
            VaR = 0
            confidence = 0

        return VaR, confidence

    def compute_VaR_between(self, start_date: str, end_date: str) -> pd.DataFrame:
        # Compute PnL
        assert self.root.PnL is not None, "Compute PnL on root node before !!!!"

        from_date = parse(start_date, dayfirst=True)
        to_date = parse(end_date)
        assert from_date < to_date, "start date > end date !!!"

        list_of_dates: list = []
        date = from_date
        while date <= to_date:
            list_of_dates.append(date)
            date += timedelta(days=1)

        # Compute VaR using the previous function
        VaR_list = []
        for date in list_of_dates:
            VaR_list.append(self.compute_VaR_on_date(date))

        # Create the serie to return
        VaR_df = pd.DataFrame(VaR_list)
        VaR_df.columns = ["VaR", "confidence"]
        VaR_df["date"] = list_of_dates
        VaR_df = VaR_df.set_index("date")

        return VaR_df
