import glob
import io
import os
from PIL import Image
from shutil import copy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys
import datetime

# version 4.2 (Batocera-only, all PNG lowercase, simplified structure)

# The path to your LaunchBox folder.
lb_dir = r'R:\Games\LaunchBox'

# Where to put the exported roms, images and xmls
output_dir = r'R:\Launchbox-Export'

copy_roms = False
copy_media = True
convert_to_png = True
recents_only = False
recent_days = 3   # copy media only for games added in last N days

# Platforms: Launchbox name -> output folder name
platforms = dict()
# platforms["3DO Interactive Multiplayer"] = "3do"
# platforms["Arcade"] = "mame"
# platforms["Arcade - FBNeo"] = "fbneo"
# platforms["Atari 2600"] = "atari2600"
platforms["Atari 7800"] = "atari7800"
# platforms["Atari Jaguar"] = "jaguar"
# platforms["Atari Lynx"] = "lynx"
# platforms["ColecoVision"] = "colecovision"
# platforms["Commodore 64"] = "c64"
# platforms["Commodore Amiga 500"] = "amiga500"
# platforms["Commodore Amiga 1200"] = "amiga1200"
# platforms["Commodore Amiga CD32"] = "amigacd32"
# platforms["Daphne"] = "daphne"
# platforms["GCE Vectrex"] = "vectrex"
# platforms["Mattel Intellivision"] = "intellivision"
# platforms["Magnavox Odyssey 2"] = "o2em"
# platforms["Microsoft MSX2"] = "msx2"
# platforms["Microsoft Xbox"] = "xbox"
# platforms["Moonlight"] = "moonlight"
# platforms["NEC TurboGrafx-16"] = "pcengine"
# platforms["NEC TurboGrafx-CD"] = "pcenginecd"
# platforms["Nintendo 3DS"] = "3ds"
# platforms["Nintendo 64"] = "n64"
# platforms["Nintendo DS"] = "nds"
# platforms["Nintendo Entertainment System"] = "nes"
# platforms["Nintendo Famicom Disk System"] = "fds"
# platforms["Nintendo Game Boy Advance"] = "gba"
# platforms["Nintendo Game Boy Color"] = "gbc"
# platforms["Nintendo Game Boy"] = "gb"
# platforms["Nintendo GameCube"] = "gamecube"
# platforms["Nintendo MSU-1"] = "snes-msu1"
# platforms["Nintendo Satellaview"] = "satellaview"
# platforms["Nintendo Switch"] = "switch"
# platforms["Nintendo Virtual Boy"] = "virtualboy"
# platforms["Nintendo Wii U"] = "wiiu"
# platforms["Nintendo Wii"] = "wii"
# platforms["Philips CD-i"] = "cdi"
# platforms["PICO-8"] = "pico8"
# platforms["Sammy Atomiswave"] = "atomiswave"
# platforms["Sega 32X"] = "sega32x"
# platforms["Sega CD"] = "segacd"
# platforms["Sega Dreamcast"] = "dreamcast"
# platforms["Sega Game Gear"] = "gamegear"
# platforms["Sega Genesis"] = "megadrive"
# platforms["Sega Master System"] = "mastersystem"
# platforms["Sega MSU-MD"] = "msu-md"
# platforms["Sega Model 3"] = "model3"
# platforms["Sega Naomi"] = "naomi"
# platforms["Sega Naomi 2"] = "naomi2"
# platforms["Sega Saturn"] = "saturn"
# platforms["Sega SG-1000"] = "sg1000"
# platforms["Sharp X68000"] = "x68000"
# platforms["Sinclair ZX Spectrum"] = "zxspectrum"
# platforms["SNK Neo Geo AES"] = "neogeo"
# platforms["SNK Neo Geo CD"] = "neogeocd"
# platforms["SNK Neo Geo Pocket Color"] = "ngpc"
# platforms["Sony Playstation"] = "psx"
# platforms["Sony Playstation 2"] = "ps2"
# platforms["Sony Playstation 3"] = "ps3"
# platforms["Sony Playstation Vita"] = "vita"
# platforms["Sony PSP"] = "psp"
# platforms["Super Nintendo Entertainment System"] = "snes"
# platforms["Windows"] = "steam"
# platforms["WonderSwan"] = "wswan"
# platforms["WonderSwan Color"] = "wswanc"

