import os
import json
import re

def rename_files():
    # Path to the JSON file
    json_path = os.path.join("AddressablesJSON", "lobby_burst_merged_data.json")
    source_folder = "temp-renaming"
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_path}")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Create a mapping dictionary: (ID, skin_code) → {lobby_id, burst_id}
    mapping = {}
    for character in character_data:
        key = (character["ID"], character["skin_code"])
        mapping[key] = {
            "lobby_id": character["lobby_id"],
            "burst_id": character["burst_id"]
        }
    
    for filename in os.listdir(source_folder):
        # Extract ID and skin code (supports both lobby/burst)
        match = re.match(r'^(c\d{3})_(\d{2})_(lobby|burst)_', filename)
        if not match:
            print(f"Skipping {filename} - doesn't match expected pattern")
            continue
        
        char_id = match.group(1)
        skin_code = match.group(2)
        file_type = match.group(3)  # "lobby" or "burst"
        
        key = (char_id, skin_code)
        if key not in mapping:
            print(f"Skipping {filename} - no matching character found for ID {char_id} and skin {skin_code}")
            continue
        
        # Use burst_id if filename contains "burst", otherwise lobby_id
        new_id = mapping[key]["burst_id"] if file_type == "burst" else mapping[key]["lobby_id"]
        
        # Rename the file
        _, ext = os.path.splitext(filename)
        new_filename = new_id + ext
        
        old_path = os.path.join(source_folder, filename)
        new_path = os.path.join(source_folder, new_filename)
        
        try:
            os.rename(old_path, new_path)
            print(f"Renamed {filename} to {new_filename}")
        except OSError as e:
            print(f"Error renaming {filename}: {e}")

if __name__ == "__main__":
    rename_files()