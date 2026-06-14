from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/optimization", tags=["optimization"])


class OptimizationRequest(BaseModel):
    primary_use: str
    square_feet: float
    meter_reading: float
    air_temperature: float


@router.post("/recommend")
async def recommend(req: OptimizationRequest):

    if req.meter_reading > 700:
        action = "reduce_hvac"
        reason = "High energy consumption detected."
    elif req.meter_reading > 400:
        action = "monitor"
        reason = "Consumption slightly elevated."
    else:
        action = "maintain"
        reason = "Consumption within expected range."

    return {
        "action": action,
        "reason": reason,
        "estimated_savings_percent": 12
    }