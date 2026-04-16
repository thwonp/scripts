"""
Minimal marquee/clear-logo renderer.

A standalone template that renders a single string ("Hello World" by
default) onto an 800x350 transparent PNG using the spiritendo.otf font,
with a dark red fill and a 4px white stroke. Output is trimmed to its
visible bounding box and written to clear_logo.png.

Used as a reference / starting point for the bulk marquee generation
logic in marquee-gen2.py. Requires ImageMagick on PATH, Wand installed
(`pip install Wand`), and spiritendo.otf next to this script.
"""

from wand.image import Image
from wand.font import Font
from wand.color import Color

w, h = 800, 350

with Image(width = w, 
            height = h, 
            background = Color('none')) as canvas: 
    font = Font('spiritendo.otf', 
                size=0,  
                color="darkred",
                stroke_color="white",
                stroke_width=4
                )
    canvas.caption('Hello World', 
                    width=w, 
                    height=h, 
                    font=font,   
                    gravity='center') 
    canvas.trim()
    canvas.save(filename='clear_logo.png')
