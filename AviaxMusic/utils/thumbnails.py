import os
import re
import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from py_yt import VideosSearch
from AnonXMusic import app
from config import YOUTUBE_IMG_URL

# Helper to resize images maintaining aspect ratio
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage

# Helper to make circular images (used for User PFP)
def circle(img): 
    h, w = img.size 
    a = Image.new('L', [h, w], 0) 
    b = ImageDraw.Draw(a) 
    b.pieslice([(0, 0), (h, w)], 0, 360, fill=255, outline="white") 
    c = np.array(img) 
    d = np.array(a) 
    e = np.dstack((c, d)) 
    return Image.fromarray(e)

# Helper to truncate long titles
def clear(text):
    list = text.split(" ")
    title = ""
    for i in list:
        if len(title) + len(i) < 50:
            title += " " + i
    return title.strip()

async def get_thumb(videoid, user_id):
    if os.path.isfile(f"cache/{videoid}_{user_id}.png"):
        return f"cache/{videoid}_{user_id}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub("\W+", " ", title)
                title = title.title()
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown Mins"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                views = result["viewCount"]["short"]
            except:
                views = "Unknown Views"
            try:
                channel = result["channel"]["name"]
            except:
                channel = "Unknown Channel"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        # Download User Profile Pic
        try:
            async for photo in app.get_chat_photos(user_id, 1):
                sp = await app.download_media(photo.file_id, file_name=f'{user_id}.jpg')
        except:
            async for photo in app.get_chat_photos(app.id, 1):
                sp = await app.download_media(photo.file_id, file_name=f'{app.id}.jpg')

        # Load Images
        xp = Image.open(sp)
        youtube = Image.open(f"cache/thumb{videoid}.png")

        # --- GRAPHICS PROCESSING START ---

        # 1. Create Background (Dark & Blurred)
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(25)) # Increased blur
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.6) # Darken background

        draw = ImageDraw.Draw(background)

        # 2. Define Fonts
        # Using font2 for Bold/Headings and font for standard text
        font_large = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 80)
        font_med = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 50)
        font_small = ImageFont.truetype("AnonXMusic/assets/font.ttf", 35)
        font_title = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 45)

        # 3. The "Card" (White Rounded Border in Center)
        # Coordinates: [Left, Top, Right, Bottom]
        box_coords = [(150, 100), (1130, 480)]
        draw.rounded_rectangle(box_coords, radius=30, outline="white", width=6)

        # 4. Content Inside the Card

        # Right Side: YouTube Thumbnail (Clean)
        # Resize thumbnail to fit height of box (380px height)
        thumb_h = 360
        thumb_ratio = youtube.width / youtube.height
        thumb_w = int(thumb_h * thumb_ratio)
        clean_thumb = youtube.resize((thumb_w, thumb_h))
        # Paste inside right side of box
        background.paste(clean_thumb, (1130 - thumb_w - 10, 110))

        # Left Side: "NOW PLAYING" text (Gold Color) and User PFP
        # Hex for that Bollywood Gold: #FFCC00
        gold_color = (255, 204, 0)

        draw.text((190, 130), "NOW", fill=gold_color, font=font_large)
        draw.text((190, 210), "PLAYING", fill=gold_color, font=font_large)

        # User PFP (Small Circle) and Name
        user_pfp = changeImageSize(80, 80, circle(xp))
        background.paste(user_pfp, (190, 380), mask=user_pfp)

        draw.text((290, 400), f"Requested By", fill="white", font=ImageFont.truetype("AnonXMusic/assets/font.ttf", 25))
        # We can add app name or more info here if needed

        # 5. Bottom Section (Outside Card)

        # Title
        draw.text((150, 520), clear(title), fill="white", font=font_title)

        # Channel | Views
        draw.text((150, 580), f"{channel}  |  {views[:23]}", fill="silver", font=font_small)

        # 6. Progress Bar (Bottom)
        # White line across
        draw.line([(150, 660), (1130, 660)], fill="gray", width=4)

        # Indicator Circle (at start 00:00)
        draw.ellipse([(140, 650), (160, 670)], fill="white", outline="white")

        # Timestamps
        draw.text((140, 685), "00:00", fill="white", font=font_small)
        draw.text((1050, 685), duration, fill="white", font=font_small)

        # --- GRAPHICS PROCESSING END ---

        try:
            os.remove(f"cache/thumb{videoid}.png")
            os.remove(sp)
        except:
            pass

        background.save(f"cache/{videoid}_{user_id}.png")
        return f"cache/{videoid}_{user_id}.png"
    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL