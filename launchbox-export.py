"""
LaunchBox Export Script

PURPOSE:
    Exports game metadata, media (box art, screenshots, videos, etc.), and
    optionally ROM files from LaunchBox to a Batocera-compatible folder
    structure with gamelist.xml files.

REQUIREMENTS:
    - Python 3.9+ (uses ET.indent and argparse.BooleanOptionalAction)
    - PIL/Pillow library (install via: pip install Pillow)
    - LaunchBox installation with game metadata and media
    - Sufficient disk space in the output directory

CONFIGURATION:
    Defaults are set as module-level constants in the CONFIGURATION block
    below, but every option is also a CLI flag. Run with -h to list them.

    - lb_dir: Path to your LaunchBox installation folder
    - output_dir: Where to export the files
    - copy_roms: Copy ROM files (can be large!)
    - copy_media: Copy media files
    - convert_to_png: Convert JPG images to PNG format
    - recents_only: Export only recently added games
    - recent_days: How many days "recent" means
    - workers: Thread-pool size for media copying
    - platforms: Dictionary mapping LaunchBox platform names to output
                 folder names (uncomment the platforms you want to export)

FUNCTIONALITY:
    - Reads LaunchBox platform XML files to extract game metadata
    - Copies and organizes media files (box art, screenshots, marquees,
      videos, manuals)
    - Renames all media files to match ROM filenames for proper Batocera
      linking
    - Converts images to PNG format (optional) and trims marquee whitespace
    - Generates Batocera-compatible gamelist.xml files for each platform
    - Can filter to only export recently added games (recents_only mode)
      * When enabled, only exports games added within the last N days
      * Useful for incremental updates without re-exporting your entire
        collection
      * Games without DateAdded metadata are skipped; the count is
        reported in the final summary

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
    python launchbox-export.py                      # use defaults
    python launchbox-export.py --recents-only       # last 7 days
    python launchbox-export.py --recents-only --recent-days 30
    python launchbox-export.py --no-convert-to-png --workers 16
"""

import argparse
import os
import traceback
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from shutil import copy
from typing import Dict, List, Optional, Tuple

from PIL import Image


# ============================================================================
# CONFIGURATION (defaults — overridable via CLI flags)
# ============================================================================

LB_DIR = r'R:\Games\LaunchBox'
OUTPUT_DIR = r'R:\Launchbox-Export'

COPY_ROMS = False
COPY_MEDIA = True
CONVERT_TO_PNG = True
RECENTS_ONLY = False
RECENT_DAYS = 7
WORKERS = 8

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

MEDIA_MAPPINGS = [
    {"type": "screenshot", "xmltag": "image",     "output": "screenshots", "subdir": "Screenshot - Gameplay"},
    {"type": "marquee",    "xmltag": "marquee",   "output": "marquees",    "subdir": "Clear Logo"},
    {"type": "box art",    "xmltag": "thumbnail", "output": "covers",      "subdir": "Box - Front"},
    {"type": "manual",     "xmltag": "manual",    "output": "manuals",     "subdir": "../manuals"},
    {"type": "video",      "xmltag": "video",     "output": "videos",      "subdir": "../videos"},
]

