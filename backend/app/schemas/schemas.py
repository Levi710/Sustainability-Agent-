from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EnergyRecord(BaseModel):
    timestamp: datetime
    device: str
    kwh: float
    location: str


class IoTPayload(BaseModel):
    device: str
    timestamp: datetime
    kwh: float
    location: str


class AnomalyOutput(BaseModel):
    device: str
    timestamp: datetime
    severity: str
    reason: str
    estimated_loss: float
    confidence: float


class RecommendationOutput(BaseModel):
    issue: str
    reason: str
    estimated_monthly_loss: str
    recommendation: str
    confidence: float


class SimulationInput(BaseModel):
    device: str
    current_daily_hours: float
    proposed_daily_hours: float
    shift_to_off_peak: bool
    tariff_rate: float


class SimulationOutput(BaseModel):
    device: str
    monthly_savings_inr: float
    cost_reduction_percent: float
    co2_avoided_kg: float
    explanation: str
