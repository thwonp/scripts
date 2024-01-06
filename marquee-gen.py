from wand.image import Image
from wand.drawing import Drawing
from wand.font import Font
from wand.color import Color
  
w, h = 800, 350

with Image(width = w, 
            height = h, 
            background = Color('none')) as canvas: 
    with Drawing() as content:
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
