"""
AI Service — FastAPI application
defining the enpoints allowed for the web app
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from predict import predict_current, predict_forecast

app = FastAPI(
    title="Aqua AI Service",
    description="Real-time water quality classification and 6-hour forecasting",
    version="1.0.0",
)


#H: request models for input validation and documentation

class SensorReading(BaseModel):
    temp:      float = Field(..., description="Water temperature in °C")
    turbidity: float = Field(..., description="Turbidity in NTU")
    do:        float = Field(..., description="Dissolved oxygen in mg/L")
    ph:        float = Field(..., description="pH level")
    ammonia:   float = Field(..., description="Ammonia in mg/L")
    nitrite:   float = Field(..., description="Nitrite in mg/L")


class HistoryPoint(BaseModel):
    temp:    float
    do:      float
    ph:      float
    ammonia: float


class ForecastRequest(BaseModel):
    history:           List[HistoryPoint] = Field(..., min_length=24, max_length=24,
                                                   description="Last 24 hourly readings")
    current_ammonia:   float
    current_nitrite:   float
    current_turbidity: float
    n_hours:           int = Field(default=6, ge=1, le=12)


#H: api endpoints

@app.get("/health")
def health():
    return {"status": "ok", "service": "Aqua AI"}


@app.post("/predict/current")
def current_status(reading: SensorReading):
    try:
        return predict_current(reading.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/forecast")
def forecast(req: ForecastRequest):
    try:
        data = req.dict()
        data["history"] = [h.dict() for h in req.history]
        return predict_forecast(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))