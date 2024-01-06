import glob
import io
import os
from PIL import Image, ImageOps
from shutil import copy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys
from wand.image import Image
from wand.font import Font
from wand.color import Color

##### Requires ImageMagick installed and added to path
##### pip install Wand 
##### spiritendo.otf font file in same dir as script
##### saves imgs in working directory of script

lb_dir = r'R:\Games\LaunchBox'
output_dir = r'R:\Launchbox-Export'

platforms = dict()
platforms["Nintendo Switch"] = "switch"

processed_games = 0
processed_platforms = 0
media_copied = 0


w, h = 800, 350


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
    output_marquee_dir = r'%s\marquee' % output_roms_platform

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

    image_maps = [{"type": "marquee", "xmltag": "marquee", "output_dir": "images_marquee", "lb_media_dir": lb_wheel_dir, "lb_media_files": images_marquee}]
    
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
        filename = os.path.basename(r'%s' % original_path)
        output_path = os.path.join(output_dir, filename)          
        copy(r'%s' % original_path, r'%s' % output_dir)
        return os.path.basename(output_path)

    for game in xmltree.getroot().iter("Game"):        
        this_game = dict()
        try:
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
                    print('Generating Marquee...')
                    gameName=this_game["name"]
                    tmpname = gameName.replace(":","_")
                    tmpname = tmpname.replace("'","_")
                    tmpname = tmpname.replace("/","_")
                    tmpname = tmpname.replace("*","_")
                    tmpfilename=tmpname + "-09.png"
                    print(tmpfilename)
                    with Image(width = w, 
                            height = h, 
                            background = Color('none')) as canvas: 
                            font = Font('spiritendo.otf', 
                                            size=0,  
                                            color="darkred",
                                            stroke_color="white",
                                            stroke_width=3
                                            )
                            canvas.caption(gameName, 
                                            width=w, 
                                            height=h, 
                                            font=font,   
                                            gravity='center') 
                            # canvas.trim()
                            canvas.save(filename=tmpfilename)
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
