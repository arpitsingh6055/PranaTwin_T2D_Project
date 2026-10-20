"""Public response contracts, also published through OpenAPI."""

from pydantic import BaseModel
from .model import Packet


class StateResponse(BaseModel):
    glucose: float
    baseline: float
    gut: float
    trend: float
    timestamp: str | None
    last_glucose: str | None
    version: int
    quality: list[str]
    source: str
    observations: int


class ReplayState(BaseModel):
    index: int
    running: bool
    speed: float


class Bookmark(BaseModel):
    label: str
    index: int


class SnapshotResponse(BaseModel):
    state: StateResponse
    replay: ReplayState
    history: list[Packet]
    bookmarks: list[Bookmark]
    total: int
    clock: str


class ForecastPoint(BaseModel):
    timestamp: str
    minute: int
    glucose: float


class Uncertainty(BaseModel):
    status: str
    reason: str


class EventFlags(BaseModel):
    above_180: bool
    below_70: bool


class ForecastResponse(BaseModel):
    points: list[ForecastPoint]
    origin: str
    state_version: int
    unit: str
    model_version: str
    data_age_minutes: float
    uncertainty: Uncertainty
    event_flags: EventFlags
    event_probability: float | None
    probability_status: str
    explanations: list[str]
    calibration: str
    source: str


class ScenarioResponse(BaseModel):
    baseline: ForecastResponse
    alternative: ForecastResponse
    inputs: dict[str, float]
    initial_state: StateResponse
    delta_peak: float
    warning: str
