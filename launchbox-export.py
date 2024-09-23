import glob
import io
import os
from PIL import Image, ImageOps
from shutil import copy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

# version 2.0
# This script is a heavy modification of a script on the LaunchBox forums:
# https://forums.launchbox-app.com/files/file/860-launchbox-retropie-batocera-miyoo-export/
# I added Manuals to the media map, added multiple platforms, and added functionality to rename all media to match the ROM names for use on various platforms, along with some general refactoring.

# The path to your Launchbox folder.
lb_dir = r'R:\Games\LaunchBox'

# Where to put the exported roms, images and xmls
# Copy the gamelist, roms and images to /home/<user>/RetroPie/roms. Gamelists are now saved inside each platform dir. 
output_dir = r'R:\Launchbox-Export'
rename_parent_dir = r'R:\Launchbox-Export-Rename'
gamelist_dir = f'{output_dir}{'\\'}{'roms'}'

# Restrict export to only Launchbox Favorites
favorites_only = False

# Retropie running on an old Pi needs small images. Images with a height or width above 500 pixels will be reduced with their aspect ratio preserved. If generating for Onion OS the images will be 250 px. 
reduce_image_size = False

copy_roms = False
copy_media = True

# Choose *one* xml format. 
# Batocera supports more metadata types and tags, Retropie xml just supports one image type per game. 
xml_retropie = False     # boxart
xml_batocera = True    # boxart, marquee, screenshots, videos, and manuals
xml_onion = False    # boxart only, 250px PNGs, miyoogamelist.xml

# Choose platforms (comment/uncomment as needed)
# The first string in each pair is the Launchbox platform filename, the second is the output platform folder name
platforms = dict()
# platforms["3DO Interactive Multiplayer"] = "3do"
# platforms["Arcade"] = "mame"
# platforms["Arcade - FBNeo"] = "fbneo"
# platforms["Atari 2600"] = "atari2600"
# platforms["Atari 7800"] = "atari7800"
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
platforms["Nintendo Game Boy"] = "gb"
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

### edits should not be required below here ###

if sum([xml_retropie, xml_batocera, xml_onion]) > 1:
    print("Choose only a single xml format")
    sys.exit(-1)
if not xml_retropie and not xml_batocera and not xml_onion:
    print("Choose an xml format")
    sys.exit(-1)

processed_games = 0
processed_platforms = 0
media_copied = 0

