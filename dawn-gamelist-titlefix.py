import json
import xml.etree.ElementTree as ET
import os

def update_game_names_nested_dict_json(games_json_path, platforms_root_dir):
    """
    Updates the 'Name' fields in Games.json (with nested platform keys pointing to game dictionaries)
    with proper titles from gamelist.xml files. The output JSON file will be flattened to a single line.

    Args:
        games_json_path (str): The path to the Games.json file.
        platforms_root_dir (str): The root directory containing platform subdirectories,
                                 each with a gamelist.xml file.
    """
    try:
        with open(games_json_path, 'r', encoding='utf-8') as f:
            games_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Games.json not found at {games_json_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {games_json_path}. Please check the file format.")
        return

    # Ensure games_data is a dictionary at the top level
    if not isinstance(games_data, dict):
        print(f"Error: Expected Games.json to contain a dictionary (object) at the root, but found a different structure.")
        return

    # Dictionary to store filename to game name mappings from all gamelist.xml files
    filename_to_title = {}

    # Discover platform directories and parse their gamelist.xml files
    platform_dirs = [d for d in os.listdir(platforms_root_dir) if os.path.isdir(os.path.join(platforms_root_dir, d))]

    if not platform_dirs:
        print(f"No platform subdirectories found in {platforms_root_dir}. Make sure your gamelist.xml files are in subdirectories (e.g., '{platforms_root_dir}/<platform_name>/gamelist.xml').")
        return

    for platform_name in platform_dirs:
        gamelist_xml_path = os.path.join(platforms_root_dir, platform_name, 'gamelist.xml')
        if not os.path.exists(gamelist_xml_path):
            print(f"Warning: gamelist.xml not found for platform '{platform_name}' at {gamelist_xml_path}. Skipping.")
            continue

        try:
            tree = ET.parse(gamelist_xml_path)
            root = tree.getroot()
            for game_element in root.findall('game'):
                path_element = game_element.find('path')
                name_element = game_element.find('name')
                if path_element is not None and name_element is not None:
                    # Extract filename from the path, e.g., './pacmania.zip' -> 'pacmania.zip'
                    filename = os.path.basename(path_element.text)
                    game_title = name_element.text
                    filename_to_title[filename] = game_title
        except ET.ParseError:
            print(f"Error: Could not parse gamelist.xml for platform '{platform_name}'. Skipping.")
        except FileNotFoundError:
            print(f"Error: gamelist.xml not found at {gamelist_xml_path}. Skipping.")

    if not filename_to_title:
        print("No game titles could be extracted from any gamelist.xml files. Please check the XML file formats and paths.")
        return

    updated_count = 0
    # Iterate through the games_data structure, which is a dictionary of platforms
    for platform_key, platform_games_dict in games_data.items():
        # Expect platform_games_dict to be a dictionary where keys are RomNames and values are game objects
        if isinstance(platform_games_dict, dict):
            for rom_name_in_json, game_info in platform_games_dict.items():
                if isinstance(game_info, dict) and "RomName" in game_info and "Name" in game_info:
                    # The RomName in Games.json includes the extension
                    # The filename extracted from gamelist.xml also includes the extension
                    if game_info["RomName"] in filename_to_title:
                        proper_title = filename_to_title[game_info["RomName"]]
                        if game_info["Name"] != proper_title:
                            game_info["Name"] = proper_title
                            updated_count += 1
                            # Optional: print updates
                            # print(f"Updated '{game_info['RomName']}' for platform '{platform_key}' to '{proper_title}'")
        else:
            print(f"Warning: Expected a dictionary of games for platform key '{platform_key}', but found a different type. Skipping.")


    if updated_count > 0:
        try:
            with open(games_json_path, 'w', encoding='utf-8') as f:
                # Flatten the JSON to a single line when writing
                json.dump(games_data, f, separators=(',', ':'))
            print(f"\nSuccessfully updated {updated_count} game names in {games_json_path} and flattened the output.")
        except IOError:
            print(f"Error: Could not write to {games_json_path}. Please check file permissions.")
    else:
        print("\nNo game names needed updating or no matches found.")

# --- How to use this script ---
# 1. Save the code above as a Python file (e.g., update_games_flattened_fixed.py).
# 2. Make sure 'Games.json' is in the same directory where you run the script,
#    or provide its full path.
# 3. Create a main directory that contains all your platform subdirectories,
#    each containing its 'gamelist.xml'.
#    Example:
#    your_root_folder/
#    ├── Games.json
#    ├── platform1/
#    │   └── gamelist.xml
#    ├── platform2/
#    │   └── gamelist.xml
#    └── ...
# 4. Set the `platforms_root_directory` variable below to the path of 'your_root_folder'.

if __name__ == "__main__":
    games_file = "Games.json"  # Path to your Games.json file
    # Set this to the directory that contains your platform subdirectories
    platforms_root_directory = "." # Assuming subdirectories are in the current directory

    update_game_names_nested_dict_json(games_file, platforms_root_directory)