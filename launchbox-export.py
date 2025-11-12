"""
LaunchBox Export Script

PURPOSE:
    Exports game metadata, media (box art, screenshots, videos, etc.), and optionally 
    ROM files from LaunchBox to a Batocera-compatible folder structure with gamelist.xml files.

REQUIREMENTS:
    - Python 3.x
    - PIL/Pillow library (install via: pip install Pillow)
    - LaunchBox installation with game metadata and media
    - Sufficient disk space in the output directory

CONFIGURATION:
    Edit the variables below before running:
    - lb_dir: Path to your LaunchBox installation folder
    - output_dir: Where to export the files
    - copy_roms: Set True to copy ROM files (can be large!)
    - copy_media: Set True to copy media files
    - convert_to_png: Convert JPG images to PNG format
    - recents_only: Export only recently added games
    - recent_days: Number of days to consider "recent" if recents_only is True
    - platforms: Dictionary mapping LaunchBox platform names to output folder names
                 (uncomment the platforms you want to export)

FUNCTIONALITY:
    - Reads LaunchBox platform XML files to extract game metadata
    - Copies and organizes media files (box art, screenshots, marquees, videos, manuals)
    - Renames all media files to match ROM filenames for proper Batocera linking
    - Converts images to PNG format (optional) and trims marquee whitespace
    - Generates Batocera-compatible gamelist.xml files for each platform
    - Can filter to only export recently added games (recents_only mode)
      * When enabled, only exports games added within the last N days (configurable)
      * Useful for incremental updates without re-exporting your entire collection
      * Games without DateAdded metadata will be skipped in this mode
    - Preserves game ratings, release dates, developers, publishers, genres, and player counts

OUTPUT STRUCTURE:
    output_dir/
    ├── platform_name/
    │   ├── gamelist.xml
    │   ├── covers/          (box art)
    │   ├── screenshots/     (gameplay screenshots)
    │   ├── marquees/        (clear logos/wheels)
    │   ├── videos/          (video previews)
    │   └── manuals/         (PDF manuals)

USAGE:
    1. Configure the variables in the "CONFIGURATION" section below
    2. Run the script: python launchbox-export.py
    3. Check the output directory for exported files
    4. Copy the platform folders to your Batocera system's roms directory

NOTES:
    - Image filenames are sanitized to handle special characters
    - All media files are renamed to match ROM filenames (e.g., if ROM is "game.chd", 
      box art becomes "game.png") to support platforms like ES-DE.
    - Marquee images are trimmed but not converted to preserve transparency
    - If media files cannot be found, warnings will be printed
    - Progress and statistics are displayed during execution
    - With recents_only=True, only games added in the last N days are exported
      (perfect for daily/weekly incremental exports to keep your collection updated)
"""

import glob
import os
from datetime import datetime, timedelta
from shutil import copy
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PIL import Image


# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to your LaunchBox folder
LB_DIR = r'R:\Games\LaunchBox'

# Where to put the exported roms, images and xmls
OUTPUT_DIR = r'R:\Launchbox-Export'

# Export options
COPY_ROMS = False
COPY_MEDIA = True
CONVERT_TO_PNG = True
RECENTS_ONLY = False
RECENT_DAYS = 7  # Export games added in last N days