### Edits should not be required below here ###

processed_games = 0
processed_platforms = 0
media_copied = 0


def safe_basename(path):
    """Sanitize a game title for safe matching."""
    badchars = [":", "'", "/", "*", "?", "\"", "<", ">", "|"]
    for ch in badchars:
        path = path.replace(ch, "_")
    return path


def get_image(game_name, image_files):
    """Find the first matching media file for this game name."""
    for image_path in image_files:
        image_name = os.path.basename(image_path)
        if (image_name.startswith(game_name + "-0")
            or image_name.startswith(game_name + ".")
            or image_name.lower() == game_name.lower() + ".mp4"):
            return image_path
    return None

def save_media(original_path, output_dir, rom_basename, media_type):
    """Copy media and rename to rom_basename, ensure lowercase .png if converting."""
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    ext = os.path.splitext(original_path)[1].lower()

    # Special handling for marquees: only trim, do not convert
    if media_type == "marquee" and ext == ".png":
        new_filename = rom_basename + ".png"
        output_path = os.path.join(output_dir, new_filename)
        try:
            img = Image.open(original_path)
            # Trim the image
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            img.save(output_path, format="PNG")
        except Exception as e:
            print(f"Error trimming {original_path} to PNG: {e}")
            try:
                # fallback: just copy original file
                copy(original_path, output_path)
            except Exception as e2:
                print(f"Failed fallback copy for {original_path}: {e2}")
        return "./" + os.path.basename(output_dir) + "/" + new_filename


    # Handle conversion to png for all other image types
    if convert_to_png and ext in [".jpg", ".jpeg", ".png"]:
        new_filename = rom_basename + ".png"
        output_path = os.path.join(output_dir, new_filename)
        try:
            img = Image.open(original_path)
            # Corrected logic to preserve transparency
            if 'A' in img.getbands():
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            img.save(output_path, format="PNG")
        except Exception as e:
            print(f"Error converting {original_path} to PNG: {e}")
            try:
                # fallback: just copy original file (still renamed as .png)
                copy(original_path, output_path)
            except Exception as e2:
                print(f"Failed fallback copy for {original_path}: {e2}")
    else:
        # Keep original ext (non-image media like .mp4, .pdf)
        new_filename = rom_basename + ext
        output_path = os.path.join(output_dir, new_filename)
        if copy_media:
            try:
                copy(original_path, output_path)
            except Exception as e:
                print(f"Error copying {original_path}: {e}")

    return "./" + os.path.basename(output_dir) + "/" + new_filename


