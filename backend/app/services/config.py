import os
from dotenv import load_dotenv

load_dotenv()

class GlobalSettings:
    def __init__(self):
        # Default from .env or True
        self.auto_fix = os.getenv("AUTO_FIX", "True").lower() == "true"
        self.debug_mode = True

settings = GlobalSettings()