for platform in platforms.keys():
    platform_lb=platform
    platform_rp=platforms[platform]
    lb_platform_xml = r'%s\Data\Platforms\%s.xml' % (lb_dir, platform_lb)
    lb_image_dir = r'%s\images\%s\Box - Front' % (lb_dir, platform_lb)
    lb_wheel_dir = r'%s\images\%s\Clear Logo' % (lb_dir, platform_lb)
    lb_3dbox_dir = r'%s\images\%s\Box - 3D' % (lb_dir, platform_lb)
    lb_screenshot_dir = r'%s\images\%s\Screenshot - Gameplay' % (lb_dir, platform_lb)
    lb_manual_dir = r'%s\manuals\%s' % (lb_dir, platform_lb)
    lb_video_dir = r'%s\videos\%s' % (lb_dir, platform_lb)
    output_roms = r'%s\roms' % output_dir
    output_roms_platform = r'%s\%s' % (output_roms, platform_rp)
    output_image_dir = r'%s\images' % output_roms_platform
    output_box3d_dir = r'%s\box3d' % output_roms_platform
    output_marquee_dir = r'%s\marquee' % output_roms_platform
    output_screenshots_dir = r'%s\screenshots' % output_roms_platform

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        
    if not os.path.isdir(output_roms):
        os.makedirs(output_roms)  
        
    if not os.path.isdir(output_roms_platform):
        os.makedirs(output_roms_platform)               
       
    xmltree = ET.parse(lb_platform_xml)
    games_found = []
    images_marquee = []
    images_box3d = []
    images_screenshots = []
    videos = []
    images = []
    manuals = []

    if xml_batocera:
        image_maps = [{"type": "screenshot", "xmltag": "image", "output_dir": "images_screenshot", "lb_media_dir": lb_screenshot_dir, "lb_media_files": images_screenshots},
                      {"type": "marquee", "xmltag": "marquee", "output_dir": "images_marquee", "lb_media_dir": lb_wheel_dir, "lb_media_files": images_marquee},
                      {"type": "box art", "xmltag": "thumbnail", "output_dir": "images_boxart", "lb_media_dir": lb_image_dir, "lb_media_files": images},
                      {"type": "manual", "xmltag": "manual", "output_dir": "manuals", "lb_media_dir": lb_manual_dir, "lb_media_files": manuals},
                      {"type": "video", "xmltag": "video", "output_dir": "video", "lb_media_dir": lb_video_dir, "lb_media_files": videos}
                      ]
    elif xml_retropie:
        image_maps = [{"type": "box art", "xmltag": "image", "output_dir": "images", "lb_media_dir": lb_image_dir, "lb_media_files": images},                      
                      ]
    elif xml_onion: 
            image_maps = [{"type": "box art", "xmltag": "image", "output_dir": "Imgs", "lb_media_dir": lb_image_dir, "lb_media_files": images},                      
                      ]
    for image_map in image_maps:          
        for fname in glob.glob(r'%s\**' % image_map["lb_media_dir"], recursive=True):
            img_path = os.path.join(image_map["lb_media_dir"], fname)
            if not os.path.isdir(img_path):
                image_map["lb_media_files"].append(img_path)

    def get_image(game_name, image_files):
        game_name = game_name.replace(":","_")
        game_name = game_name.replace("'","_")
        game_name = game_name.replace("/","_")
        game_name = game_name.replace("*","_")
        game_name = game_name.replace("?","_")
        for image_path in image_files:
            image_name = os.path.basename(r'%s' % image_path)
            if image_name.startswith(game_name + '-0') or image_name.startswith(game_name + '.') or image_name.lower() == game_name.lower() + '.mp4':
                return [image_name, image_path]
    
    def save_image(original_path, output_dir):
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        # if original_path.lower().endswith('mp4'):
        #     copy(r'%s' % original_path, r'%s' % output_dir)
        #     return
        if reduce_image_size:            
            try:
                filename = os.path.basename(r'%s' % original_path)
                original_image = Image.open(r'%s' % original_path)
                original_image.load
                width = int(original_image.size[0])
                height = int(original_image.size[1])
                ratio = 0
                max_dimension = 500
                if xml_onion:
                    max_dimension = 250
                if (width > max_dimension):
                    ratio = width/max_dimension
                elif (height > max_dimension):
                    ratio = height/max_dimension                
                if ratio > 0:
                    width = int(width / ratio)
                    height = int(height / ratio)
                    size = (width, height)                   
                    resized_image = original_image.resize(size, Image.LANCZOS)
                    resized_image = resized_image.convert('RGB')
                    output_path = os.path.join(output_dir, filename)
                    output_path = os.path.splitext(output_path)[0] + ".png"
                    resized_image.save(output_path, format="PNG")                    
                else:                    
                    copy(r'%s' % original_path, r'%s' % output_dir)              
            except Exception as e:
                print(r'Couldnt resize image, copying as is: %s' % original_path)
                copy(r'%s' % original_path, r'%s' % output_dir)
                print(e)
        else:  
            filename = os.path.basename(r'%s' % original_path)
            output_path = os.path.join(output_dir, filename)     
            if (copy_media == True):      
                copy(r'%s' % original_path, r'%s' % output_dir)
        return os.path.basename(output_path)    
    for game in xmltree.getroot().iter("Game"):        
        this_game = dict()
        try:
            favorite_element = game.find("Favorite")
            if (favorites_only == False) or (favorites_only == True and favorite_element is not None and favorite_element.text == 'true'):                                
                # print("%s: %s" % (platform_lb, game.find("Title").text))                
                rom_path = game.find("ApplicationPath").text        
                this_game["path"]="./" + os.path.basename(r'%s' % game.find("ApplicationPath").text)
                this_game["name"]=game.find("Title").text
                if not game.find("Notes") is None:
                    this_game["desc"]=game.find("Notes").text                
                for image_map in image_maps:                    
                    try:
                        image_info = get_image(this_game["name"], image_map["lb_media_files"])                            
                        image_file = image_info[0]
                        image_path = image_info[1]                             
                        new_image_filename = save_image(image_path, output_roms_platform + os.sep + image_map["output_dir"])
                        this_game[image_map["xmltag"]]="./" + image_map["output_dir"] + "/" + new_image_filename
                        media_copied += 1
                    except:                        
                        print(f'\tNo {image_map["type"]} found for {this_game["name"]}')
                        this_game[image_map["xmltag"]]=""
                if not game.find("StarRating") is None:    
                    this_game["rating"]=str((int(game.find("StarRating").text)*2/10))
                if not game.find("ReleaseDate") is None:
                    this_game["releasedate"]=game.find("ReleaseDate").text.replace("-","").split("T")[0] + "T000000"
                if not game.find("Developer") is None:
                    this_game["developer"]=game.find("Developer").text
                if not game.find("Publisher") is None: 
                    this_game["publisher"]=game.find("Publisher").text
                if not game.find("Genre") is None:
                    this_game["genre"]=game.find("Genre").text
                if not game.find("MaxPlayers") is None:
                    if game.find("MaxPlayers").text.startswith('0'):
                        this_game["players"]="1+"
                    else:      
                        this_game["players"]=game.find("MaxPlayers").text
                games_found.append(this_game)

                if (copy_roms == True): 
                    copy(rom_path, output_roms_platform)
                    copy(os.path.join(lb_dir,rom_path), output_roms_platform)

                processed_games += 1           
        except Exception as e:            
            print(e)
            
    top = ET.Element('gameList')
    for game in games_found:
        child = ET.SubElement(top, 'game')
        for key in game.keys():
            child_content = ET.SubElement(child, key)    
            child_content.text = game[key]

    try:
        xmlstr = minidom.parseString(ET.tostring(top)).toprettyxml(indent="    ")
        gamelist_xml = "gamelist.xml"
        if xml_onion:
            gamelist_xml = "miyoogamelist.xml"
        this_output_xml_filename = output_roms_platform + os.sep + gamelist_xml        
        with io.open(this_output_xml_filename, "w", encoding="utf-8") as f:
            f.write(xmlstr)
        processed_platforms += 1            
    except Exception as e:            
        print(e)
        print(f'\tERROR writing gamelist XML for {platform}')
    
    
