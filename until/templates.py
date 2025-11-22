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


def apply_modern_blue(img, palette):
    """
    Modern Blue – tamsus šviesus sluoksnis.
    """
    overlay = Image.new("RGBA", img.size, (40,80,180,120))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def apply_modern_red(img, palette):
    """
    Modern Red – tamsus šviesus sluoksnis.
    """
    overlay = Image.new("RGBA", img.size, (180,40,40,120))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def apply_modern_green(img, palette):
    """
    Modern Green – tamsus šviesus sluoksnis.
    """
    overlay = Image.new("RGBA", img.size, (40,180,80,120))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def apply_modern_gradient(img, palette):
    """
    Modern Gradient – tamsus šviesus sluoksnis.
    """
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size)
    draw = ImageDraw.Draw(overlay)
    for y in range(img.size[1]):
        color = (
            int(40 + (180-40)*y/img.size[1]),
            int(80 + (40-80)*y/img.size[1]),
            int(180 - (180-40)*y/img.size[1]),
            100
        )
        draw.line([(0, y), (img.size[0], y)], fill=color)
    return Image.alpha_composite(base, overlay)


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
    elif theme_name == "Modern Blue":
        return apply_modern_blue(img, palette)
    elif theme_name == "Modern Red":
        return apply_modern_red(img, palette)
    elif theme_name == "Modern Green":
        return apply_modern_green(img, palette)
    elif theme_name == "Modern Gradient":
        return apply_modern_gradient(img, palette)
    elif theme_name == "Pastel":
        return apply_pastel_theme(img, palette)

    return img
