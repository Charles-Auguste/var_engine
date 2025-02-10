from pathlib import Path
from typing import Union

import mermaid as mmd
import pandas as pd
import plotly.graph_objects as go


def limit_recursion(limit):
    def inner(func):
        func.count = 0

        def wrapper(*args, **kwargs):
            func.count += 1
            if func.count < limit:
                result = func(*args, **kwargs)
            else:
                raise ValueError("Too much recursive call !")
            func.count -= 1
            return result

        return wrapper

    return inner


def save_mmd(mermaid_graph, save: Union[str, Path] = None):
    try:
        graph = mmd.Mermaid(mmd.Graph("my_graph", mermaid_graph))
        if save:
            graph.to_svg(save)
    except Exception:
        graph = mermaid_graph

    return graph


# Graph


# Define a function to map confidence to color including yellow in the gradient
def confidence_to_color(confidence):
    if confidence < 0.5:
        red = int(255)
        green = int(confidence * 2 * 255)
        blue = int(0)
    else:
        red = int((1 - confidence) * 2 * 255)
        green = int(255)
        blue = int(0)
    return f'rgba({red}, {green}, {blue}, 0.2)'


def plot_VaR(df: pd.DataFrame):
    assert "VaR" in df.columns, "'VaR' column is missing"
    assert "confidence" in df.columns, "'confidence' column is missing"

    # Create the plotly figure
    fig = go.Figure()

    # Add the VaR line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['VaR'],
            mode='lines',
            name='VaR',
            line=dict(color='darkgrey'),
        )
    )

    # Add the colored area
    for i in range(len(df) - 1):
        fig.add_trace(
            go.Scatter(
                x=[df.index[i], df.index[i + 1], df.index[i + 1], df.index[i]],
                y=[df['VaR'][i], df['VaR'][i + 1], 0, 0],
                fill='toself',
                fillcolor=confidence_to_color(df['confidence'][i]),
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=False,
            )
        )

    # Update layout to remove blue background and set dark grey line color
    fig.update_layout(
        title='VaR with Confidence-based Coloring',
        xaxis_title='Date',
        yaxis_title='VaR',
        plot_bgcolor='white',  # Set background color to white
        xaxis=dict(
            showgrid=True, gridcolor='darkgrey'
        ),  # Show dark grid lines for x-axis
        yaxis=dict(
            showgrid=True, gridcolor='darkgrey'
        ),  # Show dark grid lines for y-axis
    )

    # Show the figure
    return fig
