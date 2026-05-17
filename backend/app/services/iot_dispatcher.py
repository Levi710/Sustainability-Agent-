import logging
import random
import time
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

# Load Registry dynamically for IP/Hardware lookup
def get_iot_registry():
    import os, json
    # Default fallback machines
    default_machines = {
        "HVAC_Block_A": {"ip": "192.168.1.10", "status": "ONLINE", "type": "HVAC"},
        "Lab_PCs": {"ip": "192.168.1.15", "status": "ONLINE", "type": "IT"},
    }
    
    registry_paths = ["backend/app/data/device_registry.json", "app/data/device_registry.json"]
    registry_data = None
    
    for p in registry_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    registry_data = json.load(f)
                break
            except:
                continue

    if registry_data:
        # Convert registry to IoT format (IP generation)
        iot_reg = {}
        for dev_id, meta in registry_data.items():
            ip_suffix = sum(ord(c) for c in dev_id) % 254
            iot_reg[dev_id] = {
                "ip": f"192.168.1.{ip_suffix}",
                "status": "ONLINE",
                "type": meta.get("type", "UNKNOWN")
            }
        return iot_reg
        
    return default_machines

CONNECTED_MACHINES = get_iot_registry()

class IoTCommandDispatcher:
    """Simulates a bridge to physical hardware (e.g., via MQTT or Modbus)."""
    
    @staticmethod
    def dispatch(device_id: str, command: str) -> Dict:
        """Sends a signal to the machine and waits for acknowledgment."""
        if device_id not in CONNECTED_MACHINES:
            logger.warning(f"Device {device_id} not found in IoT registry.")
            return {"status": "FAILED", "error": "OFFLINE"}

        # Simulate Network Latency
        time.sleep(0.5) 
        
        # Simulate Acknowledgment
        success = random.random() > 0.05 # 95% success rate
        
        if success:
            logger.info(f"SIGNAL_SUCCESS: [{device_id}] Executed {command}")
            return {
                "status": "ACKNOWLEDGED",
                "timestamp": datetime.now().isoformat(),
                "device_ip": CONNECTED_MACHINES[device_id]["ip"],
                "signal_strength": f"{random.randint(70, 99)}%",
                "command": command
            }
        else:
            logger.error(f"SIGNAL_TIMEOUT: [{device_id}] Hardware failed to respond.")
            return {"status": "TIMEOUT", "error": "HARDWARE_NOT_READY"}

# Global instances for the command log (ephemeral for demo)
CONTROL_SIGNALS_LOG = []

def log_control_signal(session_id: str, device_id: str, command: str, result: Dict):
    CONTROL_SIGNALS_LOG.append({
        "session_id": session_id,
        "device": device_id,
        "command": command,
        "result": result,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    # Keep only last 20 for the UI
    if len(CONTROL_SIGNALS_LOG) > 20:
        CONTROL_SIGNALS_LOG.pop(0)
