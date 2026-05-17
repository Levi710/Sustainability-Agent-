"""
Reusable card components for the SustainAI Streamlit dashboard.
"""
import streamlit as st


def metric_card(label: str, value: str, delta: str = "", delta_color: str = "normal", icon: str = ""):
    """Render a styled metric card using st.metric."""
    st.metric(
        label=f"{icon} {label}" if icon else label,
        value=value,
        delta=delta if delta else None,
        delta_color=delta_color,
    )


def recommendation_card(rec: dict, index: int):
    """Render a styled recommendation card."""
    confidence = rec.get("confidence", 0.0)
    conf_pct = int(confidence * 100)
    savings = rec.get("projected_savings") or rec.get("estimated_monthly_loss", "N/A")

    # Severity color based on confidence
    if conf_pct >= 85:
        border_color = "#e74c3c"
        badge_bg = "#c0392b"
    elif conf_pct >= 70:
        border_color = "#f39c12"
        badge_bg = "#d68910"
    else:
        border_color = "#2d9c6e"
        badge_bg = "#1a7a52"

    citation_html = ""
    if rec.get("source_document"):
        citation_html = f"""
    <div style="margin-top:10px; padding:6px 12px; background:rgba(46, 204, 113, 0.08); border: 1px solid rgba(46, 204, 113, 0.2); border-radius:6px; font-size:11px; color:#2ecc71; display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;">
        <span>📖 Grounded Manual: <b>{rec.get('source_document')}</b></span>
        <span>Section: <b>{rec.get('section', 'General')}</b> | Page: <b>{rec.get('page', 'N/A')}</b></span>
    </div>
        """

    st.markdown(f"""
<div style="
    border-left: 4px solid {border_color};
    background: rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-weight:600; font-size:15px; color:#f0f0f0;">
            #{index + 1} {rec.get('issue', rec.get('recommendation', 'Recommendation')[:60])}
        </span>
        <span style="
            background:{badge_bg};
            color:white;
            font-size:11px;
            font-weight:700;
            padding:2px 9px;
            border-radius:12px;
        ">{savings}</span>
    </div>
    <p style="color:#b0b0b0; font-size:13px; margin:4px 0;">
        {rec.get('reason', '')}
    </p>
    <p style="color:#e0e0e0; font-size:13px; margin:4px 0;">
        💡 {rec.get('recommendation', '')}
    </p>
    {citation_html}
    <div style="margin-top:10px; display:flex; align-items:center; gap:10px;">
        <span style="font-size:11px; color:#909090;">AI Confidence: <b>{conf_pct}%</b></span>
        <div style="background:rgba(255,255,255,0.1); border-radius:4px; height:6px; flex-grow:1;">
            <div style="width:{conf_pct}%; background:{border_color}; height:100%; border-radius:4px;"></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def anomaly_badge(severity: str) -> str:
    """Return HTML badge for anomaly severity."""
    colors = {"high": "#e74c3c", "medium": "#f39c12", "low": "#2ecc71"}
    color = colors.get(severity.lower(), "#999")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">{severity.upper()}</span>'


def sustainability_score_ring(score: int):
    """Display a large sustainability score with contextual color."""
    if score >= 75:
        color, label = "#2ecc71", "Excellent"
    elif score >= 50:
        color, label = "#f39c12", "Good"
    elif score >= 25:
        color, label = "#e67e22", "Needs Work"
    else:
        color, label = "#e74c3c", "Critical"

    st.markdown(f"""
<div style="text-align:center; padding:20px 0;">
    <div style="
        display:inline-block;
        width:110px; height:110px;
        border-radius:50%;
        border: 6px solid {color};
        line-height:98px;
        font-size:32px;
        font-weight:800;
        color:{color};
        box-shadow: 0 0 20px {color}44;
    ">{score}</div>
    <p style="color:{color}; font-weight:600; margin-top:8px; font-size:14px;">{label}</p>
    <p style="color:#888; font-size:12px; margin:0;">Sustainability Score</p>
</div>
""", unsafe_allow_html=True)
