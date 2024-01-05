import glob
import io
import os
from PIL import Image, ImageOps
from shutil import copy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

# version 1.2.0
# The path to your Launchbox folder.
lb_dir = r'R:\Games\LaunchBox'

# Where to put the exported roms, images and xmls
# Copy the gamelist, roms and images to /home/<user>/RetroPie/roms. Gamelists are now saved inside each platform dir. 
output_dir = r'R:\Launchbox-Export'

# Restrict export to only Launchbox Favorites
favorites_only=False

# Retropie running on an old Pi needs small images. Images with a height or width above 500 pixels will be reduced with their aspect ratio preserved. If generating for Onion OS the images will be 250 px. 
reduce_image_size = False

# Choose *one* xml format. 
# Batocera supports more metadata types and tags, Retropie xml just supports one image type per game. 
xml_retropie = False     # boxart
xml_batocera = True    # boxart, marquee, screenshots and videos
xml_onion = False    # boxart only, 250px PNGs, miyoogamelist.xml

# Choose platforms (comment/uncomment as needed)
# The first string in each pair is the Launchbox platform filename, the second is the output platform folder name
platforms = dict()
platforms["Atari Jaguar"] = "jaguar"
platforms["Atari ST"] = "atarist"
platforms["Commodore 64"] = "c64"
platforms["Commodore Amiga"] = "amiga1200"
platforms["Atari 7800"] = "atari7800"
platforms["Arcade"] = "mame"
platforms["Microsoft Xbox 360"] = "xbox360"
platforms["Microsoft Xbox"] = "xbox"
platforms["NEC TurboGrafx-16"] = "pcengine"
platforms["NEC TurboGrafx-CD"] = "pcenginecd"
platforms["Nintendo 3DS"] = "3ds"
platforms["Nintendo 64"] = "n64"
platforms["Nintendo DS"] = "nds"
platforms["Nintendo Entertainment System"] = "nes"
platforms["Nintendo Game Boy Advance"] = "gba"
platforms["Nintendo Game Boy Color"] = "gbc"
platforms["Nintendo Game Boy"] = "gb"
platforms["Nintendo GameCube"] = "gamecube"
platforms["Nintendo Switch"] = "switch"
platforms["Nintendo Wii U"] = "wiiu"
platforms["Nintendo Wii"] = "wii"
platforms["Nintendo WiiWare"] = "wiiware"
platforms["Sega 32X"] = "sega32x"
platforms["Sega CD"] = "segacd"
platforms["Sega Dreamcast"] = "dreamcast"
platforms["Sega Game Gear"] = "gamegear"
platforms["Sega Genesis"] = "megadrive"
platforms["Sega Master System"] = "mastersystem"
platforms["Sega Saturn"] = "saturn"
platforms["SNK Neo Geo AES"] = "neogeo"
platforms["Sony Playstation 2"] = "ps2"
platforms["Sony Playstation 3"] = "ps3"
platforms["Sony Playstation Vita"] = "vita"
platforms["Sony Playstation"] = "psx"
platforms["Super Nintendo Entertainment System"] = "snes"
platforms["Sony PSP"] = "psp"


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
                # this_game["players"]="1+"
                games_found.append(this_game)                
                # copy(rom_path, output_roms_platform)
                # copy(os.path.join(lb_dir,rom_path), output_roms_platform)
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
        
