import os
import json
import shutil

def main():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the settings file
    settings_path = os.path.join(script_dir, "naps_settings.json")
    
    # Path to the temp-renaming folder
    temp_renaming_path = os.path.join(script_dir, "temp-renaming")
    
    try:
        # Load the settings file
        with open(settings_path, 'r') as f:
            settings = json.load(f)
        
        naps_folder = settings.get("naps_folder")
        if not naps_folder:
            raise ValueError("NAPS folder path not found in settings file")
        
        if not os.path.exists(naps_folder):
            raise FileNotFoundError(f"NAPS folder not found at: {naps_folder}")
        
        if not os.path.exists(temp_renaming_path):
            raise FileNotFoundError(f"temp-renaming folder not found at: {temp_renaming_path}")
        
        # Get all files in temp-renaming folder
        temp_files = [f for f in os.listdir(temp_renaming_path) if os.path.isfile(os.path.join(temp_renaming_path, f))]
        
        if not temp_files:
            print("No files found in temp-renaming folder")
            return
        
        # Track which files were successfully replaced
        replaced_files = set()
        
        # Walk through the NAPS folder structure
        for root, dirs, files in os.walk(naps_folder):
            for file in files:
                if file in temp_files:
                    # Found a match, replace the file
                    src_path = os.path.join(temp_renaming_path, file)
                    dest_path = os.path.join(root, file)
                    
                    print(f"Replacing: {dest_path} with {src_path}")
                    
                    # Remove the original file
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    
                    # Copy the new file
                    shutil.copy2(src_path, dest_path)
                    replaced_files.add(file)
        
        # Delete successfully replaced files from temp-renaming
        for file in replaced_files:
            file_path = os.path.join(temp_renaming_path, file)
            os.remove(file_path)
            print(f"Deleted from temp-renaming: {file_path}")
        
        print(f"\nDone! Replaced {len(replaced_files)} files.")
        
        # Check if any files in temp-renaming weren't found in NAPS
        if len(replaced_files) < len(temp_files):
            not_found = set(temp_files) - replaced_files
            print("\nWarning: The following files from temp-renaming were not found in NAPS folder:")
            for fn in not_found:
                print(f" - {fn}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()