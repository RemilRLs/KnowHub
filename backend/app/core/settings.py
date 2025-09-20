import json 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SETTING_FILE = BASE_DIR / "config" / "settings.json"

class Settings:
    def __init__(self):
        pass 
    
    @staticmethod
    def get_allowed_extensions() -> list[str]:
        try:
            with open(SETTING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return data.get("extensions", [])
        except FileNotFoundError:
            return []