ESSENTIAL_MEDIA_OUTPUTS = {"covers", "screenshots", "marquees"}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_filename(filename: str) -> str:
    """Replace invalid filesystem characters with underscores."""
    invalid_chars = [':', "'", '/', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def list_media_files(media_dir: str) -> List[str]:
    """Return every file path beneath media_dir."""
    if not os.path.isdir(media_dir):
        return []
    files = []
    for root, _, filenames in os.walk(media_dir):
        for fn in filenames:
            files.append(os.path.join(root, fn))
    return files


def build_media_lookup(media_files: List[str]) -> Dict[str, str]:
    """
    Build a {lowercased_game_name_stem -> filepath} map for O(1) lookup.

    Handles LaunchBox's numbered-variant suffix (e.g. Game-01.png,
    Game-02.png, Game-09.jpg) by stripping a trailing "-0N" from the
    stem before indexing, which mirrors the old startswith("name-0")
    matching behavior. First file wins when multiple variants share
    a stem, so sort the input for determinism.
    """
    lookup: Dict[str, str] = {}
    for filepath in sorted(media_files):
        filename = os.path.basename(filepath)
        stem, _ = os.path.splitext(filename)

        dash_idx = stem.rfind("-0")
        if 0 <= dash_idx < len(stem) - 2:
            key = stem[:dash_idx].lower()
        else:
            key = stem.lower()

        lookup.setdefault(key, filepath)
    return lookup


def find_media_file(sanitized_name: str, lookup: Dict[str, str]) -> Optional[str]:
    """Return a media filepath for a game from a prebuilt lookup, or None."""
    return lookup.get(sanitized_name.lower())


def parse_date_added(date_str: str) -> Optional[datetime]:
    """Parse LaunchBox DateAdded field with error handling."""
    try:
        clean_date = date_str.strip().rstrip("Z")

        if "T" in clean_date:
            return datetime.fromisoformat(clean_date.split(".")[0])
        return datetime.fromisoformat(clean_date + "T00:00:00")
    except (ValueError, AttributeError):
        return None


def is_game_recent(game_element: ET.Element, cutoff_date: datetime) -> Tuple[bool, bool]:
    """
    Return (is_recent, has_parseable_date).

    The second flag lets callers tell "skipped because old" apart from
    "skipped because no DateAdded metadata exists" so the latter can be
    reported in the final summary.
    """
    date_elem = game_element.find("DateAdded")
    if date_elem is None or not date_elem.text:
        return False, False

    added_date = parse_date_added(date_elem.text)
    if added_date is None:
        return False, False

    return added_date >= cutoff_date, True


def process_image(img_path: str, output_path: str, media_type: str) -> None:
    """Process and save an image. Marquees get trimmed; others optionally convert to PNG."""
    with Image.open(img_path) as img:
        ext = os.path.splitext(img_path)[1].lower()

        if media_type == "marquee":
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            img.save(output_path, format="PNG")
            return

        if CONVERT_TO_PNG and ext in [".jpg", ".jpeg", ".png"]:
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
    media_type: str,
) -> str:
    """
    Copy and process a media file and return its path relative to the
    platform directory (for embedding into gamelist.xml).

    When COPY_MEDIA is False no file is written, but the expected path
    is still returned so gamelist.xml can reference media that was
    copied on a previous run.
    """
    ext = os.path.splitext(source_path)[1].lower()
    is_image = ext in [".jpg", ".jpeg", ".png"]

    target_ext = ".png" if (is_image and CONVERT_TO_PNG) else ext
    new_filename = f"{rom_basename}{target_ext}"
    rel_path = f"./{os.path.basename(output_dir)}/{new_filename}"

    if not COPY_MEDIA:
        return rel_path

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, new_filename)

    try:
        if is_image:
            process_image(source_path, output_path, media_type)
        else:
            copy(source_path, output_path)
    except Exception as e:
        print(f"  Warning: Failed to process {source_path}: {e}")
        # Fallback: raw copy preserving the SOURCE extension so we don't
        # end up with raw JPEG bytes inside a .png file.
        fallback_filename = f"{rom_basename}{ext}"
        fallback_path = os.path.join(output_dir, fallback_filename)
        try:
            copy(source_path, fallback_path)
            rel_path = f"./{os.path.basename(output_dir)}/{fallback_filename}"
        except Exception as e2:
            print(f"  Error: Fallback copy also failed: {e2}")

    return rel_path


def extract_game_metadata(game_elem: ET.Element) -> Dict[str, str]:
    """Extract metadata fields from a game XML element."""
    metadata: Dict[str, str] = {}

    if (rating_elem := game_elem.find("StarRating")) is not None:
        try:
            metadata["rating"] = str(int(rating_elem.text) * 2 / 10)
        except (ValueError, TypeError):
            pass

    if (release_elem := game_elem.find("ReleaseDate")) is not None and release_elem.text:
        metadata["releasedate"] = release_elem.text.replace("-", "").split("T")[0] + "T000000"

    xml_to_key = {
        "Developer": "developer",
        "Publisher": "publisher",
        "Genre":     "genre",
        "Notes":     "desc",
    }
    for xml_tag, key in xml_to_key.items():
        if (elem := game_elem.find(xml_tag)) is not None and elem.text:
            metadata[key] = elem.text

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

    ET.indent(root, space="    ")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ET.tostring(root, encoding="unicode"))


