BUILDING_BENCHMARKS = {
    "college": {
        "description": "Educational campus with classrooms, labs, hostels, admin blocks",
        "avg_kwh_per_sqft_per_month": 1.8,
        "peak_occupancy_hours": "8AM-8PM weekdays",
        "typical_high_consumption_devices": ["HVAC", "Lab_Equipment", "Computers", "Lighting"],
        "non_negotiable_devices": ["Server_Room_AC", "Security_Systems", "Lab_Servers"],
        "known_waste_patterns": [
            "Labs and classrooms left powered overnight and on weekends",
            "AC running at full capacity in empty rooms between classes",
            "Computers in labs not auto-shutdown after sessions",
            "Lighting in corridors running 24/7 instead of motion-sensor control"
        ],
        "benchmark_sources": "Bureau of Energy Efficiency (BEE) India — Educational Buildings",
        "co2_factor_india": 0.82,
        "typical_monthly_bill_inr_per_sqft": 12.0
    },
    "house": {
        "description": "Residential household — apartments or independent homes",
        "avg_kwh_per_sqft_per_month": 0.9,
        "peak_occupancy_hours": "6AM-10AM, 6PM-11PM",
        "typical_high_consumption_devices": ["AC", "Geyser", "Washing_Machine", "Refrigerator"],
        "non_negotiable_devices": ["Refrigerator", "Medical_Equipment"],
        "known_waste_patterns": [
            "AC left on overnight in empty rooms",
            "Geyser left on all day instead of scheduled heating",
            "Washing machine used during peak tariff hours (6PM-10PM)",
            "Standby power drain from TVs, chargers, set-top boxes overnight"
        ],
        "benchmark_sources": "TERI Residential Energy Consumption Survey 2023",
        "co2_factor_india": 0.82,
        "typical_monthly_bill_inr_per_sqft": 6.5
    },
    "gov_office": {
        "description": "Government office building — secretariat, municipal office, PSU",
        "avg_kwh_per_sqft_per_month": 2.1,
        "peak_occupancy_hours": "9AM-6PM weekdays",
        "typical_high_consumption_devices": ["HVAC", "Lighting", "Computers", "UPS"],
        "non_negotiable_devices": ["Server_Room_AC", "UPS_Systems", "Security_Systems", "Data_Backup_Servers"],
        "known_waste_patterns": [
            "HVAC running on weekends when building is empty",
            "Lights and computers left on overnight — no auto-shutdown policy",
            "Over-cooling common areas to below 24°C (BEE mandates 24-26°C for offices)",
            "Diesel generator running unnecessarily during grid availability"
        ],
        "benchmark_sources": "BEE Energy Conservation Building Code (ECBC) 2017 — Government Buildings",
        "co2_factor_india": 0.82,
        "typical_monthly_bill_inr_per_sqft": 15.0
    },
    "commercial_firm": {
        "description": "Private office, IT company, retail store, or coworking space",
        "avg_kwh_per_sqft_per_month": 2.5,
        "peak_occupancy_hours": "9AM-9PM depending on shifts",
        "typical_high_consumption_devices": ["HVAC", "Servers", "Lighting", "Workstations", "Elevators"],
        "non_negotiable_devices": ["Server_Room_AC", "Network_Equipment", "Security_Systems"],
        "known_waste_patterns": [
            "HVAC set below 22°C — every 1°C below 24°C adds 3-5% to cooling costs",
            "Workstations and monitors left on overnight and weekends",
            "Redundant lighting in meeting rooms and empty floors",
            "Elevator systems not on sleep mode during off-hours"
        ],
        "benchmark_sources": "ASHRAE 90.1, BEE Star Rating for Commercial Buildings",
        "co2_factor_india": 0.82,
        "typical_monthly_bill_inr_per_sqft": 18.0
    },
    "hospital": {
        "description": "Hospital, clinic, or healthcare facility",
        "avg_kwh_per_sqft_per_month": 3.2,
        "peak_occupancy_hours": "24/7 — critical operations never stop",
        "typical_high_consumption_devices": ["HVAC", "Medical_Equipment", "Lighting", "Sterilizers", "Elevators"],
        "non_negotiable_devices": [
            "ICU_AC", "OT_AC", "Medical_Refrigerators", "Ventilators",
            "Sterilizers", "Emergency_Lighting", "Backup_Generators"
        ],
        "known_waste_patterns": [
            "Non-critical area lighting (admin, waiting rooms) left on overnight",
            "HVAC in administrative wings over-cooled vs patient areas",
            "Old MRI/CT equipment with poor energy efficiency vs newer models",
            "Canteen and non-medical equipment during off-peak patient hours"
        ],
        "benchmark_sources": "WHO Healthcare Energy Guidelines, BEE Hospital Energy Audit 2022",
        "co2_factor_india": 0.82,
        "typical_monthly_bill_inr_per_sqft": 25.0
    },
    "data_center": {
        "description": "Data center, server room, or colocation facility",
        "avg_kwh_per_sqft_per_month": 8.5,
        "peak_occupancy_hours": "24/7",
        "typical_high_consumption_devices": ["Server_Racks", "Cooling_Units", "UPS", "Network_Equipment"],
        "non_negotiable_devices": [
            "All_Server_Racks", "All_Cooling_Units", "UPS_Systems",
            "Fire_Suppression", "Security_Systems"
        ],
        "known_waste_patterns": [
            "PUE (Power Usage Effectiveness) above 1.8 — industry best practice is below 1.4",
            "Hot aisle / cold aisle containment not implemented — cooling efficiency drops 30%",
            "Zombie servers (servers using power but running no workloads)",
            "Cooling units running at full capacity regardless of server load"
        ],
        "benchmark_sources": "Green Grid PUE Standard, Uptime Institute Global Data Center Survey 2023",
        "co2_factor_india": 0.82,
        "typical_monthly_bill_inr_per_sqft": 65.0
    }
}

