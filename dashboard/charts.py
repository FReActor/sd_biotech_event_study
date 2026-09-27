"""Shared Plotly styling so every chart in the app looks consistent.

Charts follow newspaper conventions: the title and subtitle sit above the
chart (see ui.chart_title), lines are labelled directly instead of with a
legend, and gridlines are faint.
"""

import plotly.graph_objects as go

from data import INK, INK_MUTED, SURFACE

GRID = "rgba(255,255,255,0.08)"
AXIS = "rgba(255,255,255,0.28)"
BAND = "rgba(255,255,255,0.05)"
FONT = "Inter, system-ui, sans-serif"

# Passed to st.plotly_chart: hide the floating Plotly toolbar
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


def style(fig: go.Figure, height: int = 380, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        # keep any right/top margin a chart set for its end labels
        margin=dict(l=4, r=fig.layout.margin.r or 4, t=fig.layout.margin.t or 12, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=AXIS, font=dict(family=FONT, size=12, color=INK)),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
            font=dict(color=INK_MUTED), bgcolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_xaxes(
        showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS, ticklen=4,
        tickfont=dict(color=INK_MUTED, size=12), title_font=dict(color=INK_MUTED, size=12),
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor=GRID, linecolor="rgba(0,0,0,0)", tickfont=dict(color=INK_MUTED, size=12),
        title_font=dict(color=INK_MUTED, size=12), zeroline=True,
        zerolinecolor=AXIS, zerolinewidth=1,
    )
    return fig


def note(fig: go.Figure, x, y, text: str, ax: int = 0, ay: int = -40,
         align: str = "left", arrow: bool = True) -> go.Figure:
    """A newspaper-style annotation: short text with a thin pointer line."""
    fig.add_annotation(
        x=x, y=y, text=text, showarrow=arrow, ax=ax, ay=ay,
        arrowhead=0, arrowwidth=1, arrowcolor=INK_MUTED,
        font=dict(size=12, color=INK), align=align,
        bgcolor="rgba(15,15,14,0.85)",
    )
    return fig


def end_label(fig: go.Figure, x, y, text: str, color: str) -> go.Figure:
    """Label a line at its right end, in place of a legend."""
    fig.add_annotation(
        x=x, y=y, text=f"<b>{text}</b>", showarrow=False, xanchor="left",
        xshift=6, font=dict(size=12, color=color),
    )
    return fig


def shade_windows(fig: go.Figure, windows: dict, labels: bool = True) -> go.Figure:
    """Light bands for the before and after windows, plus a day-0 line."""
    for name, (lo, hi) in windows.items():
        label_args = dict(
            annotation_text=name, annotation_position="top left",
            annotation_font=dict(size=11, color=INK_MUTED),
        ) if labels else {}
        fig.add_vrect(
            x0=lo - 0.5, x1=hi + 0.5, fillcolor=BAND, line_width=0,
            layer="below", **label_args,
        )
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color=INK_MUTED)
    return fig