# ============================================================================
# PER-GAME AND PER-PLATFORM PROCESSING
# ============================================================================

def process_game(
    game_elem: ET.Element,
    output_platform_dir: str,
    media_index: List[Dict],
) -> Tuple[Optional[Dict[str, str]], int]:
    """Extract and export a single game. Returns (game_data, media_files_copied)."""
    title_elem = game_elem.find("Title")
    rom_path_elem = game_elem.find("ApplicationPath")

    if rom_path_elem is None or rom_path_elem.text is None:
        return None, 0
    if title_elem is None or not title_elem.text:
        return None, 0

    game_title = title_elem.text

    try:
        rom_path = rom_path_elem.text
        rom_name = os.path.basename(rom_path)
        rom_basename = os.path.splitext(rom_name)[0]

        game_data: Dict[str, str] = {
            "path": f"./{rom_name}",
            "name": game_title,
        }
        game_data.update(extract_game_metadata(game_elem))

        sanitized_title = sanitize_filename(game_title)
        media_count = 0

        for entry in media_index:
            media_path = find_media_file(sanitized_title, entry["lookup"])
            if media_path:
                output_dir = os.path.join(output_platform_dir, entry["output"])
                rel_path = save_media_file(
                    media_path, output_dir, rom_basename, entry["type"]
                )
                game_data[entry["xmltag"]] = rel_path
                media_count += 1
            else:
                game_data[entry["xmltag"]] = ""
                if entry["output"] in ESSENTIAL_MEDIA_OUTPUTS:
                    print(f"  ERROR: No {entry['type']} found for: {game_title}")

        if COPY_ROMS and os.path.isfile(rom_path):
            try:
                copy(rom_path, output_platform_dir)
            except Exception as e:
                print(f"  Warning: Failed to copy ROM {rom_name}: {e}")

        return game_data, media_count

    except Exception as e:
        print(f"  Error processing '{game_title}': {e}")
        traceback.print_exc()
        return None, 0


def process_platform(
    platform_lb: str,
    platform_rp: str,
    cutoff_date: Optional[datetime],
) -> Tuple[int, int, int]:
    """
    Process a single platform.

    Returns (games_exported, media_copied, games_skipped_no_date).
    """
    print(f"\nProcessing {platform_lb} → {platform_rp}")

    lb_platform_xml = os.path.join(LB_DIR, "Data", "Platforms", f"{platform_lb}.xml")
    output_platform_dir = os.path.join(OUTPUT_DIR, platform_rp)

    if not os.path.isfile(lb_platform_xml):
        print(f"  Warning: Platform XML not found: {lb_platform_xml}")
        return 0, 0, 0

    os.makedirs(output_platform_dir, exist_ok=True)

    try:
        xmltree = ET.parse(lb_platform_xml)
    except ET.ParseError as e:
        print(f"  Error: Failed to parse XML: {e}")
        return 0, 0, 0

    # Build per-platform media lookups as a LOCAL list so the module-level
    # MEDIA_MAPPINGS isn't mutated or shared across platforms.
    print("  Indexing media files...")
    media_index: List[Dict] = []
    for mapping in MEDIA_MAPPINGS:
        if mapping["subdir"].startswith(".."):
            media_dir = os.path.join(
                LB_DIR, mapping["subdir"].replace("..", "").strip("/\\"), platform_lb
            )
        else:
            media_dir = os.path.join(LB_DIR, "images", platform_lb, mapping["subdir"])

        media_files = list_media_files(media_dir)
        media_index.append({
            "type":   mapping["type"],
            "xmltag": mapping["xmltag"],
            "output": mapping["output"],
            "lookup": build_media_lookup(media_files),
        })

    # Filter games by date up front so the thread pool only sees eligible ones.
    games_to_process: List[ET.Element] = []
    skipped_no_date = 0
    total_games = 0

    for game in xmltree.getroot().iter("Game"):
        total_games += 1
        if cutoff_date is not None:
            is_recent, has_date = is_game_recent(game, cutoff_date)
            if not has_date:
                skipped_no_date += 1
                continue
            if not is_recent:
                continue
        games_to_process.append(game)

    # Process in parallel. I/O-bound work (disk copies, PIL conversions
    # that release the GIL) benefits from threads.
    games_found: List[Dict[str, str]] = []
    local_media_count = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [
            executor.submit(process_game, game, output_platform_dir, media_index)
            for game in games_to_process
        ]
        for future in as_completed(futures):
            game_data, media_count = future.result()
            if game_data is not None:
                games_found.append(game_data)
                local_media_count += media_count

    if games_found:
        xml_path = os.path.join(output_platform_dir, "gamelist.xml")
        try:
            write_gamelist_xml(games_found, xml_path)
        except Exception as e:
            print(f"  Error writing gamelist.xml: {e}")
            return 0, 0, skipped_no_date

    if RECENTS_ONLY:
        print(f"  Exported {len(games_found)} recent games out of {total_games} total")
        if skipped_no_date:
            print(f"  Skipped {skipped_no_date} games with missing/unparseable DateAdded")
    else:
        print(f"  Exported {len(games_found)} games")

    return len(games_found), local_media_count, skipped_no_date


