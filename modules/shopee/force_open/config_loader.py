import json
import os
import logging

log = logging.getLogger("config_loader")

def load_config():
    """
    Load configuration from JSON files in the same directory.
    Loads monday_config.json and scheduler_config.json.
    Returns a merged dictionary.
    """
    config = {}
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    files = ["monday_config.json", "scheduler_config.json"]
    
    for filename in files:
        file_path = os.path.join(current_dir, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        config.update(data)
                        log.info(f"Loaded config from {filename}")
                    else:
                        log.warning(f"Config file {filename} does not contain a JSON object.")
            except Exception as e:
                log.error(f"Error loading {filename}: {e}")
        else:
            log.warning(f"Config file {filename} not found.")
            
    return config