# Platforms: Launchbox name -> output folder name
PLATFORMS = {
    # Uncomment platforms you want to export:
    # "3DO Interactive Multiplayer": "3do",
    # "Arcade": "mame",
    # "Arcade - FBNeo": "fbneo",
    # "Atari 2600": "atari2600",
    "Atari 7800": "atari7800",
    # "Atari Jaguar": "jaguar",
    # "Atari Lynx": "lynx",
    # "ColecoVision": "colecovision",
    # "Commodore 64": "c64",
    # "Commodore Amiga 500": "amiga500",
    # "Commodore Amiga 1200": "amiga1200",
    # "Commodore Amiga CD32": "amigacd32",
    # "Daphne": "daphne",
    # "GCE Vectrex": "vectrex",
    # "Mattel Intellivision": "intellivision",
    # "Magnavox Odyssey 2": "o2em",
    # "Microsoft MSX2": "msx2",
    # "Microsoft Xbox": "xbox",
    # "Moonlight": "moonlight",
    # "NEC TurboGrafx-16": "pcengine",
    # "NEC TurboGrafx-CD": "pcenginecd",
    # "Nintendo 3DS": "3ds",
    # "Nintendo 64": "n64",
    # "Nintendo DS": "nds",
    # "Nintendo Entertainment System": "nes",
    # "Nintendo Famicom Disk System": "fds",
    # "Nintendo Game Boy Advance": "gba",
    # "Nintendo Game Boy Color": "gbc",
    # "Nintendo Game Boy": "gb",
    # "Nintendo GameCube": "gamecube",
    # "Nintendo MSU-1": "snes-msu1",
    # "Nintendo Satellaview": "satellaview",
    # "Nintendo Switch": "switch",
    # "Nintendo Virtual Boy": "virtualboy",
    # "Nintendo Wii U": "wiiu",
    # "Nintendo Wii": "wii",
    # "Philips CD-i": "cdi",
    # "PICO-8": "pico8",
    # "Sammy Atomiswave": "atomiswave",
    # "Sega 32X": "sega32x",
    # "Sega CD": "segacd",
    # "Sega Dreamcast": "dreamcast",
    # "Sega Game Gear": "gamegear",
    # "Sega Genesis": "megadrive",
    # "Sega Master System": "mastersystem",
    # "Sega MSU-MD": "msu-md",
    # "Sega Model 3": "model3",
    # "Sega Naomi": "naomi",
    # "Sega Naomi 2": "naomi2",
    # "Sega Saturn": "saturn",
    # "Sega SG-1000": "sg1000",
    # "Sharp X68000": "x68000",
    # "Sinclair ZX Spectrum": "zxspectrum",
    # "SNK Neo Geo AES": "neogeo",
    # "SNK Neo Geo CD": "neogeocd",
    # "SNK Neo Geo Pocket Color": "ngpc",
    # "Sony Playstation": "psx",
    # "Sony Playstation 2": "ps2",
    # "Sony Playstation 3": "ps3",
    # "Sony Playstation Vita": "vita",
    # "Sony PSP": "psp",
    # "Super Nintendo Entertainment System": "snes",
    # "Windows": "steam",
    # "WonderSwan": "wswan",
    # "WonderSwan Color": "wswanc",
}

# Batocera media type mapping
MEDIA_MAPPINGS = [
    {"type": "screenshot", "xmltag": "image", "output": "screenshots", "subdir": "Screenshot - Gameplay"},
    {"type": "marquee", "xmltag": "marquee", "output": "marquees", "subdir": "Clear Logo"},
    {"type": "box art", "xmltag": "thumbnail", "output": "covers", "subdir": "Box - Front"},
    {"type": "manual", "xmltag": "manual", "output": "manuals", "subdir": "../manuals"},
    {"type": "video", "xmltag": "video", "output": "videos", "subdir": "../videos"},
]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by replacing invalid characters."""
    invalid_chars = [':', "'", '/', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def find_media_file(game_name: str, media_files: List[str]) -> Optional[str]:
    """
    Find the first matching media file for a game.
    
    Optimized with early return and reduced string operations.
    """
    sanitized_name = sanitize_filename(game_name)
    sanitized_lower = sanitized_name.lower()
    
    for filepath in media_files:
        filename = os.path.basename(filepath)
        filename_lower = filename.lower()
        
        # Check for common naming patterns
        if (filename.startswith(sanitized_name + "-0") or 
            filename.startswith(sanitized_name + ".") or
            filename_lower == sanitized_lower + ".mp4"):
            return filepath
    
    return None


def parse_date_added(date_str: str) -> Optional[datetime]:
    """Parse LaunchBox DateAdded field with error handling."""
    try:
        clean_date = date_str.strip().replace("Z", "")
        
        if "T" in clean_date:
            # Full datetime format
            return datetime.fromisoformat(clean_date.split(".")[0])
        else:
            # Date only format (YYYY-MM-DD)
            return datetime.fromisoformat(clean_date + "T00:00:00")
    except (ValueError, AttributeError):
        return None


def is_game_recent(game_element: ET.Element, cutoff_date: datetime) -> bool:
    """Check if a game was added after the cutoff date."""
    date_elem = game_element.find("DateAdded")
    
    if date_elem is None or not date_elem.text:
        return False
    
    added_date = parse_date_added(date_elem.text)
    return added_date is not None and added_date >= cutoff_date


def process_image(img_path: str, output_path: str, media_type: str) -> None:
    """
    Process and save an image file with optional conversion and trimming.
    
    Args:
        img_path: Source image path
        output_path: Destination image path
        media_type: Type of media (marquee, screenshot, etc.)
    """
    img = Image.open(img_path)
    ext = os.path.splitext(img_path)[1].lower()
    
    # Special handling for marquees: trim but don't convert
    if media_type == "marquee":
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.save(output_path, format="PNG")
        return
    
    # Convert to PNG if enabled and applicable
    if CONVERT_TO_PNG and ext in [".jpg", ".jpeg", ".png"]:
        # Preserve transparency
        if 'A' in img.getbands():
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(output_path, format="PNG")
    else:
        img.save(output_path)


def save_media_file(
    source_path: str,
    output_dir: str,
    rom_basename: str,
    media_type: str
) -> str:
    """
    Copy and process media file, returning relative path for XML.
    
    Args:
        source_path: Original media file path
        output_dir: Output directory for this media type
        rom_basename: Base name of the ROM (without extension)
        media_type: Type of media for special handling
    
    Returns:
        Relative path string for use in gamelist.xml
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ext = os.path.splitext(source_path)[1].lower()
    
    # Determine output filename and extension
    if CONVERT_TO_PNG and ext in [".jpg", ".jpeg", ".png"]:
        new_filename = f"{rom_basename}.png"
    else:
        new_filename = f"{rom_basename}{ext}"
    
    output_path = os.path.join(output_dir, new_filename)
    
    try:
        # Process images, copy other media types
        if ext in [".jpg", ".jpeg", ".png"]:
            process_image(source_path, output_path, media_type)
        elif COPY_MEDIA:
            copy(source_path, output_path)
    except Exception as e:
        print(f"  Warning: Failed to process {source_path}: {e}")
        # Attempt fallback copy
        try:
            copy(source_path, output_path)
        except Exception as e2:
            print(f"  Error: Fallback copy also failed: {e2}")
    
    # Return relative path for XML
    return f"./{os.path.basename(output_dir)}/{new_filename}"