# ============================================================================
# CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export LaunchBox metadata and media to a Batocera-compatible tree."
    )
    parser.add_argument("--lb-dir", default=LB_DIR,
                        help="Path to LaunchBox installation (default: %(default)s)")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="Destination directory (default: %(default)s)")
    parser.add_argument("--copy-roms", action=argparse.BooleanOptionalAction,
                        default=COPY_ROMS, help="Also copy ROM files (default: %(default)s)")
    parser.add_argument("--copy-media", action=argparse.BooleanOptionalAction,
                        default=COPY_MEDIA, help="Copy media files (default: %(default)s)")
    parser.add_argument("--convert-to-png", action=argparse.BooleanOptionalAction,
                        default=CONVERT_TO_PNG,
                        help="Convert JPG images to PNG (default: %(default)s)")
    parser.add_argument("--recents-only", action=argparse.BooleanOptionalAction,
                        default=RECENTS_ONLY,
                        help="Only export games added in the last --recent-days days")
    parser.add_argument("--recent-days", type=int, default=RECENT_DAYS,
                        help="Days threshold for --recents-only (default: %(default)s)")
    parser.add_argument("--workers", type=int, default=WORKERS,
                        help="Thread-pool size for media copying (default: %(default)s)")
    return parser.parse_args()


def main() -> None:
    global LB_DIR, OUTPUT_DIR, COPY_ROMS, COPY_MEDIA, CONVERT_TO_PNG
    global RECENTS_ONLY, RECENT_DAYS, WORKERS

    args = parse_args()
    LB_DIR         = args.lb_dir
    OUTPUT_DIR     = args.output_dir
    COPY_ROMS      = args.copy_roms
    COPY_MEDIA     = args.copy_media
    CONVERT_TO_PNG = args.convert_to_png
    RECENTS_ONLY   = args.recents_only
    RECENT_DAYS    = args.recent_days
    WORKERS        = args.workers

    print("=" * 70)
    print("LaunchBox to Batocera Export")
    print("=" * 70)

    cutoff_date: Optional[datetime] = None
    if RECENTS_ONLY:
        cutoff_date = datetime.now() - timedelta(days=RECENT_DAYS)
        print(f"\nExporting games added since: {cutoff_date.strftime('%Y-%m-%d')}")

    total_games = 0
    total_media = 0
    total_skipped_no_date = 0
    total_platforms = 0

    for platform_lb, platform_rp in PLATFORMS.items():
        games_count, media_count, skipped_no_date = process_platform(
            platform_lb, platform_rp, cutoff_date
        )
        total_skipped_no_date += skipped_no_date
        if games_count > 0:
            total_games += games_count
            total_media += media_count
            total_platforms += 1

    print("\n" + "=" * 70)
    print("Export Complete!")
    print(f"  Platforms:   {total_platforms}")
    print(f"  Games:       {total_games:,}")
    print(f"  Media files: {total_media:,}")
    if RECENTS_ONLY and total_skipped_no_date:
        print(f"  Skipped (no DateAdded): {total_skipped_no_date:,}")
    print("=" * 70)


if __name__ == "__main__":
    main()
