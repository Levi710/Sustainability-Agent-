"""Pattern agent — wraps detect_habit_patterns for use in the pipeline."""
from app.services.habits import detect_habit_patterns
import pandas as pd


def run(df: pd.DataFrame) -> list[dict]:
    return detect_habit_patterns(df)
