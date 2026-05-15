import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_dataset(filename, devices, start_date, days, normal_range, peak_multiplier=1.2, anomaly_prob=0.01):
    os.makedirs("datasets", exist_ok=True)
    records = []
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        for hour in range(24):
            timestamp = current_date + timedelta(hours=hour)
            for device in devices:
                base_kwh = np.random.uniform(*normal_range)
                
                if 18 <= hour <= 22:
                    kwh = base_kwh * peak_multiplier
                else:
                    kwh = base_kwh
                    
                if np.random.random() < anomaly_prob:
                    kwh = kwh * np.random.uniform(2.5, 4.0)
                    
                records.append({
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:00:00"),
                    "device": device,
                    "kwh": round(kwh, 3),
                    "location": "Main"
                })
                
    df = pd.DataFrame(records)
    filepath = os.path.join("datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Generated {filepath} with {len(df)} rows.")

def main():
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = now - timedelta(days=30)
    
    generate_dataset("college_30days.csv", ["HVAC_Block_A", "Lab_PCs", "Corridor_Lights", "Server_Room_AC", "Canteen_Equipment"], start_date, 30, (1.0, 3.0))
    generate_dataset("house_30days.csv", ["AC", "Geyser", "Washing_Machine", "Refrigerator", "TV"], start_date, 30, (0.2, 1.5))
    generate_dataset("commercial_firm_30days.csv", ["HVAC_Floor1", "HVAC_Floor2", "Workstations", "Server_Room_AC", "Lighting_Main"], start_date, 30, (2.0, 5.0))
    generate_dataset("gov_office_30days.csv", ["HVAC_Main", "HVAC_Server", "Lighting_Floors", "UPS_Bank", "Computers"], start_date, 30, (1.5, 4.0))
    
    # Specific anomaly test scenario
    generate_dataset("scenario_anomaly_test.csv", 
                     ["HVAC_Block_A", "Server_Room_AC", "Corridor_Lights"], 
                     start_date, 30, (1.0, 2.0), 
                     peak_multiplier=1.5, 
                     anomaly_prob=0.05)

if __name__ == "__main__":
    main()