print('----------------------------------------------------------------------')
print(f'Created {processed_platforms :,} gamelist XMLs and copied {media_copied :,} media files from {processed_games :,} games')
print('----------------------------------------------------------------------')

print('----------------------------------------------------------------------')
print(f'Starting rename function')
print('----------------------------------------------------------------------')
        
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
    xmlfile = f'{gamelist_dir}{'\\'}{platform}{'\\'}{'gamelist.xml'}'
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
                input_filepath = f'{gamelist_dir}{'\\'}{platform}{'\\'}{media_filename_trimmed}'
                new_filename = f'{media_dir}{'\\'}{basename}{extension}'
                # print("DEBUG: Game Title: ", basename)
                # print("DEBUG: Old Filename: ", input_filepath)
                # print("DEBUG: New Filename: ", new_filename)
                copy(input_filepath, new_filename)
            else: 
                print("INFO: No ", media, " XML entry found for ", basename)

# Create the parent output directory if missing
create_missing_dir(rename_parent_dir)

# Iterate through each platform under input_roms_dir
for platform in os.listdir(gamelist_dir):
    # Create subdirectory for the platform
    output_platform_dir = f'{rename_parent_dir}{'\\'}{platform}'
    create_missing_dir(output_platform_dir)
    # Begin parsing the xml
    print("Copying renamed media for: ", platform)
    parse_xml(platform)

print('----------------------------------------------------------------------')
print(f'Fixing XML gamelists')
print('----------------------------------------------------------------------')

# Dictionary of media tags to search in the gamelist.xml
media_tags = {
    'image' : 'screenshots',
    'marquee' : 'marquees',
    'thumbnail' : 'covers',
    'manual' : 'manuals',
    'video' : 'videos'
} 

def parse_xml(platform):
    xmlfile = f'{gamelist_dir}{'\\'}{platform}{'\\'}{'gamelist.xml'}'
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
            media_element_orig=game.find(media)
            media_element=game.find(media).text
            print(media_element)
            if media_element is not None:
                extension = os.path.splitext(media_element)[1]
                print("TEST: FOUND", media_element)
                new_element = str('./' + media_tags[media] + '/' + basename + extension)
                media_element_orig.text = new_element
                
            else: 
                print("INFO: No ", media, " XML entry found for ", basename)
    xmlfile = f'{rename_parent_dir}{'\\'}{platform}{'\\'}{'gamelist.xml'}'
    xmltree.write(xmlfile)
    # copy(xmlfile, os.path.join(rename_parent_dir, platform, xmlfile))
        

# Iterate through each platform under input_roms_dir
for platform in os.listdir(gamelist_dir):
    # Create subdirectory for the platform
    # Begin parsing the xml
    print("Parsing: ", platform)
    parse_xml(platform)
