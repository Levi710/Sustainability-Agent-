"""
Plotly chart functions for SustainAI dashboard.
All charts use transparent background with minimal gridlines (dark Streamlit theme).
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── Design tokens ─────────────────────────────────────────────────────────────
COLOR_GREEN = "#2d9c6e"
COLOR_PEAK = "#e74c3c"
COLOR_SHOULDER = "#f39c12"
COLOR_OFF_PEAK = "#2ecc71"
COLOR_ACCENT = "#3498db"
BG_COLOR = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(255,255,255,0.08)"
FONT_COLOR = "#e0e0e0"

LAYOUT_BASE = dict(
    paper_bgcolor=BG_COLOR,
    plot_bgcolor=BG_COLOR,
    font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def _apply_base_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=title, font=dict(size=14, color=FONT_COLOR)),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, showgrid=True),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, showgrid=True),
    )
    return fig


# ── Chart 1: 30-day daily kWh line chart ─────────────────────────────────────

def usage_line_chart(df: pd.DataFrame) -> go.Figure:
    """30-day daily kWh consumption line chart."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    daily = df.groupby(df["timestamp"].dt.date)["kwh"].sum().reset_index()
    daily.columns = ["date", "kwh"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["kwh"],
        mode="lines+markers",
        name="Daily kWh",
        line=dict(color=COLOR_GREEN, width=2.5),
        marker=dict(size=5, color=COLOR_GREEN),
        fill="tozeroy",
        fillcolor="rgba(45,156,110,0.12)",
    ))
    _apply_base_layout(fig, "Daily Energy Consumption (kWh)")
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="kWh")
    return fig


# ── Chart 2: Hourly usage heatmap ────────────────────────────────────────────

def usage_heatmap(df: pd.DataFrame, device: str) -> go.Figure:
    """Hour × Date heatmap for a specific device."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    device_df = df[df["device"] == device].copy()

    device_df["date"] = device_df["timestamp"].dt.date.astype(str)
    device_df["hour"] = device_df["timestamp"].dt.hour

    pivot = device_df.pivot_table(values="kwh", index="date", columns="hour", aggfunc="sum", fill_value=0)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index.tolist(),
        colorscale="YlOrRd",
        colorbar=dict(title="kWh", tickfont=dict(color=FONT_COLOR)),
        hovertemplate="Hour: %{x}<br>Date: %{y}<br>kWh: %{z:.3f}<extra></extra>",
    ))
    _apply_base_layout(fig, f"{device} — Hourly Usage Heatmap")
    fig.update_xaxes(title_text="Hour of Day", tickfont=dict(size=10))
    fig.update_yaxes(title_text="Date", tickfont=dict(size=9))
    return fig


# ── Chart 3: Anomaly marker chart ────────────────────────────────────────────

def anomaly_chart(df: pd.DataFrame, anomalies: list) -> go.Figure:
    """Line chart with red dots marking anomaly timestamps."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    daily = df.groupby(df["timestamp"].dt.date)["kwh"].sum().reset_index()
    daily.columns = ["date", "kwh"]

    fig = go.Figure()

    # Base line
    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["kwh"],
        mode="lines",
        name="Daily kWh",
        line=dict(color=COLOR_GREEN, width=2),
    ))

    # Anomaly dots
    if anomalies:
        anom_df = pd.DataFrame(anomalies)
        anom_df["timestamp"] = pd.to_datetime(anom_df["timestamp"])
        anom_df["date"] = anom_df["timestamp"].dt.date
        anom_grouped = anom_df.groupby("date")["kwh"].sum().reset_index()

        fig.add_trace(go.Scatter(
            x=anom_grouped["date"],
            y=anom_grouped["kwh"],
            mode="markers",
            name="Anomaly",
            marker=dict(color=COLOR_PEAK, size=10, symbol="circle", line=dict(color="white", width=1)),
        ))

    _apply_base_layout(fig, "Energy Usage with Anomaly Markers")
    return fig


# ── Chart 4: Tariff zone pie chart ───────────────────────────────────────────

def _get_tariff_zone(hour: int) -> str:
    """Inline tariff zone helper (keeps frontend self-contained)."""
    if 18 <= hour < 22:
        return "peak"
    elif hour >= 22 or hour < 6:
        return "off_peak"
    return "shoulder"


def tariff_pie(df: pd.DataFrame) -> go.Figure:
    """Pie chart: peak / shoulder / off-peak kWh distribution."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    if "tariff_zone" not in df.columns:
        df["tariff_zone"] = df["hour"].apply(_get_tariff_zone)

    zone_kwh = df.groupby("tariff_zone")["kwh"].sum()

    labels = zone_kwh.index.tolist()
    values = zone_kwh.values.tolist()

    color_map = {"peak": COLOR_PEAK, "shoulder": COLOR_SHOULDER, "off_peak": COLOR_OFF_PEAK}
    colors = [color_map.get(z, COLOR_GREEN) for z in labels]

    fig = go.Figure(go.Pie(
        labels=[z.replace("_", " ").title() for z in labels],
        values=values,
        marker=dict(colors=colors, line=dict(color="#1a1a2e", width=2)),
        hole=0.4,
        textfont=dict(color=FONT_COLOR),
    ))
    fig.update_layout(**LAYOUT_BASE, title="kWh by Tariff Zone", showlegend=True)
    return fig


# ── Chart 5: Simulation bar chart ────────────────────────────────────────────

def simulation_bar(current: float, projected: float) -> go.Figure:
    """Side-by-side bar: current cost vs projected cost."""
    fig = go.Figure(data=[
        go.Bar(
            x=["Current Cost (₹/mo)", "Projected Cost (₹/mo)"],
            y=[current, projected],
            marker_color=[COLOR_PEAK, COLOR_GREEN],
            width=0.4,
            text=[f"₹{current:,.0f}", f"₹{projected:,.0f}"],
            textposition="outside",
            textfont=dict(color=FONT_COLOR, size=13),
        )
    ])
    _apply_base_layout(fig, "Cost Comparison: Current vs Projected")
    fig.update_yaxes(title_text="₹ / Month")
    return fig


# ── Chart 6: Before/After improvement chart ──────────────────────────────────

def before_after_chart(df: pd.DataFrame) -> go.Figure:
    """Split line chart: first 15 days vs last 15 days of usage."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    df = df.sort_values("timestamp")

    all_dates = sorted(df["date"].unique())
    split = len(all_dates) // 2
    before_dates = all_dates[:split]
    after_dates = all_dates[split:]

    before = df[df["date"].isin(before_dates)].groupby("date")["kwh"].sum().reset_index()
    after = df[df["date"].isin(after_dates)].groupby("date")["kwh"].sum().reset_index()

    # Align on day index for clean comparison
    before["day"] = range(1, len(before) + 1)
    after["day"] = range(1, len(after) + 1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=before["day"], y=before["kwh"],
        mode="lines+markers",
        name="Before (Days 1–15)",
        line=dict(color=COLOR_PEAK, width=2.5),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=after["day"], y=after["kwh"],
        mode="lines+markers",
        name="After (Days 16–30)",
        line=dict(color=COLOR_GREEN, width=2.5),
        marker=dict(size=5),
    ))

    _apply_base_layout(fig, "Behavior Improvement: Before vs After")
    fig.update_xaxes(title_text="Day of Period")
    fig.update_yaxes(title_text="Daily kWh")
    return fig
