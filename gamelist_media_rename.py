import xml.etree.ElementTree as ET
import os
import sys
from shutil import copy

# version 0.1 
# This is a quick and dirty script I used to rename EmulationStation scraped media 1:1 with their ROM filenames.
# - Iterates through all platforms in your roms directory
# - - Parses their gamelist.xml file
# - - - ...and uses the XML tags to create a copy of each media file using the ROM filename 
#  
# Windows is the assumed platform - '\' directory separators in use.
#
# This script expects an input 'roms' directory with contents structured like so:
## roms\ 
##   platform \
##     -> gamelist.xml
##     some_media_folder(s)\
##       -> Ttris.jpg

# Define your roms directory here
input_roms_dir = r'E:\Games\roms'

# Base directory to save your freshly renamed files
output_parent_dir = r'E:\tmp\gamelist_media_rename'

# Dictionary of media tags to search in the gamelist.xml / their destination output subfolder  
media_tags = {
    'image' : 'screenshots',
    'marquee' : 'marquees',
    'thumbnail' : 'covers',
    'manual' : 'manuals',
    'video' : 'videos'
} 

def create_missing_dir(dir):
    if not os.path.isdir(dir):
        os.makedirs(dir)

def parse_xml(platform):
    xmlfile = f'{input_roms_dir}{'\\'}{platform}{'\\'}{'gamelist.xml'}'
    if not os.path.exists(xmlfile):
        print("Error: Could not find a gamelist.xml file for ", platform)
        sys.exit(-1)
    xmltree = ET.parse(xmlfile)
    root = xmltree.getroot()

    # Iterate over each <game> in the XML file
    for game in root.iter('game'):
        # Access the <path> element for the ROM filename
        filename = game.find('path').text
        # Remove trailing file extension and leading './'
        basename = os.path.splitext(filename)[0].replace('./', '')

        # For each game, iterate over the dictionary of media types
        for media in media_tags.keys():
            # Try to access the XML tag value for each media type, skip any missing elements
            media_input_filename=game.find(media).text
            if media_input_filename is not None:
                # Create output subdirectory for this media type
                media_dir = f'{output_platform_dir}{'\\'}{media_tags[media]}'
                create_missing_dir(media_dir)
                # typecast to string and remove leading './'
                media_filename_trimmed = str(media_input_filename).replace('./', '').replace('/', '\\')
                # media_basename = os.path.splitext(media_filename_trimmed)[0].split('\\')[-1]
                extension = os.path.splitext(media_filename_trimmed)[1]
                input_filepath = f'{input_roms_dir}{'\\'}{platform}{'\\'}{media_filename_trimmed}'
                new_filename = f'{media_dir}{'\\'}{basename}{extension}'
                # print("DEBUG: Game Title: ", basename)
                # print("DEBUG: Old Filename: ", input_filepath)
                # print("DEBUG: New Filename: ", new_filename)
                copy(input_filepath, new_filename)
            else: 
                print("INFO: No ", media, " XML entry found for ", basename)

# Create the parent output directory if missing
create_missing_dir(output_parent_dir)

# Iterate through each platform under input_roms_dir
for platform in os.listdir(input_roms_dir):
    # Create subdirectory for the platform
    output_platform_dir = f'{output_parent_dir}{'\\'}{platform}'
    create_missing_dir(output_platform_dir)
    # Begin parsing the xml
    print("Copying renamed media for: ", platform)
    parse_xml(platform)
