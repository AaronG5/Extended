import os
from math import gcd
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scipy.signal import butter, filtfilt, resample_poly

# ── Load model & encoder once at startup ─────────────────────────────────────
MODEL_PATH   = os.getenv("MODEL_PATH",   "saved_model/model_250hz.json")
ENCODER_PATH = os.getenv("ENCODER_PATH", "saved_model/label_encoder.pkl")

model = XGBClassifier()
model.load_model(MODEL_PATH)
le = joblib.load(ENCODER_PATH)

app = FastAPI(title="Appliance Classifier", version="1.0")

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )


MODEL_FREQ_HZ = int(os.getenv("MODEL_FREQ_HZ", "250"))
MODEL_SOURCE_HZ = int(os.getenv("MODEL_SOURCE_HZ", "250"))
MODEL_IMG_SIZE = int(os.getenv("MODEL_IMG_SIZE", "32"))


def quantized_feature(voltage_cycle: np.ndarray, current_cycle: np.ndarray) -> np.ndarray:
    def quantized_waveform(signal: np.ndarray, n_bins: int = 20) -> np.ndarray:
        max_abs = np.max(np.abs(signal))
        if max_abs <= 1e-12:
            return np.zeros(n_bins, dtype=float)
        normalized = signal / max_abs
        hist, _ = np.histogram(normalized, bins=n_bins, range=(-1, 1))
        hist_sum = hist.sum()
        return hist / hist_sum if hist_sum > 0 else np.zeros(n_bins, dtype=float)

    v_feat = quantized_waveform(voltage_cycle)
    i_feat = quantized_waveform(current_cycle)
    return np.concatenate([v_feat, i_feat])


def vi_image_feature(voltage: np.ndarray, current: np.ndarray, img_size: int = 32) -> np.ndarray:
    vmax = np.max(np.abs(voltage))
    imax = np.max(np.abs(current))
    if vmax <= 1e-12 or imax <= 1e-12:
        return np.zeros((img_size, img_size), dtype=np.uint8)

    v = voltage / vmax
    i = current / imax
    vx = ((v + 1) / 2 * (img_size - 1)).astype(int)
    iy = ((i + 1) / 2 * (img_size - 1)).astype(int)
    vx = np.clip(vx, 0, img_size - 1)
    iy = np.clip(iy, 0, img_size - 1)

    img = np.zeros((img_size, img_size), dtype=np.uint8)
    for idx in range(len(vx) - 1):
        x0, y0 = vx[idx], iy[idx]
        x1, y1 = vx[idx + 1], iy[idx + 1]
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            img[y0, x0] = 1
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
    return img


