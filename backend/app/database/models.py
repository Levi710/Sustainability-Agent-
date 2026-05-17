from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database.connection import Base

class BuildingProfile(Base):
    __tablename__ = "building_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), unique=True, index=True)
    building_type = Column(String(50))
    building_name = Column(String(150))
    floors = Column(Integer)
    occupancy_hours = Column(String(50))
    occupancy_peak_days = Column(String(50))
    critical_devices = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    special_constraints = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EnergyUsage(Base):
    __tablename__ = "energy_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    device = Column(String(100))
    timestamp = Column(DateTime)
    kwh = Column(Float)
    tariff_zone = Column(String(20))
    cost = Column(Float)
    is_telemetry = Column(Boolean, default=False)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    device = Column(String(100))
    timestamp = Column(DateTime)
    severity = Column(String(20))
    reason = Column(String(300))
    estimated_loss = Column(Float)
    confidence = Column(Float)
    is_critical_device = Column(Boolean, default=False)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    issue = Column(String(200))
    reason = Column(Text)
    reasoning_proof = Column(Text)
    control_action = Column(String(200))
    estimated_monthly_loss = Column(String(50))
    recommendation = Column(Text)
    projected_savings = Column(Float)
    confidence = Column(Float)
    triggered_by = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    device = Column(String(100))
    timestamp = Column(DateTime)
    kwh = Column(Float)
    event_type = Column(String(50))
    auto_recommendation_fired = Column(Boolean, default=False)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    agent_name = Column(String(100))
    device = Column(String(100), nullable=True)
    action = Column(String(200))
    output = Column(Text)
    details = Column(Text)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DoctorAudit(Base):
    __tablename__ = "doctor_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    device = Column(String(100))
    verification_status = Column(String(50))  # VERIFIED, SUPERFICIAL, FAILED
    doctor_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionReport(Base):
    __tablename__ = "session_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    final_explanation = Column(Text)
    summary_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeviceRegistry(Base):
    """
    IoT Device Registry — The Source of Truth for all connected machines.
    Maps Device IDs to physical locations and metadata.
    """
    __tablename__ = "device_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), unique=True, index=True)  # e.g. 'HVAC_F1_01'
    device_name = Column(String(150))                        # e.g. 'Main HVAC Unit Floor 1'
    category = Column(String(100))                         # e.g. 'HVAC', 'LIGHTING'
    floor = Column(String(50))
    room = Column(String(50))
    is_critical = Column(Boolean, default=False)
    metadata_json = Column(Text)                            # Extra technical specs
