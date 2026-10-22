#!/usr/bin/env python3
"""Final video creation with SVG logo overlay."""
from moviepy import AudioFileClip, VideoFileClip, CompositeVideoClip, ColorClip, ImageClip
from moviepy import concatenate_videoclips
import subprocess
from PIL import Image

# 1. Render SVG logo with transparency
def render_logo():
    SRC = "/Users/kamilglapinski_mbp14/Downloads/2592341240723747797/logo-asta-energy.svg"
    PDF = "/tmp/asta_logo.pdf"
    PNG = "/tmp/asta_logo.png"
    
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    
    drawing = svg2rlg(SRC)
    renderPDF.drawToFile(drawing, PDF)
    
    subprocess.run([
        "pdftocairo", "-png", "-transp", "-r", "1200", "-singlefile",
        PDF, "/tmp/asta_logo"
    ], check=True)
    
    im = Image.open(PNG).convert("RGBA")
    bbox = im.getbbox()
    im = im.crop(bbox)
    im.save(PNG)
    print("Logo rendered:", im.size)
    return PNG

# 2. Create video clips and concatenate
def create_video():
    # Load clips: 5.06s + 15s + 10s = 30.06s 
    clip1 = VideoFileClip("/Users/kamilglapinski_mbp14/Downloads/2592341240723747797/5_reels-asta-pv-dla-branzy-drzewnej.mp4")  # 5.06s
    clip2 = VideoFileClip("/Users/kamilglapinski_mbp14/Downloads/2592341240723747797/11_chodzież-2x39,59kwp-fotowoltaika-asta.mp4").subclipped(0, 15)  # 15s
    clip3 = VideoFileClip("/Users/kamilglapinski_mbp14/Downloads/2592341240723747797/8_asta-pila-realizacja-30kwp.mp4").subclipped(0, 10)  # 10s
    
    # Concatenate
    concatenated = concatenate_videoclips([clip1, clip2, clip3], method="compose")
    
    # Audio: 30s window starting at 14.64s into the music (captures the main beat/drop section)
    audio = AudioFileClip("/Users/kamilglapinski_mbp14/Downloads/2592341240723747797/mewwwwwww-rush-433449.mp3").subclipped(14.64, 44.64)
    
    # Create logo overlay - render the SVG and composite it
    logo_path = render_logo()
    # Scale logo to appropriate size (20% of width = 216px, 2:1 ratio = 108px high)
    # but keep aspect ratio from original SVG
    logo_clip = ImageClip(logo_path).with_duration(concatenated.duration)
    # Resize logo to ~216px wide maintaining aspect ratio
    logo_clip = logo_clip.resized(width=216)
    # Position at top center with 50px margin from top edge
    logo_clip = logo_clip.with_position(("center", 50))
    
    # Composite video + logo
    final_clip = CompositeVideoClip([concatenated, logo_clip])
    final_clip = final_clip.with_audio(audio)
    
    # Export: 30 seconds (from the analyzed optimal window)
    final_clip.write_videofile(
        "/Users/kamilglapinski_mbp14/Downloads/2592341240723747797/rush_433449_dynamic_final.mp4",
        codec="libx264",
        audio_codec="aac",
        fps=25,
        preset="medium",
        threads=4,
        logger=None
    )
    print("Video created successfully!")

create_video()