def extract_cycles(voltage: np.ndarray, current: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
    crossings = np.where((voltage[:-1] <= 0) & (voltage[1:] > 0))[0]
    cycles_v: list[np.ndarray] = []
    cycles_i: list[np.ndarray] = []
    for start, end in zip(crossings[:-1], crossings[1:]):
        seg_v = voltage[start:end + 1]
        seg_i = current[start:end + 1]
        if len(seg_v) > 1 and len(seg_i) > 1:
            cycles_v.append(seg_v)
            cycles_i.append(seg_i)
    return cycles_v, cycles_i


def downsample(voltage: np.ndarray, current: np.ndarray, goal_hz: int, source_hz: int) -> tuple[np.ndarray, np.ndarray]:
    if goal_hz >= source_hz:
        return voltage, current
    nyq = source_hz / 2
    cutoff = goal_hz * 0.45
    b, a = butter(8, cutoff / nyq, btype="low")
    v_filt = filtfilt(b, a, voltage)
    i_filt = filtfilt(b, a, current)
    r = gcd(int(source_hz), int(goal_hz))
    up = int(goal_hz // r)
    down = int(source_hz // r)
    return resample_poly(v_filt, up, down), resample_poly(i_filt, up, down)


def build_features_from_waveforms(
    voltage: np.ndarray,
    current: np.ndarray,
    source_hz: int,
    goal_hz: int,
    img_size: int,
) -> dict[str, float]:
    voltage, current = downsample(voltage, current, goal_hz=goal_hz, source_hz=source_hz)
    cycles_v, cycles_i = extract_cycles(voltage, current)
    if len(cycles_v) < 56:
        raise HTTPException(
            status_code=422,
            detail="Not enough cycles after preprocessing. Need at least 56 positive-going cycles.",
        )

    steady_v = cycles_v[5:55]
    steady_i = cycles_i[5:55]
    all_v = np.concatenate(steady_v)
    all_i = np.concatenate(steady_i)

    image_feature = vi_image_feature(all_v, all_i, img_size=img_size).flatten()
    fixed_len = 10 if goal_hz <= 2000 else int(np.median([len(c) for c in steady_v]))
    fixed_len = max(2, fixed_len)
    x_new = np.linspace(0, 1, fixed_len)
    norm_v = [np.interp(x_new, np.linspace(0, 1, len(c)), c) for c in steady_v]
    norm_i = [np.interp(x_new, np.linspace(0, 1, len(c)), c) for c in steady_i]
    avg_v = np.mean(norm_v, axis=0)
    avg_i = np.mean(norm_i, axis=0)
    quant_feature = quantized_feature(avg_v, avg_i)

    rms_v = float(np.sqrt(np.mean(all_v ** 2)))
    rms_i = float(np.sqrt(np.mean(all_i ** 2)))
    real_power = float(np.mean(all_v * all_i))
    apparent_power = float(rms_v * rms_i)
    power_factor = float(real_power / apparent_power) if apparent_power > 1e-12 else 0.0
    crest_factor = float(np.max(np.abs(all_i)) / rms_i) if rms_i > 1e-12 else 0.0

    features: dict[str, float] = {
        "rms_v": rms_v,
        "rms_i": rms_i,
        "real_power": real_power,
        "apparent_power": apparent_power,
        "power_factor": power_factor,
        "crest_factor": crest_factor,
    }

    for j, val in enumerate(quant_feature):
        features[f"quant_{j}"] = float(val)
    for j, val in enumerate(image_feature):
        features[f"img_{j}"] = float(val)

    return features


def predict_from_features(features: dict[str, float]) -> "PredictResponse":
    df = pd.DataFrame([features])

    # Reorder columns to match training order if the model exposes them
    if hasattr(model, "feature_names_in_"):
        missing = set(model.feature_names_in_) - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing features: {sorted(missing)}",
            )
        df = df[model.feature_names_in_]

    proba = model.predict_proba(df)[0]
    idx = int(np.argmax(proba))
    return PredictResponse(
        label=le.classes_[idx],
        confidence=float(proba[idx]),
        all_probabilities={cls: float(p) for cls, p in zip(le.classes_, proba)},
    )


# ── Schemas ───────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    # Flat dict of feature_name → value, matching the CSV column names
    # e.g. {"rms_v": 120.1, "rms_i": 0.5, "quant_0": 0.02, ..., "img_0": 1, ...}
    features: dict[str, float]


class PredictResponse(BaseModel):
    label: str
    confidence: float
    all_probabilities: dict[str, float]


class ValidationRequest(BaseModel):
    voltage: list[float]
    current: list[float]
    source_hz: int = MODEL_SOURCE_HZ
    target_hz: int = MODEL_FREQ_HZ


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    return predict_from_features(request.features)


@app.post("/validation", response_model=PredictResponse)
def validation(request: ValidationRequest):
    if len(request.voltage) != len(request.current):
        raise HTTPException(status_code=422, detail="voltage and current arrays must have equal length")
    if len(request.voltage) < 100:
        raise HTTPException(status_code=422, detail="Input arrays are too short for cycle extraction")

    voltage = np.asarray(request.voltage, dtype=float)
    current = np.asarray(request.current, dtype=float)
    features = build_features_from_waveforms(
        voltage=voltage,
        current=current,
        source_hz=request.source_hz,
        goal_hz=request.target_hz,
        img_size=MODEL_IMG_SIZE,
    )
    return predict_from_features(features)
