"""
LaunchBox → Batocera marquee exporter with auto-generated fallback.

For each game in the configured LaunchBox platform XML, tries to find a
"Clear Logo" image and copy it into a Batocera-style marquee folder.
If no Clear Logo exists, synthesizes a marquee PNG from the game's title
using the spiritendo.otf font (dark red fill with a white stroke).

This is a narrower variant of launchbox-export.py used specifically when
the platform's Clear Logo art is spotty (e.g. Nintendo Switch), so every
game still ends up with some form of marquee for the frontend to show.

Requirements:
    - ImageMagick installed and on PATH
    - pip install Wand Pillow
    - spiritendo.otf present in the script's working directory
"""

import io
import os
from shutil import copy
import xml.etree.ElementTree as ET
from xml.dom import minidom

from wand.color import Color
from wand.font import Font
from wand.image import Image


LB_DIR = r'R:\Games\LaunchBox'
OUTPUT_DIR = r'R:\Launchbox-Export'

PLATFORMS = {
    "Nintendo Switch": "switch",
}

MARQUEE_WIDTH, MARQUEE_HEIGHT = 800, 350

INVALID_FILENAME_CHARS = (":", "'", "/", "*")


def sanitize_filename(name: str) -> str:
    for ch in INVALID_FILENAME_CHARS:
        name = name.replace(ch, "_")
    return name


def find_media_file(game_name: str, media_files):
    sanitized = sanitize_filename(game_name)
    sanitized_lower = sanitized.lower()
    for image_path in media_files:
        image_name = os.path.basename(image_path)
        if (image_name.startswith(sanitized + "-0")
                or image_name.startswith(sanitized + ".")
                or image_name.lower() == sanitized_lower + ".mp4"):
            return image_name, image_path
    return None


def copy_media_file(original_path: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    copy(original_path, output_dir)
    return os.path.basename(original_path)


def generate_marquee(game_name: str, output_path: str) -> None:
    with Image(width=MARQUEE_WIDTH, height=MARQUEE_HEIGHT,
               background=Color('none')) as canvas:
        font = Font(
            'spiritendo.otf',
            size=0,
            color="darkred",
            stroke_color="white",
            stroke_width=3,
        )
        canvas.caption(
            game_name,
            width=MARQUEE_WIDTH,
            height=MARQUEE_HEIGHT,
            font=font,
            gravity='center',
        )
        canvas.save(filename=output_path)


def main() -> None:
    processed_games = 0
    processed_platforms = 0
    media_copied = 0

    for platform_lb, platform_rp in PLATFORMS.items():
        lb_platform_xml = rf'{LB_DIR}\Data\Platforms\{platform_lb}.xml'
        lb_wheel_dir = rf'{LB_DIR}\images\{platform_lb}\Clear Logo'
        output_roms_platform = rf'{OUTPUT_DIR}\roms\{platform_rp}'

        os.makedirs(output_roms_platform, exist_ok=True)

        images_marquee = []
        if os.path.isdir(lb_wheel_dir):
            for root, _, files in os.walk(lb_wheel_dir):
                for f in files:
                    images_marquee.append(os.path.join(root, f))

        xmltree = ET.parse(lb_platform_xml)
        games_found = []

        for game in xmltree.getroot().iter("Game"):
            try:
                title_elem = game.find("Title")
                path_elem = game.find("ApplicationPath")
                if title_elem is None or path_elem is None:
                    continue

                this_game = {
                    "path": "./" + os.path.basename(path_elem.text),
                    "name": title_elem.text,
                }

                if (notes := game.find("Notes")) is not None and notes.text:
                    this_game["desc"] = notes.text

                marquee_out_dir = os.path.join(output_roms_platform, "images_marquee")
                match = find_media_file(this_game["name"], images_marquee)
                if match is not None:
                    _, image_path = match
                    filename = copy_media_file(image_path, marquee_out_dir)
                    this_game["marquee"] = f"./images_marquee/{filename}"
                    media_copied += 1
                else:
                    print(f'\tNo marquee found for {this_game["name"]} - generating')
                    os.makedirs(marquee_out_dir, exist_ok=True)
                    sanitized = sanitize_filename(this_game["name"])
                    gen_filename = f"{sanitized}-09.png"
                    gen_path = os.path.join(marquee_out_dir, gen_filename)
                    generate_marquee(this_game["name"], gen_path)
                    this_game["marquee"] = f"./images_marquee/{gen_filename}"

                if (rating := game.find("StarRating")) is not None and rating.text:
                    this_game["rating"] = str((int(rating.text) * 2 / 10))
                if (release := game.find("ReleaseDate")) is not None and release.text:
                    this_game["releasedate"] = release.text.replace("-", "").split("T")[0] + "T000000"
                if (developer := game.find("Developer")) is not None and developer.text:
                    this_game["developer"] = developer.text
                if (publisher := game.find("Publisher")) is not None and publisher.text:
                    this_game["publisher"] = publisher.text
                if (genre := game.find("Genre")) is not None and genre.text:
                    this_game["genre"] = genre.text
                if (players := game.find("MaxPlayers")) is not None and players.text:
                    this_game["players"] = "1+" if players.text.startswith('0') else players.text

                games_found.append(this_game)
                processed_games += 1
            except Exception as e:
                print(f"Error processing game: {e}")

        top = ET.Element('gameList')
        for game_data in games_found:
            child = ET.SubElement(top, 'game')
            for key, value in game_data.items():
                field = ET.SubElement(child, key)
                field.text = value

        try:
            xmlstr = minidom.parseString(ET.tostring(top)).toprettyxml(indent="    ")
            gamelist_path = os.path.join(output_roms_platform, "gamelist.xml")
            with io.open(gamelist_path, "w", encoding="utf-8") as f:
                f.write(xmlstr)
            processed_platforms += 1
        except Exception as e:
            print(e)
            print(f'\tERROR writing gamelist XML for {platform_lb}')

    print('----------------------------------------------------------------------')
    print(f'Created {processed_platforms:,} gamelist XMLs and copied '
          f'{media_copied:,} media files from {processed_games:,} games')
    print('----------------------------------------------------------------------')


if __name__ == "__main__":
    main()