def get_benchmark(building_type: str) -> dict:
    return BUILDING_BENCHMARKS.get(building_type, BUILDING_BENCHMARKS["commercial_firm"])

def get_constraint_prompt_block(profile: dict) -> str:
    """
    Generates the constraint block injected into every LLM prompt.
    This MUST be included in all agent system prompts.
    """
    import json
    benchmark = get_benchmark(profile["building_type"])
    critical_str = profile.get("critical_devices", "[]")
    try:
        critical = json.loads(critical_str)
    except:
        critical = []

    return f"""
=== BUILDING CONTEXT (READ BEFORE ANALYSIS) ===
Building Type: {profile['building_type'].upper()} — {benchmark['description']}
Building Name: {profile.get('building_name', 'Unknown')}
Location: {profile.get('city', 'India')}, {profile.get('state', '')}
Occupancy Pattern: {profile.get('occupancy_hours', benchmark['peak_occupancy_hours'])}
Special Constraints: {profile.get('special_constraints', 'None specified')}

CRITICAL DEVICES (NEVER FLAG THESE AS WASTE — THEY MUST RUN):
{json.dumps(critical + benchmark['non_negotiable_devices'], indent=2)}

DOMAIN BENCHMARKS FOR THIS BUILDING TYPE:
- Expected avg consumption: {benchmark['avg_kwh_per_sqft_per_month']} kWh/sqft/month
- Known waste patterns in this building type:
{chr(10).join(f'  • {p}' for p in benchmark['known_waste_patterns'])}

SOURCE: {benchmark['benchmark_sources']}

ANALYSIS RULES:
1. Any device in the CRITICAL DEVICES list above is informational only — never recommend turning it off or reducing it.
2. Frame all recommendations relative to the occupancy pattern. Usage during non-occupancy hours = waste. Usage during occupancy hours = potentially necessary.
3. Reference the domain benchmarks above when quantifying whether consumption is high or normal.
4. If consumption is within benchmark range, say so explicitly rather than manufacturing a problem.
=== END BUILDING CONTEXT ===
"""
