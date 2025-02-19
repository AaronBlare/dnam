import plotly.graph_objects as go


def add_scatter_trace(fig, x, y, name, mode='markers', size=8):
    showlegend = False if name == "" else True
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            showlegend=showlegend,
            name=name,
            mode=mode,
            marker=dict(
                size=size,
                opacity=0.7,
                line=dict(
                    width=0.0
                )
            )
        )
    )


