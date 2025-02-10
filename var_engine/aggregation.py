from typing import Dict, Type

import pandas as pd

from var_engine.model import Graph, Node, RiskFactor, Sensitivity
from var_engine.utils import limit_recursion


@limit_recursion(limit=100)  # To protect the code
def __recursive_read(row, records, layers, current_layer: str = "L1"):
    # Read parameters
    nb = int(current_layer[1:])
    nodename = row["NodeName"]

    if current_layer not in layers.keys():
        layers[current_layer] = {}

    # Recursion
    if ''.join(row["Child"]) != '':  # If children i.e not leaf
        for child_name in row["Child"]:
            child_row = [_r for _r in records if _r["NodeName"] == child_name][0]
            __recursive_read(child_row, records, layers, current_layer=f"L{nb+1}")
    layers[current_layer][nodename] = row["Child"]
    return layers


def __parse_tree_structure(df: pd.DataFrame) -> dict:
    """
    Parse a dataframe and extract tree structure

    Input expected:

    NodeName    Parent  Child
    N1          N2
    N2          N1      N5
    N2          N1      N6
    N3          N1      N7
    N3          N1      N8
    N3          N1      N9
    N4          N2      N10
    N5          N2
    N6          N2
    N7          N3
    N8          N3
    N9          N3
    N10         N4

    Output expected:

    {
        "L4":{
            N10:[""],
        },
        "L3":{
            N4:["N10"],
            N5:[""],
            N6:[""],
            N7:[""],
            N8:[""],
            N9:[""],
        },
        "L2":{
            N3:["N7","N8","N9"],
            N2:["N4","N5","N6"]
        },
        "L1":{
            N1:["N2","N3"]
        }
    }
    """
    # Read with children
    df = df.groupby(["NodeName", "Parent"], as_index=False).agg(list)
    dict_records = df.to_dict("records")
    roots = [_r for _r in dict_records if _r["Parent"] == ""]
    assert len(roots) == 1, f"Algorithm needs only one tree, got {len(roots)}"
    root = roots[0]

    layer_tree = __recursive_read(root, dict_records, {})
    layer_tree = dict(sorted(layer_tree.items(), reverse=True))
    return layer_tree


def __create_node_sensitivities(nodename: str, df: pd.DataFrame, market_data: dict):
    df_filter = df.loc[df.NodeName == nodename]
    list_sensi = df_filter.to_dict("records")
    if len(list_sensi) > 0:
        new_sensi = Sensitivity(f"{nodename}_sensibility")
        for sensi in list_sensi:
            dict_metadata = sensi.copy()
            val = sensi["Val"]
            rf = market_data[sensi["RF"]]
            del dict_metadata["NodeName"]
            del dict_metadata["RF"]
            del dict_metadata["Val"]
            new_sensi.add_risk_factor(rf, dict_metadata, val)
    else:
        new_sensi = None

    return new_sensi


def build_aggregation_tree(
    market_data_dict: Dict[str, Type[RiskFactor]],
    tree_df: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
) -> Graph:
    """
    Build the main Graph
    """
    print("\nBuild Aggregation Tree")
    layer_tree: dict = __parse_tree_structure(tree_df)

    dict_nodes = {}
    for layer in layer_tree.keys():
        print("\tTreating layer ", layer)
        for node in layer_tree[layer].items():
            nodename = node[0]
            children = node[1]

            # Sensibilities
            sensibility = __create_node_sensitivities(
                nodename, sensitivity_df, market_data_dict
            )

            # Children
            if "".join(children) != "":  # If there are children
                new_children = []
                for child in children:
                    assert (
                        child in dict_nodes.keys()
                    ), f"{child} not in the construction list, check the layers... (for dev)"  # noqa
                    new_children.append(dict_nodes[child])
                children = new_children
            else:
                children = []

            # Build Node
            new_node = Node(f"{nodename}", children, sensibility)
            dict_nodes[nodename] = new_node

    root = new_node
    new_graph = Graph(f"graph_from_node_{nodename}", root, dict_nodes)

    return new_graph
