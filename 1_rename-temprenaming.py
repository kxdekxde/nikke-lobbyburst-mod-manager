import os
import json
import re

def rename_files():
    # Paths to the JSON files
    burst_json_path = os.path.join("AddressablesJSON", "lobby_burst_merged_data.json")
    event_json_path = os.path.join("AddressablesJSON", "lobby_event_data.json")
    source_folder = "temp-renaming"

    # Load standard character data (burst/lobby)
    try:
        with open(burst_json_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {burst_json_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file at {burst_json_path}")
        return

    # Load event character data
    try:
        with open(event_json_path, 'r', encoding='utf-8') as f:
            event_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {event_json_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file at {event_json_path}")
        return

    # Create mapping for standard characters: (ID, skin_code) -> {lobby_id, burst_id}
    character_mapping = {}
    for character in character_data:
        key = (character["ID"], character["skin_code"])
        character_mapping[key] = {
            "lobby_id": character["lobby_id"],
            "burst_id": character["burst_id"]
        }

    # Create mapping for event characters: ID -> lobby_id
    event_mapping = {}
    for item in event_data:
        event_mapping[item["ID"]] = item["lobby_id"]

    # Iterate over files and rename them
    for filename in os.listdir(source_folder):
        new_id = None
        processed = False

        # Pattern 1: Check for standard character skin file (e.g., c470-00-lobby-...)
        skin_match = re.match(r'^(c\d{3})-(\d{2})-(lobby|burst)-', filename)
        if skin_match:
            processed = True
            char_id = skin_match.group(1)
            skin_code = skin_match.group(2)
            file_type = skin_match.group(3)

            key = (char_id, skin_code)
            if key in character_mapping:
                new_id = character_mapping[key]["burst_id"] if file_type == "burst" else character_mapping[key]["lobby_id"]
            else:
                print(f"Skipping {filename} - no mapping found for ID {char_id} and skin {skin_code}")
                continue
        
        # Pattern 2: If primary pattern failed, check for event file (e.g., eventtitle_neverland_02-lobby-...)
        if not processed:
            event_match = re.match(r'^([a-zA-Z0-9_]+)-(lobby|burst)-', filename)
            if event_match:
                processed = True
                id_part = event_match.group(1)
                
                # For events, we use the lobby_id from the JSON regardless of file type
                if id_part in event_mapping:
                    new_id = event_mapping[id_part]
                else:
                    print(f"Skipping {filename} - no mapping found for event ID '{id_part}'")
                    continue

        # If a new ID was found from either pattern, proceed with renaming
        if new_id:
            _, ext = os.path.splitext(filename)
            new_filename = new_id + ext

            old_path = os.path.join(source_folder, filename)
            new_path = os.path.join(source_folder, new_filename)

            try:
                os.rename(old_path, new_path)
                print(f"Renamed {filename} to {new_filename}")
            except OSError as e:
                print(f"Error renaming {filename}: {e}")
        elif not processed:
            # Only print skip message if the file was not processed by any pattern
            print(f"Skipping {filename} - does not match any known filename pattern.")

if __name__ == "__main__":
    rename_files()