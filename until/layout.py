from PIL import Image, ImageDraw, ImageFont
import os

def draw_text_auto(img, text, font_path="Roboto-Bold.ttf"):
    """
    Automatiškai deda tekstą į apatines 40% vaizdo, centras.
    Vėliau galima sukurti sudėtingesnį AI layout.
    """
    W, H = img.size
    draw = ImageDraw.Draw(img)

    # Šrifto dydis pagal vaizdo aukštį
    font_size = int(H * 0.05)
    fallback_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        if not os.path.exists(font_path):
            font = ImageFont.truetype(fallback_font, font_size)
        else:
            font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.truetype(fallback_font, font_size)

    w, h = draw.textsize(text, font=font)
    position = ((W - w) / 2, H * 0.60)

    # Teksto fonas (lengvas permatomumas)
    overlay = Image.new("RGBA", (w+60, h+40), (0,0,0,150))
    img.paste(overlay, (int(position[0]-30), int(position[1]-20)), overlay)

    draw.text(position, text, fill="white", font=font)

    return img
