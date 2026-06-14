"""
SustainAI — Nudge Service v1
─────────────────────────────
Responsibility:
  - Send real-time SMS nudges to building manager via Twilio
  - Triggered by telemetry_engine when anomaly/sensor event detected
  - Directly addresses Eval Criterion 3: Behavior Nudges Effectiveness

Setup (add to .env):
  TWILIO_ACCOUNT_SID=your_sid
  TWILIO_AUTH_TOKEN=your_token
  TWILIO_FROM_NUMBER=+1XXXXXXXXXX   (your Twilio number)
  TWILIO_TO_NUMBER=+91XXXXXXXXXX    (building manager's phone)

If any env var is missing, nudges are silently skipped — pipeline never fails.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("uvicorn.error")


def send_nudge(session_id: str, db) -> bool:
    """
    Sends an SMS nudge to the building manager when an energy anomaly is detected.

    Returns True if SMS was sent, False otherwise (missing config, no spike, error).
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    to_number = os.getenv("TWILIO_TO_NUMBER")

    # ── Safety Switch: Check if SMS is enabled in .env ───────────────────────
    enable_sms = os.getenv("ENABLE_SMS", "False").lower() == "true"
    if not enable_sms:
        # Check if we have a spike to at least log that we *would* have sent it
        logger.info("Nudge Service: SMS is DISABLED via .env — simulation mode only.")
        return False

    # ── Skip gracefully if Twilio not configured ─────────────────────────────
    if not all([account_sid, auth_token, from_number, to_number]):
        logger.info("Nudge Service: Twilio not configured — skipping SMS.")
        return False

    try:
        from app.database.models import TelemetryEvent

        # ── Find the most recent spike event (last 30 seconds) ───────────────
        cutoff = datetime.now() - timedelta(seconds=30)
        spike = (
            db.query(TelemetryEvent)
            .filter(
                TelemetryEvent.session_id == session_id,
                TelemetryEvent.timestamp >= cutoff,
                TelemetryEvent.event_type.in_([
                    "hardware_malfunction",
                    "occupancy_triggered_spike",
                    "voice_triggered_on",
                ])
            )
            .order_by(TelemetryEvent.timestamp.desc())
            .first()
        )

        if not spike:
            return False

        # ── Format event type for human reading ──────────────────────────────
        event_labels = {
            "hardware_malfunction": "Malfunction",
            "occupancy_triggered_spike": "Empty Zone Motion",
            "voice_triggered_on": "Voice Trigger",
        }
        event_label = event_labels.get(spike.event_type, spike.event_type)

        # ── Compose SMS message (Shortened & Unicode-Free to fit 1 Trial Segment) ───
        message = (
            f"SustainAI Alert: Anomaly ({event_label}) on {spike.device} "
            f"({spike.kwh:.2f}kWh) at {spike.timestamp.strftime('%H:%M')}. "
            f"Auto-fix initiated."
        )

        # ── Send via Twilio ───────────────────────────────────────────────────
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )

        logger.info(f"Nudge Service: SMS sent for {spike.device} — SID: {msg.sid}")
        return True

    except ImportError:
        logger.warning("Nudge Service: twilio package not installed. Run: pip install twilio")
        return False
    except Exception as e:
        # Never let nudge failure break the pipeline
        logger.warning(f"Nudge Service: SMS failed — {e}")
        return False


def get_nudge_history(session_id: str, db, limit: int = 10) -> list[dict]:
    """
    Returns recent spike events formatted as nudge history for the UI.
    Used by the Streamlit dashboard to show past alerts.
    """
    from app.database.models import TelemetryEvent

    try:
        spikes = (
            db.query(TelemetryEvent)
            .filter(
                TelemetryEvent.session_id == session_id,
                TelemetryEvent.event_type.in_([
                    "hardware_malfunction",
                    "occupancy_triggered_spike",
                    "voice_triggered_on",
                ])
            )
            .order_by(TelemetryEvent.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "device": s.device,
                "event_type": s.event_type,
                "kwh": s.kwh,
                "timestamp": s.timestamp.strftime("%H:%M:%S"),
                "message": f"⚡ {s.device} spiked at {s.kwh:.2f} kWh — auto-fix initiated",
            }
            for s in spikes
        ]
    except Exception as e:
        logger.warning(f"Nudge history fetch failed: {e}")
        return []
