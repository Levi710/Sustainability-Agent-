"""Anomaly agent — wraps detect_anomalies for use in the pipeline."""
from app.services.anomaly import detect_anomalies
import pandas as pd


def run(df_with_baseline: pd.DataFrame) -> list[dict]:
    return detect_anomalies(df_with_baseline)