def build_media_index(media_dir: str) -> List[str]:
    """Build a list of all media files in a directory."""
    if not os.path.isdir(media_dir):
        return []
    
    return [
        f for f in glob.glob(os.path.join(media_dir, "**"), recursive=True)
        if os.path.isfile(f)
    ]


def extract_game_metadata(game_elem: ET.Element) -> Dict[str, str]:
    """Extract all metadata fields from a game XML element."""
    metadata = {}
    
    # Star rating (convert to 0-1 scale)
    if (rating_elem := game_elem.find("StarRating")) is not None:
        try:
            metadata["rating"] = str(int(rating_elem.text) * 2 / 10)
        except (ValueError, TypeError):
            pass
    
    # Release date (convert to Batocera format)
    if (release_elem := game_elem.find("ReleaseDate")) is not None and release_elem.text:
        metadata["releasedate"] = release_elem.text.replace("-", "").split("T")[0] + "T000000"
    
    # Simple text fields
    text_fields = ["Developer", "Publisher", "Genre", "Notes"]
    xml_to_key = {
        "Developer": "developer",
        "Publisher": "publisher",
        "Genre": "genre",
        "Notes": "desc"
    }
    
    for xml_tag in text_fields:
        if (elem := game_elem.find(xml_tag)) is not None and elem.text:
            metadata[xml_to_key[xml_tag]] = elem.text
    
    # Max players (handle "0" prefix)
    if (players_elem := game_elem.find("MaxPlayers")) is not None and players_elem.text:
        mp = players_elem.text
        metadata["players"] = "1+" if mp.startswith("0") else mp
    
    return metadata


