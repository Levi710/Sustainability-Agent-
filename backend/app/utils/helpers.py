"""
General utility helpers for SustainAI backend.
"""
import pandas as pd
from datetime import datetime


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp string to datetime object."""
    return pd.to_datetime(ts_str).to_pydatetime()


def safe_round(value: float, decimals: int = 2) -> float:
    """Safely round a float, handling NaN/None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    return round(float(value), decimals)


def df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to a list of dicts with JSON-safe types."""
    return df.to_dict(orient="records")
