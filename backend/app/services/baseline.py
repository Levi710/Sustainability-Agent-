import pandas as pd
import numpy as np


def build_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a device-level hourly baseline using mean consumption.

    Input df must have columns: timestamp (datetime), device, kwh
    Returns device-level hourly baseline (average by device+hour+is_weekend).
    """
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6])

    baseline = (
        df.groupby(["device", "hour", "is_weekend"])["kwh"]
        .mean()
        .reset_index()
        .rename(columns={"kwh": "baseline_kwh"})
    )
    return baseline


def merge_with_baseline(df: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """
    Merge raw readings with baseline and compute deviation + z-score.

    Returns the original df with extra columns: baseline_kwh, deviation, z_score.
    """
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["is_weekend"] = df["timestamp"].dt.dayofweek.isin([5, 6])
    merged = df.merge(baseline, on=["device", "hour", "is_weekend"], how="left")
    merged["deviation"] = merged["kwh"] - merged["baseline_kwh"]
    merged["z_score"] = (
        merged["deviation"]
        / merged.groupby("device")["kwh"].transform("std").replace(0, 1)
    )
    return merged