def write_gamelist_xml(games: List[Dict[str, str]], output_path: str) -> None:
    """Write games list to Batocera-compatible XML file."""
    root = ET.Element("gameList")
    
    for game_data in games:
        game_elem = ET.SubElement(root, "game")
        for key, value in game_data.items():
            child = ET.SubElement(game_elem, key)
            child.text = value
    
    # Pretty print XML
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    # Remove XML declaration
    xml_lines = xml_str.splitlines()
    if xml_lines[0].startswith("<?xml"):
        xml_str = "\n".join(xml_lines[1:])
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_platform(platform_lb: str, platform_rp: str, cutoff_date: Optional[datetime]) -> tuple:
    """
    Process a single platform and return statistics.
    
    Returns:
        Tuple of (games_exported, media_copied)
    """
    print(f"\nProcessing {platform_lb} → {platform_rp}")
    
    # Build paths
    lb_platform_xml = os.path.join(LB_DIR, "Data", "Platforms", f"{platform_lb}.xml")
    output_platform_dir = os.path.join(OUTPUT_DIR, platform_rp)
    
    # Check if platform XML exists
    if not os.path.isfile(lb_platform_xml):
        print(f"  Warning: Platform XML not found: {lb_platform_xml}")
        return 0, 0
    
    # Create output directory
    os.makedirs(output_platform_dir, exist_ok=True)
    
    # Parse XML
    try:
        xmltree = ET.parse(lb_platform_xml)
    except ET.ParseError as e:
        print(f"  Error: Failed to parse XML: {e}")
        return 0, 0
    
    # Build media file indexes
    print("  Indexing media files...")
    for mapping in MEDIA_MAPPINGS:
        if mapping["subdir"].startswith(".."):
            # Manual and video directories are at LaunchBox root
            media_dir = os.path.join(LB_DIR, mapping["subdir"].replace("..", "").strip("/\\"), platform_lb)
        else:
            # Image directories are under images/platform
            media_dir = os.path.join(LB_DIR, "images", platform_lb, mapping["subdir"])
        
        mapping["files"] = build_media_index(media_dir)
    
    # Process games
    games_found = []
    total_games = 0
    local_media_count = 0
    
    for game in xmltree.getroot().iter("Game"):
        total_games += 1
        
        try:
            # Check if game is recent enough
            if cutoff_date and not is_game_recent(game, cutoff_date):
                continue
            
            # Extract ROM info
            rom_path_elem = game.find("ApplicationPath")
            title_elem = game.find("Title")
            
            if rom_path_elem is None or title_elem is None:
                continue
            
            rom_path = rom_path_elem.text
            rom_name = os.path.basename(rom_path)
            rom_basename = os.path.splitext(rom_name)[0]
            game_title = title_elem.text
            
            # Build game data
            game_data = {
                "path": f"./{rom_name}",
                "name": game_title
            }
            
            # Add metadata
            game_data.update(extract_game_metadata(game))
            
            # Process media files
            sanitized_title = sanitize_filename(game_title)
            for mapping in MEDIA_MAPPINGS:
                media_path = find_media_file(sanitized_title, mapping["files"])
                
                if media_path:
                    output_dir = os.path.join(output_platform_dir, mapping["output"])
                    rel_path = save_media_file(media_path, output_dir, rom_basename, mapping["type"])
                    game_data[mapping["xmltag"]] = rel_path
                    local_media_count += 1
                else:
                    game_data[mapping["xmltag"]] = ""
                    # Only print errors for essential media types (covers, screenshots, marquees)
                    if mapping["output"] in ["covers", "screenshots", "marquees"]:
                        print(f"  ERROR: No {mapping['type']} found for: {game_title}")
            
            # Copy ROM if enabled
            if COPY_ROMS and os.path.isfile(rom_path):
                try:
                    copy(rom_path, output_platform_dir)
                except Exception as e:
                    print(f"  Warning: Failed to copy ROM {rom_name}: {e}")
            
            games_found.append(game_data)
            
        except Exception as e:
            print(f"  Error processing game: {e}")
            continue
    
    # Write gamelist.xml
    if games_found:
        xml_path = os.path.join(output_platform_dir, "gamelist.xml")
        try:
            write_gamelist_xml(games_found, xml_path)
        except Exception as e:
            print(f"  Error writing gamelist.xml: {e}")
            return 0, 0
    
    # Print summary
    if RECENTS_ONLY:
        print(f"  Exported {len(games_found)} recent games out of {total_games} total")
    else:
        print(f"  Exported {len(games_found)} games")
    
    return len(games_found), local_media_count


def main():
    """Main execution function."""
    print("=" * 70)
    print("LaunchBox to Batocera Export")
    print("=" * 70)
    
    # Calculate cutoff date for recent games
    cutoff_date = None
    if RECENTS_ONLY:
        cutoff_date = datetime.now() - timedelta(days=RECENT_DAYS)
        print(f"\nExporting games added since: {cutoff_date.strftime('%Y-%m-%d')}")
    
    # Process each platform
    total_games = 0
    total_media = 0
    total_platforms = 0
    
    for platform_lb, platform_rp in PLATFORMS.items():
        games_count, media_count = process_platform(platform_lb, platform_rp, cutoff_date)
        
        if games_count > 0:
            total_games += games_count
            total_media += media_count
            total_platforms += 1
    
    # Print final summary
    print("\n" + "=" * 70)
    print(f"Export Complete!")
    print(f"  Platforms: {total_platforms}")
    print(f"  Games: {total_games:,}")
    print(f"  Media files: {total_media:,}")
    print("=" * 70)


if __name__ == "__main__":
    main()
