from PIL import Image, ImageDraw, ImageFont

def draw_text_auto(img, text, font_path="Roboto-Bold.ttf"):
    """
    Automatiškai deda tekstą į apatines 40% vaizdo, centras.
    Vėliau galima sukurti sudėtingesnį AI layout.
    """
    W, H = img.size
    draw = ImageDraw.Draw(img)

    # Šrifto dydis pagal vaizdo aukštį
    font = ImageFont.truetype(font_path, int(H * 0.05))
    w, h = draw.textsize(text, font=font)

    position = ((W - w) / 2, H * 0.60)

    # Teksto fonas (lengvas permatomumas)
    overlay = Image.new("RGBA", (w+60, h+40), (0,0,0,150))
    img.paste(overlay, (int(position[0]-30), int(position[1]-20)), overlay)

    draw.text(position, text, fill="white", font=font)

    return img