for platform_lb, platform_rp in platforms.items():
    print(f"Processing {platform_lb} → {platform_rp}")

    lb_platform_xml = fr"{lb_dir}\Data\Platforms\{platform_lb}.xml"
    lb_image_dir = fr"{lb_dir}\images\{platform_lb}\Box - Front"
    lb_wheel_dir = fr"{lb_dir}\images\{platform_lb}\Clear Logo"
    lb_screenshot_dir = fr"{lb_dir}\images\{platform_lb}\Screenshot - Gameplay"
    lb_manual_dir = fr"{lb_dir}\manuals\{platform_lb}"
    lb_video_dir = fr"{lb_dir}\videos\{platform_lb}"

    output_platform_dir = fr"{output_dir}\{platform_rp}"

    if not os.path.isdir(output_platform_dir):
        os.makedirs(output_platform_dir)

    xmltree = ET.parse(lb_platform_xml)

    # Batocera mapping
    image_maps = [
        {"type": "screenshot", "xmltag": "image", "output": "screenshots", "lbdir": lb_screenshot_dir},
        {"type": "marquee", "xmltag": "marquee", "output": "marquees", "lbdir": lb_wheel_dir},
        {"type": "box art", "xmltag": "thumbnail", "output": "covers", "lbdir": lb_image_dir},
        {"type": "manual", "xmltag": "manual", "output": "manuals", "lbdir": lb_manual_dir},
        {"type": "video", "xmltag": "video", "output": "videos", "lbdir": lb_video_dir}
    ]

    # preload all media files
    for imap in image_maps:
        imap["files"] = [f for f in glob.glob(fr"{imap['lbdir']}\**", recursive=True) if os.path.isfile(f)]

    games_found = []

    total_games_in_xml = 0
    recent_games_exported = 0

    for game in xmltree.getroot().iter("Game"):
        try:
            total_games_in_xml += 1

            rom_path = game.find("ApplicationPath").text
            rom_name = os.path.basename(rom_path)
            rom_basename = os.path.splitext(rom_name)[0]

            this_game = {"path": "./" + rom_name, "name": game.find("Title").text}

            if game.find("Notes") is not None:
                this_game["desc"] = game.find("Notes").text

            # --- Check recents_only condition ---
            is_recent = True
            if recents_only:
                date_added_elem = game.find("DateAdded")
                if date_added_elem is not None and date_added_elem.text:
                    try:
                        date_str = date_added_elem.text.strip().replace("Z", "")
                        if "T" in date_str:
                            # full datetime
                            added_date = datetime.datetime.fromisoformat(date_str.split(".")[0])
                        else:
                            # just date (YYYY-MM-DD)
                            added_date = datetime.datetime.fromisoformat(date_str + "T00:00:00")

                        days_old = (datetime.datetime.now() - added_date).days
                        is_recent = days_old <= recent_days
                    except Exception as e:
                        print(f"Warning: Could not parse DateAdded '{date_added_elem.text}' for {this_game['name']} ({e})")
                        is_recent = False
                else:
                    is_recent = False

            # --- Skip old games entirely if recents_only enabled ---
            if recents_only and not is_recent:
                continue

            # --- media ---
            for imap in image_maps:
                media_path = get_image(safe_basename(this_game["name"]), imap["files"])
                if media_path:
                    # Pass the media type to the save_media function
                    rel_path = save_media(media_path, os.path.join(output_platform_dir, imap["output"]), rom_basename, imap["type"])
                    this_game[imap["xmltag"]] = rel_path
                    media_copied += 1
                else:
                    this_game[imap["xmltag"]] = ""
                    if imap["type"] in ["screenshot", "marquee", "box art"]:
                        print(f'\tNo {imap["type"]} found for {this_game["name"]}')

            # --- metadata ---
            if game.find("StarRating") is not None:
                this_game["rating"] = str(int(game.find("StarRating").text) * 2 / 10)
            if game.find("ReleaseDate") is not None:
                this_game["releasedate"] = game.find("ReleaseDate").text.replace("-", "").split("T")[0] + "T000000"
            if game.find("Developer") is not None:
                this_game["developer"] = game.find("Developer").text
            if game.find("Publisher") is not None:
                this_game["publisher"] = game.find("Publisher").text
            if game.find("Genre") is not None:
                this_game["genre"] = game.find("Genre").text
            if game.find("MaxPlayers") is not None:
                mp = game.find("MaxPlayers").text
                this_game["players"] = "1+" if mp.startswith("0") else mp

            games_found.append(this_game)

            if copy_roms:
                copy(rom_path, output_platform_dir)

            processed_games += 1
            recent_games_exported += 1
        except Exception as e:
            print("Error processing game:", e)

    # --- Print recents summary ---
    if recents_only:
        print(f"Exported {recent_games_exported} recent games out of {total_games_in_xml} total")

    # write XML
    top = ET.Element("gameList")
    for g in games_found:
        child = ET.SubElement(top, "game")
        for key, val in g.items():
            child_content = ET.SubElement(child, key)
            child_content.text = val

    try:
        xmlstr = minidom.parseString(ET.tostring(top)).toprettyxml(indent="    ")
        # Remove the XML declaration if present
        xml_lines = xmlstr.splitlines()
        if xml_lines[0].startswith("<?xml"):
            xmlstr = "\n".join(xml_lines[1:])

        xml_outfile = os.path.join(output_platform_dir, "gamelist.xml")
        with io.open(xml_outfile, "w", encoding="utf-8") as f:
            f.write(xmlstr)
        processed_platforms += 1
    except Exception as e:
        print(f"ERROR writing gamelist XML for {platform_lb}", e)

print("----------------------------------------------------------------------")
print(f"Created {processed_platforms:,} gamelist XMLs and copied {media_copied:,} media files from {processed_games:,} games")
print("----------------------------------------------------------------------")
