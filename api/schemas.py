"""Validated completed-cycle summaries, not instantaneous pack measurements."""
from pydantic import BaseModel, ConfigDict, Field, model_validator

class CycleMeasurement(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    cycle: int = Field(ge=1,le=10000)
    capacity_ah: float = Field(gt=0,le=3)
    voltage_mean: float = Field(gt=0,le=5)
    voltage_min: float = Field(ge=0,le=5)
    voltage_max: float = Field(gt=0,le=5)
    voltage_std: float = Field(ge=0,le=3)
    current_mean: float = Field(ge=-10,le=10)
    current_std: float = Field(ge=0,le=10)
    temperature_mean: float = Field(ge=-40,le=100)
    temperature_max: float = Field(ge=-40,le=100)
    temperature_std: float = Field(ge=0,le=60)
    discharge_duration: float = Field(gt=0,le=86400)

    @model_validator(mode='after')
    def sensor_relationships(self):
        if not self.voltage_min<=self.voltage_mean<=self.voltage_max:
            raise ValueError('Voltage minimum <= mean <= maximum is required')
        if self.temperature_mean>self.temperature_max:
            raise ValueError('Temperature maximum cannot be below mean')
        return self

class HistoryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    battery_id: str = Field(default='CUSTOM',min_length=1,max_length=64)
    history: list[CycleMeasurement] = Field(min_length=1,max_length=1000)

    @model_validator(mode='after')
    def ordered_history(self):
        cycles=[x.cycle for x in self.history]
        if any(b!=a+1 for a,b in zip(cycles,cycles[1:])):
            raise ValueError('History must contain consecutive cycles in ascending order')
        return self

class Contribution(BaseModel):
    feature: str
    contribution: float

class Explanation(BaseModel):
    method: str
    base_value: float | None = None
    contributions: list[Contribution]

class SOHResponse(BaseModel):
    forecast_cycle: int
    predicted_soh: float
    current_measured_soh: float
    status: str
    model: str
    sequence_predictions: dict[str,float]
    explanation: Explanation
    uncertainty: str
    input_warnings: list[str]

class RULResponse(BaseModel):
    forecast_cycle: int
    predicted_remaining_cycles: float
    sequence_remaining_cycles: float | None
    trend_cycles: float | None
    slope_ah_per_cycle: float | None
    eol_soh: float
    model: str
    limitations: str
    gaussian_remaining_cycles: float | None = None
    gaussian_predictive_range: dict | None = None

class DischargeSample(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    time_seconds: float = Field(ge=0,le=86400)
    voltage: float = Field(gt=0,le=5)
    current: float = Field(ge=-10,le=10)
    temperature: float = Field(ge=-40,le=100)

class SOCRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    trace: list[DischargeSample] = Field(min_length=2,max_length=2000)

    @model_validator(mode='after')
    def ordered_trace(self):
        times=[x.time_seconds for x in self.trace]
        if times[0]!=0 or any(b<=a for a,b in zip(times,times[1:])):
            raise ValueError('Trace must start at discharge time zero and strictly increase')
        return self

class PlanningRequest(HistoryRequest):
    cycles_per_day: float = Field(default=1,gt=0,le=24,allow_inf_nan=False)

class AnomalyResponse(BaseModel):
    score: float
    status: str
    thresholds: dict[str,float]
    interpretation: str

class AnalysisResponse(BaseModel):
    soh: SOHResponse
    rul: RULResponse
    anomaly: AnomalyResponse
