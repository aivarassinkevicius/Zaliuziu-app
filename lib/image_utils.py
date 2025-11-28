from PIL import Image, ImageDraw, ImageFont
from typing import Tuple

def add_marketing_overlay(image: Image.Image, text: str, font_path: str = None) -> Image.Image:
    """
    Adds a marketing overlay with the given text to the image.
    Args:
        image: The input PIL Image.
        text: The text to overlay.
        font_path: Optional path to a .ttf font file.
    Returns:
        Image.Image: The image with the overlay applied.
    """
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    font = load_font(font_path, 32)
    text_width, text_height = draw.textsize(text, font=font)
    x = (overlay.width - text_width) // 2
    y = overlay.height - text_height - 20
    draw.rectangle([(x-10, y-10), (x+text_width+10, y+text_height+10)], fill=(0,0,0,128))
    draw.text((x, y), text, font=font, fill=(255,255,255,255))
    return overlay

def load_font(font_path: str = None, size: int = 32) -> ImageFont.FreeTypeFont:
    """
    Loads a font for drawing text on images.
    Args:
        font_path: Path to a .ttf font file. If None, uses default PIL font.
        size: Font size.
    Returns:
        ImageFont.FreeTypeFont: The loaded font object.
    """
    try:
        if font_path:
            return ImageFont.truetype(font_path, size)
    except Exception:
        pass
    return ImageFont.load_default()

def create_social_template(image: Image.Image, template_color: Tuple[int, int, int] = (30, 144, 255)) -> Image.Image:
    """
    Creates a social media template overlay on the image.
    Args:
        image: The input PIL Image.
        template_color: RGB color for the template overlay.
    Returns:
        Image.Image: The image with the social template applied.
    """
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    bar_height = int(overlay.height * 0.15)
    draw.rectangle([(0, overlay.height - bar_height), (overlay.width, overlay.height)], fill=template_color + (128,))
    return overlay
