import pandas as pd

Z_SCORE_THRESHOLD = 2.5


def detect_anomalies(df_with_baseline: pd.DataFrame, critical_devices: list[str]) -> list[dict]:
    """
    Detect anomalous energy readings using z-score thresholding.

    Input: dataframe from merge_with_baseline() with z_score column.
    Returns: list of anomaly dicts.
    """
    anomalies = []
    flagged = df_with_baseline[df_with_baseline["z_score"].abs() > Z_SCORE_THRESHOLD]

    for _, row in flagged.iterrows():
        abs_z = abs(row["z_score"])
        if abs_z > 4:
            severity = "high"
        elif abs_z > 3:
            severity = "medium"
        else:
            severity = "low"
            
        kwh_val = float(row["kwh"])
        base_val = float(row.get("baseline_kwh", 0))
        diff = kwh_val - base_val
        reason = f"Observed {kwh_val:.3f} kWh vs expected {base_val:.3f} kWh (+{diff:.3f} kWh deviation, Z-score: {row['z_score']:.2f})."
        
        is_critical = row["device"] in critical_devices
        if is_critical:
            reason = f"[CRITICAL SYSTEM - PROTECTED] {reason}"

        anomalies.append({
            "device": row["device"],
            "timestamp": row["timestamp"],
            "kwh": round(float(row["kwh"]), 3),
            "baseline_kwh": round(float(row.get("baseline_kwh", 0)), 3),
            "z_score": round(float(row["z_score"]), 2),
            "severity": severity,
            "reason": reason,
            "estimated_loss": round((float(row["kwh"]) - float(row.get("baseline_kwh", 0))) * 6.0, 2),
            "confidence": min(0.99, round(abs_z / 5.0, 2)),
            "is_critical_device": is_critical
        })

    return anomalies
