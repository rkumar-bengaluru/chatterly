import json
from typing import Dict, Any 
# Load JSON from file
def load_json_from_file(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def save_json(file_path, settings: Dict[str, Any]):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)