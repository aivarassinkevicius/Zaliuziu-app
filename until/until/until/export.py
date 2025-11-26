from PIL import Image

SOCIAL_SIZES = {
    "Instagram Square": (1080,1080),
    "Instagram Story": (1080,1920),
    "Facebook Post": (1200,628),
    "Pinterest Vertical": (1000,1500)
}

def resize_for_social(img, format_name):
    if format_name not in SOCIAL_SIZES:
        return img
    return img.resize(SOCIAL_SIZES[format_name], Image.LANCZOS)
