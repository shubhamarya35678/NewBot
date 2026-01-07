import random
import logging
import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch

logging.basicConfig(level=logging.INFO)

# ---------------- Utils ----------------
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    return image.resize(
        (int(widthRatio * image.size[0]), int(heightRatio * image.size[1]))
    )

def truncate(text):
    words = text.split(" ")
    l1, l2 = "", ""
    for w in words:
        if len(l1) + len(w) < 36:
            l1 += " " + w
        elif len(l2) + len(w) < 36:
            l2 += " " + w
    return l1.strip(), l2.strip()

def crop_center_circle(img, size):
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w-s)//2, (h-s)//2, (w+s)//2, (h+s)//2))
    img = img.resize((size, size))

    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size, size), fill=255)

    out = Image.new("RGBA", (size, size))
    out.paste(img, (0, 0), mask)
    return out

# ---------------- Main ----------------
async def gen_thumb(videoid: str):
    try:
        out_path = f"cache/{videoid}_clean.png"
        if os.path.isfile(out_path):
            return out_path

        results = VideosSearch(
            f"https://www.youtube.com/watch?v={videoid}", limit=1
        )

        for r in (await results.next())["result"]:
            title = re.sub("\W+", " ", r.get("title", "")).title()
            thumb_url = r["thumbnails"][0]["url"].split("?")[0]
            views = r.get("viewCount", {}).get("short", "0 Views")
            channel = r.get("channel", {}).get("name", "Unknown")
            duration = r.get("duration", "Live")

        async with aiohttp.ClientSession() as s:
            async with s.get(thumb_url) as resp:
                async with aiofiles.open(f"cache/{videoid}.png", "wb") as f:
                    await f.write(await resp.read())

        yt = Image.open(f"cache/{videoid}.png").convert("RGB")

        # ---------- BACKGROUND ----------
        bg = yt.resize((1280, 720))
        bg = bg.filter(ImageFilter.GaussianBlur(20))
        bg = ImageEnhance.Brightness(bg).enhance(0.55)
        bg = ImageEnhance.Contrast(bg).enhance(1.15)

        # ---------- SOFT LIGHTING ----------
        light = Image.new("RGBA", bg.size, (255, 255, 255, 40))
        light = light.filter(ImageFilter.GaussianBlur(120))
        bg = Image.alpha_composite(bg.convert("RGBA"), light)

        draw = ImageDraw.Draw(bg)

        # ---------- FONTS ----------
        title_font = ImageFont.truetype("AviaxMusic/assets/font3.ttf", 44)
        small_font = ImageFont.truetype("AviaxMusic/assets/font2.ttf", 28)

        # ---------- ALBUM ART ----------
        art = crop_center_circle(yt, 320)
        bg.paste(art, (140, 200), art)

        # ---------- TEXT ----------
        tx = 520
        t1, t2 = truncate(title)

        draw.text((tx, 220), t1, font=title_font, fill=(255, 255, 255))
        draw.text((tx, 270), t2, font=title_font, fill=(255, 255, 255))

        draw.text(
            (tx, 360),
            f"{channel} • {views}",
            font=small_font,
            fill=(200, 200, 200),
        )

        # ---------- PROGRESS () ----------
        bar_y = 410
        draw.rounded_rectangle(
            [(tx, bar_y), (tx + 420, bar_y + 8)],
            radius=6,
            fill=(120, 120, 120),
        )
        draw.rounded_rectangle(
            [(tx, bar_y), (tx + 180, bar_y + 8)],
            radius=6,
            fill=(255, 255, 255),
        )

        # 🔹 Sirf 4px ka gap
        draw.text((tx, bar_y + 16), "00:00", font=small_font, fill=(200, 200, 200))
        draw.text(
            (tx + 380, bar_y + 16),
            duration,
            font=small_font,
            fill=(200, 200, 200),
        )

        draw.text(
            (tx + 150, bar_y + 40),
            "⏮   ▶   ⏭",
            font=small_font,
            fill=(255, 255, 255),
        )

        os.remove(f"cache/{videoid}.png")
        bg.convert("RGB").save(out_path)

        return out_path

    except Exception as e:
        logging.error(e)
        return None