from PIL import Image, ImageDraw

def apply_winter_theme(img, palette):
    """
    Paprastas žieminis šablonas – mėlynai balti tonai.
    """
    overlay = Image.new("RGBA", img.size, (palette[0][0], palette[0][1], palette[0][2], 60))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def apply_modern_theme(img, palette):
    """
    Modern – tamsus skaidrus sluoksnis.
    """
    overlay = Image.new("RGBA", img.size, (0,0,0,120))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def apply_pastel_theme(img, palette):
    """
    Pastelinis – labai šviesus baltas blur blokas.
    """
    overlay = Image.new("RGBA", img.size, (255,255,255,80))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def apply_template(img, palette, theme_name):
    """
    Pasirenka vieną iš šablonų.
    """
    if theme_name == "Winter":
        return apply_winter_theme(img, palette)
    elif theme_name == "Modern Dark":
        return apply_modern_theme(img, palette)
    elif theme_name == "Pastel":
        return apply_pastel_theme(img, palette)

    return img
