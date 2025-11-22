import streamlit as st
import io, os, base64
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter
import random

# Bandome importuoti camera input (jei neveiks, praleidžia)
try:
    from streamlit_camera_input_live import camera_input_live
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ---------- Nustatymai ----------
load_dotenv()

# Version: 2.4-dev - Social Media Template Generator
# NEW: create_social_template() function for 1080x1080 Instagram templates
# Bandome gauti API raktą iš .env failo (vietinis) arba Streamlit secrets (cloud)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    # Jei vietiniai aplinkos kintamieji nėra, bandome Streamlit secrets
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        pass

if not api_key:
    st.error("❌ OpenAI API raktas nerastas! Patikrinkite konfigūraciją.")
    st.stop()

client = OpenAI(api_key=api_key)

st.set_page_config(
    page_title="Žaliuzių turinio kūrėjas", 
    page_icon="🌞", 
    layout="wide"
)

st.title("🌿 Žaliuzių & Roletų turinio kūrėjas")
st.caption("Įkelk iki 4 nuotraukų ir gauk paruoštus įrašus socialiniams tinklams.")

# ---------- Pagalbinės funkcijos ----------

def add_marketing_overlay(image_file, add_watermark=False, add_border=False, brightness=1.0, contrast=1.0, saturation=1.0, watermark_text="", watermark_size=150):
    """
    Prideda marketinginius elementus prie nuotraukos:
    - Vandens ženklą (ryškų, baltą su šešėliu)
    - Rėmelį
    - Spalvų koregavimą (šviesumas, kontrastas, sodrumas)
    """
    try:
        from PIL import ImageEnhance, ImageDraw, ImageFont, ImageFilter
        
        # Atidarome nuotrauką
        img = Image.open(image_file)
        
        # Konvertuojame į RGB jei reikia
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Spalvų koregavimai
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation)
        
        # Pridedame rėmelį
        if add_border:
            from PIL import ImageOps
            border_color = (255, 255, 255)  # Baltas rėmelis
            border_width = 20
            img = ImageOps.expand(img, border=border_width, fill=border_color)
        
        # Vandens ženklas (RYŠKUS IR REGULIUOJAMAS DYDIS)
        if add_watermark and watermark_text:
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            # PAPRASTA formulė: watermark_size procentai tiesiai nuo mažesnio nuotraukos matmens
            # pvz: 1000px nuotrauka, 80% slider → 800px šrifto aukštis (per didelis!)
            # Geriau: 1000px, 80 slider → 80px šriftas (normalus)
            # TIESIAI: slider reikšmė = px dydis
            font_size = max(30, int(watermark_size))
            
            # Bandome įkelti geresnį fontą (PRIORITY: Bold)
            font = None
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold (Windows)
                "C:/Windows/Fonts/arial.ttf",    # Arial Regular
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux Bold
                "/System/Library/Fonts/Helvetica.ttc"  # Mac
            ]
            
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
            
            # Jei niekas neveikė - sukuriame DIDELĮ default
            if font is None:
                font = ImageFont.load_default()
                # Default font nemažas - pakartojame tekstą kad būtų didesnis
                watermark_text = watermark_text * 2
            
            # Pozicija - dešiniame apatiniame kampe
            try:
                text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            except:
                text_bbox = (0, 0, len(watermark_text) * 10, 20)
            
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = width - text_width - 30
            y = height - text_height - 30
            
            # Piešiame STORESNI šešėlį (juodą)
            for offset in [(3, 3), (2, 2), (1, 1), (4, 4)]:
                draw.text((x + offset[0], y + offset[1]), watermark_text, fill=(0, 0, 0), font=font)
            
            # Piešiame BALTĄ RYŠKŲ tekstą
            draw.text((x, y), watermark_text, fill=(255, 255, 255), font=font)
        
        # Išsaugome į bytes su AUKŠTA kokybe
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=98, optimize=False)
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Klaida redaguojant nuotrauką: {e}")
        import traceback
        st.error(traceback.format_exc())
        image_file.seek(0)
        return image_file

def analyze_image(image_bytes):
    """Naudoja GPT-4o-mini vaizdo analizei su konkrečiu produktų atpažinimu"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Tu esi langų uždangalų ir žaliuzių produktų atpažinimo EKSPERTAS. 
Tavo užduotis - TIKSLIAI ir DETALIZUOTAI identifikuoti KIEKVIENĄ produktą nuotraukoje."""},
            {"role": "user", "content": [
                {"type": "text", "text": """Analizuok šią nuotrauką kaip ŽALIUZIŲ EKSPERTAS ir BŪTINAI nurodyk:

1. **PRODUKTO TIPAS IR KIEKIS** (labai svarbu!):
   ⚠️ Jei matai KELIS skirtingus produktus - BŪTINAI aprašyk KIEKVIENĄ ATSKIRAI!
   Produktų tipai:
   - Roletai (tekstiliniai, roll-up blinds)
   - Roletai Diena-Naktis / Zebra (duo blinds su juostelėmis)
   - Horizontalios žaliuzės / Venetian (horizontalios lamelės)
   - Vertikalios žaliuzės (vertikalios lamelės)
   - Plisuotos žaliuzės / Pleated (sulankstomos)
   - Medinės žaliuzės / Wood blinds (medžio lamelės)
   - Romanetės / Roman shades
   - Lamelės / Panel blinds
   - Užuolaidos / Curtains

2. **SPALVOS, MEDŽIAGA, TEKSTŪRA**:
   - Tikslios spalvos (balta, pilka, smėlio, mėlyna, etc.)
   - Medžiaga (medis, audinys, PVC, aliuminis)
   - Ar matinė, blizgi, skaidri, tamsinanti

3. **MONTAVIMO VIETA IR KAMBARYS**:
   - Kokio tipo kambarys (svetainė, miegamasis, virtuvė, biuras)
   - Kaip sumontuota (sienoje, lubose, lange)

4. **VIZUALINĖS DETALĖS**:
   - Apšvietimas (dienos šviesa, dirbtinė)
   - Interjero stilius
   - Vandens ženklas ar tekstas (jei yra)
   - Vaizdas pro langą

PRIVALOMA: Pradėk aprašymą nuo TIKSLAUS produkto tipo. 
Pavyzdys: "Nuotraukoje matosi TRYS SKIRTINGI PRODUKTAI: 1) PLISUOTOS ŽALIUZĖS pilkos spalvos, 2) MEDINĖS HORIZONTALIOS ŽALIUZĖS šviesaus ąžuolo, 3) ROLETAI DIENA-NAKTIS balti..." """},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_bytes}}
            ]}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def generate_captions(analysis_text, season, holiday):
    """Sukuria 3 teksto variantus lietuviškai pagal tikslią produkto analizę"""
    
    # ULTRA GRIEŽTA sezonų ir švenčių kontrolė
    season_data = {
        "Pavasaris": {
            "must_have": ["pavasari", "atsinaujinim", "šviesi", "gaivu", "pavasario"],
            "forbidden": ["žiem", "šalt", "snieg", "kalėd", "ruduo", "ruden", "vasara", "vasar", "karšt"],
            "message": "pavasario gaivumą ir šviesumą"
        },
        "Vasara": {
            "must_have": ["vasara", "vasar", "saulė", "šilum", "vėsin", "karšt"],
            "forbidden": ["žiem", "šalt", "snieg", "kalėd", "pavasa", "ruduo", "ruden"],
            "message": "vasaros šviesumą ir vėsumą"
        },
        "Ruduo": {
            "must_have": ["ruden", "jauk", "šilt", "rudeni", "ruduo"],
            "forbidden": ["žiem", "kalėd", "pavasa", "vasara", "karšt", "sniegas"],
            "message": "rudenio jaukumą"
        },
        "Žiema": {
            "must_have": ["žiem", "šalt", "šilum", "kalėd"],
            "forbidden": ["pavasa", "vasara", "ruden", "karšt", "velyk"],
            "message": "žiemos šilumą"
        }
    }
    
    # Švenčių kontrolė - VISOS ŠVENTĖS
    holiday_data = {
        "Naujieji metai": {
            "must_have": ["nauj metin", "nauj met", "2025", "2026"],
            "forbidden": ["kalėd", "velyk", "vasara"],
            "keywords": "Naujųjų metų, naujo gyvenimo, tikslų, pokyčių"
        },
        "Šv. Valentino diena": {
            "must_have": ["valentin", "meilė", "meil", "romantik"],
            "forbidden": ["kalėd", "velyk"],
            "keywords": "Valentino dienos, meilės, romantikos, dovanų mylimam žmogui"
        },
        "Vasario 16-oji": {
            "must_have": ["vasario 16", "nepriklausomyb", "lietuv"],
            "forbidden": ["kalėd", "velyk"],
            "keywords": "Vasario 16-osios, Lietuvos nepriklausomybės, valstybės, trispalvės"
        },
        "Kovo 11-oji": {
            "must_have": ["kovo 11", "nepriklausomyb", "lietuv"],
            "forbidden": ["kalėd", "velyk"],
            "keywords": "Kovo 11-osios, Lietuvos nepriklausomybės atkūrimo, laisvės"
        },
        "Velykos": {
            "must_have": ["velyk", "velykini", "pavasari"],
            "forbidden": ["kalėd", "nauj metin", "žiem"],
            "keywords": "Velykų, pavasario šventės, šeimos susibūrimo, atgimimo"
        },
        "Gegužės 1-oji": {
            "must_have": ["gegužės 1", "gegužin", "darbo dien", "pavasa"],
            "forbidden": ["kalėd", "žiem"],
            "keywords": "Gegužės 1-osios, Darbo dienos, pavasario, poilsio"
        },
        "Motinos diena": {
            "must_have": ["motin", "mam", "dovana mamai"],
            "forbidden": ["kalėd", "žiem"],
            "keywords": "Motinos dienos, mamos, šeimos, dovanų"
        },
        "Tėvo diena": {
            "must_have": ["tėv", "tėt", "dovana tėčiui"],
            "forbidden": ["kalėd", "žiem"],
            "keywords": "Tėvo dienos, tėčio, šeimos, dovanų"
        },
        "Joninės": {
            "must_have": ["jonin", "vasaros švent", "rasos"],
            "forbidden": ["kalėd", "žiem"],
            "keywords": "Joninių, vasaros šventės, tradicijų, gamtos"
        },
        "Liepos 6-oji": {
            "must_have": ["liepos 6", "mindaug", "karaliaus", "valstybės"],
            "forbidden": ["kalėd", "žiem"],
            "keywords": "Valstybės dienos, Mindaugo karūnavimo, Lietuvos"
        },
        "Žolinė": {
            "must_have": ["žolin", "rugpjūt", "žolių"],
            "forbidden": ["kalėd", "žiem"],
            "keywords": "Žolinės, žolių šventinimo, vasaros pabaigos"
        },
        "Rugsėjo 1-oji": {
            "must_have": ["rugsėjo 1", "žinių dien", "mokykl", "mokslo met"],
            "forbidden": ["kalėd", "velyk"],
            "keywords": "Rugsėjo 1-osios, Žinių dienos, mokyklos, naujo mokslo metų"
        },
        "Šiurpnaktis (Halloween)": {
            "must_have": ["šiurpnakt", "halloween", "helovyn", "spalio 31", "moliūg"],
            "forbidden": ["kalėd", "velyk", "žiem"],
            "keywords": "Šiurpnakčio, Halloween, rudens šventės, moliūgų, siaubo"
        },
        "Šv. Kalėdos": {
            "must_have": ["kalėd", "švent", "žiem"],
            "forbidden": ["velyk", "pavasa", "vasara"],
            "keywords": "Kalėdų, žiemos švenčių, dovanų, šeimos"
        },
        "Kūčios": {
            "must_have": ["kūč", "kalėd", "žiem", "šventini"],
            "forbidden": ["velyk", "pavasa"],
            "keywords": "Kūčių, šventinės vakarienės, šeimos susibūrimo"
        }
    }
    
    current_season = season_data.get(season, season_data["Pavasaris"])
    current_holiday = holiday_data.get(holiday, None) if holiday != "Nėra" else None
    
    # Sukuriame ULTRA GRIEŽTĄ prompt'ą
    forbidden_list = current_season["forbidden"].copy()
    must_have_list = current_season["must_have"].copy()
    
    if current_holiday:
        forbidden_list.extend(current_holiday["forbidden"])
        must_have_list.extend(current_holiday["must_have"])
        holiday_text = f"""
🎄 PRIVALOMA ŠVENTĖ: {holiday}
Kiekviename tekste TURI būti: {current_holiday["keywords"]}
NIEKADA nerašyk apie: {', '.join(current_holiday["forbidden"])}
"""
    else:
        holiday_text = "Šventės nėra - nerašyk apie jokias šventes!"
    
    prompt = f"""KRITIŠKAI SVARBU! Perskaityk šias taisykles 3 KARTUS prieš rašydamas:

═══════════════════════════════════════
🚨 ABSOLIUČIOS TAISYKLĖS (NEGALIMA PAŽEISTI!) 🚨
═══════════════════════════════════════

📅 SEZONAS: {season.upper()}
✅ PRIVALOMA naudoti šiuos žodžius: {', '.join(must_have_list)}
❌ GRIEŽTAI DRAUDŽIAMA naudoti: {', '.join(forbidden_list)}

{holiday_text}

📋 PRODUKTAI (iš nuotraukų):
{analysis_text}

═══════════════════════════════════════
📝 UŽDUOTIS: Sukurk 3 tekstus (iki 250 simbolių kiekvienas)
═══════════════════════════════════════

**TEKSTO PAVYZDYS KĄ RAŠYTI:**
"Pavasario gaivumas su mūsų žaliuzėmis! 🌸 Šviesios spalvos, atsinaujinimas, nauji sprendimai Velykų proga!"

**TEKSTO PAVYZDYS KO NERAŠYTI:**
"Žiemos šiluma..." ❌ (jei sezonas PAVASARIS!)
"Kalėdų dovanos..." ❌ (jei šventė VELYKOS!)

═══════════════════════════════════════

VARIANTAS 1 - MARKETINGINIS 💼
- Profesionalus tonas
- Produktų privalumai + {current_season["message"]}
{f"- {holiday} šventės kontekstas" if holiday != "Nėra" else ""}
- 2-3 hashtag'us

VARIANTAS 2 - DRAUGIŠKAS 🏡
- Šiltas tonas
- Praktiška nauda + {current_season["message"]}
{f"- {holiday} jaukumas" if holiday != "Nėra" else ""}
- 1-2 hashtag'us

VARIANTAS 3 - SU HUMORU 😄
- Linksmas tonas
- Juokas + {current_season["message"]}
{f"- {holiday} su šypsena" if holiday != "Nėra" else ""}
- 2-3 hashtag'us

═══════════════════════════════════════
⚠️ PRIEŠ SIŲSDAMAS ATSAKYMĄ - PATIKRINK:
═══════════════════════════════════════
1. Ar KIEKVIENAME tekste yra bent vienas iš: {', '.join(must_have_list[:3])}?
2. Ar NĖRA nei vieno iš: {', '.join(forbidden_list[:5])}?
3. Ar produktai paminėti tiksliais pavadinimais?

Jei bent vienas patikrinimas FAILED - PERRAŠYK tekstus!

Atskirk variantus su "---"
Rašyk LIETUVIŠKAI.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Tu esi AI asistentas. ABSOLIUTI TAISYKLĖ: Dabar yra {season} sezonas{f' ir {holiday} šventė' if holiday != 'Nėra' else ''}. Tu NIEKADA nerašai apie kitus sezonus ar šventes. Jei bandysi pažeisti - tekstas bus atmestas."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,  # DAR sumažinta - maksimalus tikslumas
        max_tokens=1200
    )
    return response.choices[0].message.content.strip()

def image_to_base64(image_file):
    """Konvertuoja įkeltą failą į base64 be kompresijos"""
    image_file.seek(0)
    return base64.b64encode(image_file.read()).decode()

def create_social_template(images, text, layout="auto", text_position="bottom", font_size=40, background_color="#FFFFFF", style="Classic", font_family="Arial Bold", text_color="#000000", bg_opacity=180):
    """
    Sukuria 1080x1080 Instagram šabloną su nuotraukomis ir tekstu
    
    Args:
        images: List of PIL Image objects
        text: Tekstas, kuris bus pridėtas prie šablono
        layout: "auto", "1", "2", "3", "4", "2_vertical", "collage" - nuotraukų išdėstymas
        text_position: "top", "bottom", "center", "top_right", "bottom_right", "top_left", "bottom_left", "full_center" - teksto pozicija
        font_size: Tikslus šrifto dydis pikseliais (int)
        background_color: Hex spalva fono (pvz. "#FFFFFF")
        style: "Classic", "Gradient", "Rounded corners", "Shadow effect", "Vignette", "Polaroid"
        font_family: Šrifto šeima ("Arial Bold", "Times New Roman", etc.)
        text_color: Hex spalva teksto (pvz. "#000000")
        bg_opacity: Fono overlay permatomumas 0-255 (0=permatomas, 255=nepermatomas)
    
    Returns:
        BytesIO object su PNG šablonu
    """
    try:
        import random
        from PIL import ImageFilter
        
        # Canvas parametrai
        canvas_size = 1080
        margin = 50
        text_area_height = 250  # Fiksuotas teksto srities aukštis
        
        # Konvertuojame hex į RGB
        bg_color = tuple(int(background_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        text_rgb = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        # Nustatome teksto dydį - UŽTIKRINAME INT
        try:
            actual_font_size = int(font_size)
        except:
            actual_font_size = 40
        
        # DEBUG
        print(f"DEBUG: font_size parametras = {font_size} (type: {type(font_size)}), actual_font_size = {actual_font_size}")
        
        # Automatinis layout pagal nuotraukų kiekį
        if layout == "auto":
            layout = str(len(images))
        
        # Sukuriame Canvas
        canvas = Image.new('RGB', (canvas_size, canvas_size), bg_color)
        
        # Apskaičiuojame nuotraukų srities dydį pagal teksto poziciją (VISOS SU OVERLAY)
        photos_y_start = 0
        photos_height = canvas_size
        text_overlay = True
        
        # Nustatome teksto poziciją
        pos = text_position.lower()
        print(f"DEBUG: Gauta pozicija: '{text_position}' -> '{pos}'")
        
        # Lietuviški žodžiai
        has_top = "top" in pos or "viršus" in pos or "viršutinis" in pos or "virsus" in pos or "virsutinis" in pos
        has_bottom = "bottom" in pos or "apačia" in pos or "apatinis" in pos or "apacia" in pos
        has_right = "right" in pos or "dešinys" in pos or "desinys" in pos or "dešin" in pos or "desin" in pos
        has_left = "left" in pos or "kairys" in pos or "kair" in pos
        has_center = "center" in pos or "centras" in pos or "vidurys" in pos
        has_full = "full" in pos or "pilnas" in pos
        
        if has_top and has_right:
            text_align = "top_right"
        elif has_top and has_left:
            text_align = "top_left"
        elif has_bottom and has_right:
            text_align = "bottom_right"
        elif has_bottom and has_left:
            text_align = "bottom_left"
        elif has_top:
            text_align = "top"
        elif has_bottom:
            text_align = "bottom"
        elif has_full:
            text_align = "full_center"
        elif has_center:
            text_align = "center"
        else:
            text_align = "center"
        
        print(f"DEBUG: Nustatyta text_align: {text_align}")
        
        # NUOTRAUKŲ IŠDĖSTYMAS
        photos_width = canvas_size
        rounded_radius = 30 if "rounded" in style.lower() else 0
        
        def apply_rounded_corners(img, radius):
            """Prideda apvalius kampus nuotraukai"""
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
            img.putalpha(mask)
            return img
        
        def apply_photo_style(img, style_name):
            """Pritaiko stilių nuotraukai"""
            if "vignette" in style_name.lower():
                # Pridedame vignette efektą
                vignette = Image.new('L', img.size, 255)
                draw = ImageDraw.Draw(vignette)
                width, height = img.size
                for i in range(min(width, height) // 4):
                    alpha = int(255 * (1 - i / (min(width, height) / 4)))
                    draw.rectangle([i, i, width-i, height-i], outline=alpha)
                img = Image.composite(img, Image.new('RGB', img.size, (0, 0, 0)), vignette)
            
            if "shadow" in style_name.lower():
                # Šešėlio efektas (simuliacija)
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)
            
            return img
        
        if layout == "1" and len(images) >= 1:
            # 1 nuotrauka - pilnas plotis
            img = images[0].copy()
            img = apply_photo_style(img, style)
            img = img.resize((photos_width, photos_height), Image.Resampling.LANCZOS)
            
            if rounded_radius > 0:
                img = img.convert("RGBA")
                img = apply_rounded_corners(img, rounded_radius)
                temp_canvas = Image.new('RGBA', (canvas_size, canvas_size), bg_color + (255,))
                temp_canvas.paste(img, (0, photos_y_start), img)
                canvas = temp_canvas.convert("RGB")
            else:
                canvas.paste(img, (0, photos_y_start))
            
        elif layout == "2" and len(images) >= 2:
            # 2 nuotraukos - 2 stulpeliai
            photo_width = photos_width // 2
            gap = 10
            photo_width = (photos_width - gap) // 2
            
            for i in range(2):
                img = images[i].copy()
                img = apply_photo_style(img, style)
                img = img.resize((photo_width, photos_height), Image.Resampling.LANCZOS)
                canvas.paste(img, (i * (photo_width + gap), photos_y_start))
        
        elif layout == "2_vertical" and len(images) >= 2:
            # 2 nuotraukos - viršuje ir apačioje
            photo_height = photos_height // 2
            gap = 10
            photo_height = (photos_height - gap) // 2
            
            for i in range(2):
                img = images[i].copy()
                img = apply_photo_style(img, style)
                img = img.resize((photos_width, photo_height), Image.Resampling.LANCZOS)
                canvas.paste(img, (0, photos_y_start + i * (photo_height + gap)))
                
        elif layout == "3" and len(images) >= 3:
            # 3 nuotraukos - 1 viršuje, 2 apačioje
            top_height = photos_height // 2
            bottom_height = photos_height - top_height - 10
            gap = 10
            
            # Viršutinė nuotrauka
            img = images[0].copy()
            img = apply_photo_style(img, style)
            img = img.resize((photos_width, top_height), Image.Resampling.LANCZOS)
            canvas.paste(img, (0, photos_y_start))
            
            # Dvi apatinės
            photo_width = (photos_width - gap) // 2
            for i in range(2):
                img = images[i + 1].copy()
                img = apply_photo_style(img, style)
                img = img.resize((photo_width, bottom_height), Image.Resampling.LANCZOS)
                canvas.paste(img, (i * (photo_width + gap), photos_y_start + top_height + gap))
                
        elif layout == "4" and len(images) >= 4:
            # 4 nuotraukos - 2x2 grid
            gap = 10
            photo_width = (photos_width - gap) // 2
            photo_height = (photos_height - gap) // 2
            
            for i in range(4):
                row = i // 2
                col = i % 2
                img = images[i].copy()
                img = apply_photo_style(img, style)
                img = img.resize((photo_width, photo_height), Image.Resampling.LANCZOS)
                canvas.paste(img, (col * (photo_width + gap), photos_y_start + row * (photo_height + gap)))
        
        elif layout == "collage":
            # Atsitiktinis kolažas
            random.seed()
            for i, img in enumerate(images[:4]):
                size = random.randint(400, 600)
                angle = random.randint(-15, 15)
                
                img_resized = img.copy()
                img_resized = apply_photo_style(img_resized, style)
                img_resized = img_resized.resize((size, size), Image.Resampling.LANCZOS)
                
                if "polaroid" in style.lower():
                    # Polaroid efektas
                    border = 20
                    polaroid = Image.new('RGB', (size + border*2, size + border*2 + 40), (255, 255, 255))
                    polaroid.paste(img_resized, (border, border))
                    img_resized = polaroid
                
                rotated = img_resized.rotate(angle, expand=True, fillcolor=bg_color)
                
                max_x = canvas_size - rotated.width
                max_y = photos_height - rotated.height
                x = random.randint(0, max(1, max_x))
                y = photos_y_start + random.randint(0, max(1, max_y))
                
                canvas.paste(rotated, (x, y))
        
        # GRADIENT FONAS (jei pasirinktas)
        if "gradient" in style.lower() and not text_overlay:
            gradient = Image.new('RGB', (canvas_size, text_area_height), bg_color)
            draw_grad = ImageDraw.Draw(gradient)
            
            r, g, b = bg_color
            for i in range(text_area_height):
                ratio = i / text_area_height
                new_r = int(r * (1 - ratio * 0.3))
                new_g = int(g * (1 - ratio * 0.3))
                new_b = int(b * (1 - ratio * 0.3))
                
                if text_position.lower() == "top":
                    draw_grad.line([(0, i), (canvas_size, i)], fill=(new_r, new_g, new_b))
                else:
                    draw_grad.line([(0, text_area_height - i - 1), (canvas_size, text_area_height - i - 1)], fill=(new_r, new_g, new_b))
            
            if text_position.lower() == "top":
                canvas.paste(gradient, (0, 0))
            else:
                canvas.paste(gradient, (0, photos_height))
        
        # TEKSTO PRIDĖJIMAS
        draw = ImageDraw.Draw(canvas)
        
        # Įkeliame fontą pagal pasirinkimą - UNIVERSAL PATHS
        font = None
        
        # PIRMENYBĖ: Linux/Cloud šriftai (Streamlit Cloud), tada Windows
        font_map = {
            "Arial Bold": [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux/Cloud PIRMAS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",  # Windows
                "/System/Library/Fonts/Helvetica.ttc"  # Mac
            ],
            "Times New Roman": [
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                "C:/Windows/Fonts/times.ttf",
                "C:/Windows/Fonts/timesbd.ttf",
                "/System/Library/Fonts/Times.ttc"
            ],
            "Georgia": [
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "C:/Windows/Fonts/georgiab.ttf",
                "C:/Windows/Fonts/georgia.ttf",
                "/System/Library/Fonts/Georgia.ttf"
            ],
            "Courier New": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
                "C:/Windows/Fonts/courbd.ttf",
                "C:/Windows/Fonts/cour.ttf",
                "/System/Library/Fonts/Courier.ttc"
            ],
            "Verdana": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/verdanab.ttf",
                "C:/Windows/Fonts/verdana.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
            ],
            "Comic Sans MS": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/comicbd.ttf",
                "C:/Windows/Fonts/comic.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
            ]
        }
        
        font_paths = font_map.get(font_family, font_map["Arial Bold"])
        
        # CRITICAL: Naudojame font_size (ne base_font_size!)
        actual_font_size = int(font_size)
        
        # CRITICAL: Tikrai užkrauname fontą su OS patikra
        import os
        
        # DIAGNOSTIKA: Parodome VISUS galimus šriftus
        print(f"\n{'='*60}")
        print(f"FONT LOADING DEBUG: {font_family} su {actual_font_size}px")
        print(f"{'='*60}")
        
        font_loaded = False
        for i, font_path in enumerate(font_paths, 1):
            # Pirma tikriname ar failas egzistuoja
            exists = os.path.exists(font_path)
            print(f"{i}. {font_path}")
            print(f"   Egzistuoja: {'✅ TAIP' if exists else '❌ NE'}")
            
            if not exists:
                continue
                
            try:
                font = ImageFont.truetype(font_path, actual_font_size)
                print(f"   Rezultatas: ✅ SUCCESS! Užkrautas su {actual_font_size}px")
                print(f"{'='*60}\n")
                font_loaded = True
                break
            except Exception as e:
                print(f"   Rezultatas: ❌ ERROR - {str(e)[:60]}")
                continue
        
        # Jei NIEKUR nepavyko - ERROR
        if not font_loaded:
            error_msg = f"⚠️ CRITICAL ERROR: Negaliu užkrauti JOKIO šrifto su {actual_font_size}px!"
            print(f"DEBUG: {error_msg}")
            st.error(error_msg)
            # Last resort - bet kuris šriftas su dydžiu
            try:
                # Bandome bet kokį Linux šriftą
                for fallback in [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "C:/Windows/Fonts/arial.ttf"
                ]:
                    try:
                        font = ImageFont.truetype(fallback, actual_font_size)
                        print(f"DEBUG: ✅ FALLBACK sukurtas: {fallback} su {actual_font_size}px")
                        st.warning(f"Naudojamas fallback šriftas: {fallback}")
                        break
                    except:
                        continue
            except:
                st.error("FATAL: Default font be dydžio kontrolės!")
                font = ImageFont.load_default()
        
        # Automatinis teksto laužymas (word wrap)
        # PLATESNIS stulpelis - 4-6 žodžiai eilutėje = mažesni tarpai su justify
        
        # Pirma paskaičiuojame optimalų plotį pagal tekstą
        words = text.split()
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        total_chars = len(text)
        
        # Optimizuojame plotį - PLATESNĖ versija (4-6 žodžiai eilutėje)
        if text_align in ["top_right", "top_left", "bottom_right", "bottom_left"]:
            # Kampuose - 45-55% (daug žodžių = maži tarpai)
            if total_chars < 100:
                ratio = 0.45
            elif total_chars < 200:
                ratio = 0.50
            else:
                ratio = 0.55
            text_width = int(canvas_size * ratio) - (margin * 2)
        elif text_align in ["center", "full_center"]:
            # Centre - 50-65%
            if total_chars < 100:
                ratio = 0.50
            elif total_chars < 200:
                ratio = 0.57
            else:
                ratio = 0.65
            text_width = int(canvas_size * ratio) - (margin * 2)
        else:
            # Top/Bottom - pilnas plotis
            text_width = canvas_size - (margin * 2)
        
        wrapped_lines = []
        
        # Padalijame tekstą į eilutes
        paragraphs = text.split('\n')
        for paragraph in paragraphs:
            words = paragraph.split(' ')
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
                
                if line_width <= text_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                wrapped_lines.append(' '.join(current_line))
        
        # Naudojame vartotojo pasirinktą teksto spalvą
        final_text_color = text_rgb
        
        # Šešėlio spalva - priešinga teksto spalvai
        avg_text = sum(text_rgb) / 3
        shadow_color = (0, 0, 0, 180) if avg_text > 128 else (255, 255, 255, 180)
        
        # Apskaičiuojame teksto bloko dydį
        line_height = int(actual_font_size * 1.2)  # 20% tarpas (mažiau nei buvo)
        total_text_height = len(wrapped_lines) * line_height + margin
        
        # Apskaičiuojame tikrą teksto plotį (kompaktiškai)
        if wrapped_lines:
            max_line_width = max([draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0] for line in wrapped_lines])
            padding = margin // 2  # Mažesnis padding
            total_text_width = max_line_width + padding * 2
        else:
            total_text_width = canvas_size
        
        # Jei overlay - pridedame pusskaidrų foną tekstui pagal poziciją
        if text_overlay:
            overlay_bg = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay_bg)
            
            # Nustatome overlay poziciją pagal text_align (kompaktiškai)
            padding = margin // 2
            if text_align == "top_right":
                overlay_x = canvas_size - total_text_width - padding
                overlay_y = padding
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            elif text_align == "top_left":
                overlay_x = padding
                overlay_y = padding
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            elif text_align == "bottom_right":
                overlay_x = canvas_size - total_text_width - padding
                overlay_y = canvas_size - total_text_height - padding
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            elif text_align == "bottom_left":
                overlay_x = padding
                overlay_y = canvas_size - total_text_height - padding
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            elif text_align == "top":
                overlay_x = (canvas_size - total_text_width) // 2
                overlay_y = padding
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            elif text_align == "bottom":
                overlay_x = (canvas_size - total_text_width) // 2
                overlay_y = canvas_size - total_text_height - padding
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            elif text_align == "full_center":
                overlay_x = (canvas_size - total_text_width) // 2
                overlay_y = canvas_size // 2 - total_text_height // 2
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            else:  # center
                overlay_x = canvas_size // 2 - total_text_width // 2
                overlay_y = canvas_size // 2 - total_text_height // 2
                text_x_start = overlay_x + padding
                text_y = overlay_y + padding // 2
            
            # Piešiame pusskaidrų fono stačiakampį su vartotojo pasirinktu permatomumu
            overlay_draw.rectangle(
                [(overlay_x, overlay_y), (overlay_x + total_text_width, overlay_y + total_text_height)],
                fill=bg_color + (bg_opacity,)  # Naudojame vartotojo pasirinkta alpha
            )
            
            canvas = canvas.convert('RGBA')
            canvas = Image.alpha_composite(canvas, overlay_bg)
            draw = ImageDraw.Draw(canvas)
        
        # Piešiame tekstą su šešėliu + JUSTIFY
        current_y = text_y
        
        for i, line in enumerate(wrapped_lines):
            if current_y + line_height > canvas_size - margin:
                break  # Per daug teksto
            
            # PAPRASTAS LEFT ALIGN - normalūs tarpai (be justify)
            # Storasis šešėlis jei "shadow effect"
            if "shadow" in style.lower():
                for offset_x in range(-3, 4, 2):
                    for offset_y in range(-3, 4, 2):
                        if offset_x != 0 or offset_y != 0:
                            draw.text((text_x_start + offset_x, current_y + offset_y), line, fill=(0, 0, 0), font=font)
            else:
                # Įprastas šešėlis
                draw.text((text_x_start + 2, current_y + 2), line, fill=shadow_color[:3] if len(shadow_color) > 3 else shadow_color, font=font)
            
            # Tekstas su vartotojo pasirinkta spalva
            draw.text((text_x_start, current_y), line, fill=final_text_color, font=font)
            current_y += line_height
        
        # Konvertuojame atgal į RGB jei buvo RGBA
        if canvas.mode == 'RGBA':
            canvas = canvas.convert('RGB')
        
        # Išsaugome į BytesIO
        output = io.BytesIO()
        canvas.save(output, format='PNG', quality=95)
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Klaida kuriant šabloną: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

# ========== MODERNUS SOCIAL TEMPLATE ========== #
from until.export import resize_for_social
from until.layout import draw_text_auto
from until.templates import apply_template

st.markdown("---")
st.header("🆕 Modernus Social Media Šablonas")

uploaded_imgs = st.file_uploader("Įkelk nuotraukas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
input_text = st.text_input("Tekstas ant nuotraukos", "Žaliuzių akcija!")
extra_text = st.text_input("Papildomas tekstas (mažesnis)", "Akcija tik šią savaitę!")
social_format = st.selectbox("Formatas:", ["Instagram Square", "Instagram Story", "Facebook Post", "Pinterest Vertical"])
theme = st.selectbox("Tema:", ["Modern Dark", "Modern Blue", "Modern Red", "Modern Green", "Modern Gradient", "Winter", "Pastel"])
export_format = st.selectbox("Eksportuoti kaip:", ["PNG", "JPEG"])
font_path = st.text_input("Šrifto failas (pvz. Roboto-Bold.ttf)", "Roboto-Bold.ttf")

if uploaded_imgs:
    for idx, uploaded_img in enumerate(uploaded_imgs):
        img = Image.open(uploaded_img)
        img = resize_for_social(img, social_format)
        palette = [(120,180,255), (255,255,255)]
        img = apply_template(img, palette, theme)
        img = draw_text_auto(img, input_text, font_path=font_path)
        # Papildomas tekstas - mažesnis, žemiau pagrindinio
        if extra_text:
            W, H = img.size
            draw = ImageDraw.Draw(img)
            font_size = int(H * 0.035)
            fallback_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            try:
                font2 = ImageFont.truetype(font_path, font_size)
            except Exception:
                font2 = ImageFont.truetype(fallback_font, font_size)
            bbox2 = draw.textbbox((0, 0), extra_text, font=font2)
            w2 = bbox2[2] - bbox2[0]
            h2 = bbox2[3] - bbox2[1]
            position2 = ((W - w2) / 2, H * 0.70)
            overlay2 = Image.new("RGBA", (w2+40, h2+30), (0,0,0,120))
            img.paste(overlay2, (int(position2[0]-20), int(position2[1]-15)), overlay2)
            draw.text(position2, extra_text, fill="white", font=font2)
        st.image(img, caption=f"Modernus šablonas {idx+1}", use_column_width=True)
        buf = io.BytesIO()
        if export_format == "PNG":
            img.save(buf, format="PNG")
        else:
            img.save(buf, format="JPEG")
        st.download_button(f"Atsisiųsti {idx+1}", buf.getvalue(), file_name=f"template_{idx+1}.{export_format.lower()}", mime=f"image/{export_format.lower()}")

# ---------- Pagrindinis UI ----------
st.sidebar.header("⚙️ Nustatymai")

season = st.sidebar.selectbox(
    "🌤️ Metų laikas",
    ["Pavasaris", "Vasara", "Ruduo", "Žiema"],
    index=1
)

holiday = st.sidebar.selectbox(
    "🎉 Šventės (pasirinktinai)",
    [
        "Nėra", 
        "Naujieji metai", 
        "Šv. Valentino diena", 
        "Vasario 16-oji", 
        "Kovo 11-oji", 
        "Velykos", 
        "Gegužės 1-oji", 
        "Motinos diena", 
        "Tėvo diena", 
        "Joninės", 
        "Liepos 6-oji", 
        "Žolinė", 
        "Rugsėjo 1-oji", 
        "Šiurpnaktis (Halloween)",
        "Šv. Kalėdos", 
        "Kūčios"
    ],
    index=0
)

auto_process = st.sidebar.checkbox("🤖 Automatinis apdorojimas", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Marketinginis redagavimas")

add_watermark = st.sidebar.checkbox("💧 Pridėti vandens ženklą", value=True, help="Pridės jūsų tekstą dešiniame apatiniame kampe")
if add_watermark:
    watermark_text = st.sidebar.text_input("Vandens ženklo tekstas", value="#RūbaiLangams", help="Pvz: #RūbaiLangams arba © Jūsų Įmonė")
    watermark_size = st.sidebar.slider("📏 Vandens ženklo dydis (px)", 30, 300, 150, 10, help="Šrifto dydis pikseliais. 150px = vidutinis, 250px = DIDELIS")
else:
    watermark_text = ""
    watermark_size = 120

add_border = st.sidebar.checkbox("🖼️ Pridėti baltą rėmelį", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("**🤖 Automatinė optimizacija**")
auto_enhance = st.sidebar.checkbox("✨ AUTO spalvų optimizacija", value=True, help="Automatiškai pagerina šviesumą, kontrastą ir sodrumo")

if auto_enhance:
    st.sidebar.info("💡 Automatinė optimizacija įjungta - nuotraukos bus pagerintos!")
    # Automatiniai nustatymai marketinginėms nuotraukoms
    brightness = 1.1  # Šiek tiek šviesiau
    contrast = 1.15   # Ryškesnis kontrastas
    saturation = 1.1  # Sodresni spalvos
else:
    st.sidebar.markdown("**Rankinė spalvų korekcija:**")
    brightness = st.sidebar.slider("☀️ Šviesumas", 0.5, 1.5, 1.0, 0.05, help="<1.0 tamsiau, >1.0 šviesiau")
    contrast = st.sidebar.slider("🎭 Kontrastas", 0.5, 1.5, 1.0, 0.05, help="<1.0 blankiau, >1.0 ryškiau")
    saturation = st.sidebar.slider("🎨 Sodrumas", 0.5, 1.5, 1.0, 0.05, help="<1.0 pilkiau, >1.0 sodresni spalvos")

st.sidebar.markdown("---")
st.sidebar.markdown("💡 **Patarimas:** Įkelkite ryškias, kokybiškas nuotraukas su žaliuzėmis ar roletais.")

# Failų įkėlimas

# CSS stilių pridejimas
st.markdown("""
<style>
/* Mobilių optimizacija */
@media (max-width: 768px) {
    .stFileUploader > div > div {
        font-size: 18px !important;
        padding: 30px !important;
        border: 3px dashed #1f77b4 !important;
        border-radius: 15px !important;
        text-align: center !important;
        background-color: #f0f8ff !important;
        min-height: 100px !important;
    }
    
    .stFileUploader label {
        font-size: 20px !important;
        font-weight: bold !important;
        color: #1f77b4 !important;
    }
}

.upload-area {
    border: 2px dashed #ccc;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
    background-color: #f8f9fa;
}
.upload-area-success {
    border: 2px solid #28a745;
    background-color: #d4edda;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Patikriname ar yra įkeltų failų
# Mobiliai optimizuotas failų įkėlimas
st.markdown("### 📸 Įkelkite nuotraukas")

# Sukuriame tabs skirtingoms įkėlimo opcijoms
tab1, tab2, tab3 = st.tabs(["📁 Failų įkėlimas", "📷 Kamera", "🔧 Rankiniu būdu"])

uploaded_files = []

with tab1:
    st.markdown("**Standartinis būdas** (veikia PC ir kai kuriuose telefonuose)")
    files_standard = st.file_uploader(
        "Pasirinkite nuotraukas",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="standard_uploader"
    )
    if files_standard:
        uploaded_files.extend(files_standard)
        st.success(f"✅ Įkelta {len(files_standard)} nuotraukų!")

with tab2:
    if CAMERA_AVAILABLE:
        st.markdown("**Mobiliams telefonams** - fotografuokite tiesiai iš kameros")
        
        # Patikrinimas ar veikia kamera
        camera_photo = camera_input_live()
        if camera_photo is not None:
            st.image(camera_photo, caption="Užfiksuota nuotrauka")
            
            if st.button("📸 Pridėti šią nuotrauką", key="add_camera"):
                # Konvertuojame PIL į UploadedFile formato objektą
                if "camera_photos" not in st.session_state:
                    st.session_state.camera_photos = []
                
                # Konvertuojame PIL image į bytes
                img_bytes = io.BytesIO()
                camera_photo.save(img_bytes, format='JPEG')
                img_bytes.seek(0)
                
                st.session_state.camera_photos.append(img_bytes.getvalue())
                st.success("📸 Nuotrauka pridėta!")
                st.rerun()
        
        # Rodyti pridėtas nuotraukas iš kameros
        if "camera_photos" in st.session_state and st.session_state.camera_photos:
            st.info(f"🖼️ Pridėta iš kameros: {len(st.session_state.camera_photos)} nuotraukų")
            uploaded_files.extend([io.BytesIO(photo) for photo in st.session_state.camera_photos])
    else:
        st.error("📷 Kameros komponentas nepasiekiamas. Naudokite kitus būdus.")

with tab3:
    st.markdown("**Rezervinis variantas** - jei kiti būdai neveikia")
    st.info("📱 **Instrukcijos telefonui:**\n1. Įkelkite po vieną nuotrauką\n2. Spauskite 'Pridėti' po kiekvienos\n3. Kartokite iki 4 nuotraukų")
    
    single_file = st.file_uploader(
        "Įkelkite vieną nuotrauką",
        type=["jpg", "jpeg", "png"],
        key="single_uploader"
    )
    
    if single_file:
        # Rodyti failo dydį
        file_size_mb = single_file.size / (1024 * 1024)
        
        col1, col2 = st.columns([1,1])
        with col1:
            st.image(single_file, caption="Peržiūra", width=200)
            st.caption(f"📏 Dydis: {file_size_mb:.2f} MB")
        with col2:
            if st.button("➕ Pridėti šią nuotrauką", key="add_single"):
                if "manual_files" not in st.session_state:
                    st.session_state.manual_files = []
                
                if len(st.session_state.manual_files) < 4:
                    st.session_state.manual_files.append(single_file)
                    st.success(f"Pridėta! Iš viso: {len(st.session_state.manual_files)}")
                    st.rerun()
                else:
                    st.error("Maksimaliai 4 nuotraukos!")
    
    # Rodyti rankiniu būdu pridėtas nuotraukas
    if "manual_files" in st.session_state and st.session_state.manual_files:
        st.success(f"📝 Rankiniu būdu pridėta: {len(st.session_state.manual_files)} nuotraukų")
        uploaded_files.extend(st.session_state.manual_files)
        
        # Preview mažų nuotraukų
        cols = st.columns(4)
        for i, file in enumerate(st.session_state.manual_files):
            with cols[i]:
                st.image(file, width=100)
        
        if st.button("🗑️ Išvalyti visas rankiniu būdu pridėtas", key="clear_manual"):
            st.session_state.manual_files = []
            st.rerun()

# Mobilus failų valdymas
if uploaded_files:
    st.session_state.uploaded_files = uploaded_files
    st.success(f"🎉 **Iš viso pasirinkta: {len(uploaded_files)} nuotraukų!**")
    
    # Rodyti preview
    if len(uploaded_files) <= 4:
        cols = st.columns(len(uploaded_files))
        for i, file in enumerate(uploaded_files):
            with cols[i]:
                st.image(file, caption=f"#{i+1}", width=150)
    else:
        st.warning("⚠️ Per daug nuotraukų! Bus naudojamos tik pirmosios 4.")
        uploaded_files = uploaded_files[:4]
        st.session_state.uploaded_files = uploaded_files

elif "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# Globalus išvalymo mygtukas
if st.session_state.uploaded_files:
    if st.button("🗑️ Išvalyti VISAS nuotraukas", type="secondary", key="clear_all"):
        st.session_state.uploaded_files = []
        if "manual_files" in st.session_state:
            st.session_state.manual_files = []
        if "camera_photos" in st.session_state:
            st.session_state.camera_photos = []
        st.rerun()

# Rodyti instrukcijas jei nėra failų
if not st.session_state.uploaded_files:
    st.info("👆 **Pasirinkite vieną iš būdų aukščiau įkelti nuotraukas**")

# Naudojame session_state failus
files_to_process = st.session_state.uploaded_files

if files_to_process:
    st.success(f"✅ Įkelta {len(files_to_process)} nuotraukų!")
    
    # Rodyti ir leisti atsisiųsti kiekvieną nuotrauką atskirai
    st.markdown("### 🎨 Redaguotos nuotraukos")
    st.info("Reguliokite redagavimo nustatymus šoniniame meniu (šviesumas, kontrastas, vandens ženklas)")
    
    cols = st.columns(min(len(files_to_process), 4))
    for i, file in enumerate(files_to_process):
        with cols[i % 4]:
            file.seek(0)
            
            # SVARBU: Vandens ženklas tik ant paskutinės nuotraukos (jei jų daugiau nei 1)
            show_watermark = add_watermark and (len(files_to_process) == 1 or i == len(files_to_process) - 1)
            
            # Redaguojame nuotrauką
            edited = add_marketing_overlay(
                file,
                add_watermark=show_watermark,
                add_border=add_border,
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
                watermark_text=watermark_text,
                watermark_size=watermark_size
            )
            edited.seek(0)
            
            # Rodyti peržiūrą
            st.image(edited, caption=f"Nuotrauka {i+1}", use_container_width=True)
            
            # Download mygtukas kiekvienai nuotraukai
            filename = getattr(file, 'name', f'nuotrauka_{i+1}.jpg')
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            
            edited.seek(0)
            st.download_button(
                label=f"📥 Atsisiųsti #{i+1}",
                data=edited.getvalue(),
                file_name=f"{base_name}_edited.jpg",
                mime="image/jpeg",
                key=f"download_{i}",
                use_container_width=True
            )
    
    # COLLAGE KŪRIMAS
    st.markdown("---")
    st.markdown("### 🖼️ Collage Kūrėjas")
    
    # Automatiškai nustatome temą pagal sezoną/šventę
    if holiday != "Nėra":
        auto_theme = f"🎉 Šventinė: {holiday}"
    else:
        auto_theme = f"🍂 Sezoninė: {season}"
    
    st.info(f"✨ Automatinė tema: **{auto_theme}** (pagal jūsų nustatymus kairėje)")
    
    if len(files_to_process) >= 2:
        # Stilius pasirinkimas
        collage_style = st.selectbox(
            "🎨 Collage stilius:",
            [
                "📸 Polaroid - Nuotraukos su baltais rėmeliais, pasuktos",
                "📱 Instagram Grid - Tvarkingas tinklelis su tarpais",
                "🎨 Scrapbook - Kūrybiškas, atsitiktinis išdėstymas",
                "🖼️ Gallery Wall - Galerijos siena su juodais rėmeliais",
                "✨ Minimalist - Minimalus stilius, baltas fonas"
            ],
            help="Pasirinkite collage stilių",
            key="collage_style_selector"
        )
        
        collage_layout = st.selectbox(
            "📐 Išdėstymas:",
            ["2x2 Grid (4 nuotraukos)", "1x2 Horizontal (2 nuotraukos)", "2x1 Vertical (2 nuotraukos)", "1x3 Horizontal (3 nuotraukos)", "3x1 Vertical (3 nuotraukos)"],
            help="Pasirinkite kaip išdėstyti nuotraukas"
        )
        
        if st.button("🎨 Sukurti Collage", type="primary", use_container_width=True):
            with st.spinner("🖼️ Kuriamas tematinis collage..."):
                try:
                    # Paruošiame redaguotas nuotraukas
                    edited_images = []
                    for idx, file in enumerate(files_to_process):
                        file.seek(0)
                        
                        # SVARBU: Vandens ženklas tik ant paskutinės nuotraukos collage
                        show_watermark = add_watermark and (idx == len(files_to_process) - 1)
                        
                        edited = add_marketing_overlay(
                            file,
                            add_watermark=show_watermark,
                            add_border=False,  # Collage'ui be rėmelio
                            brightness=brightness,
                            contrast=contrast,
                            saturation=saturation,
                            watermark_text=watermark_text,
                            watermark_size=watermark_size
                        )
                        edited.seek(0)
                        img = Image.open(edited)
                        edited_images.append(img)
                    
                    # Nustatome layout
                    if "2x2" in collage_layout:
                        rows, cols = 2, 2
                        needed = 4
                    elif "1x2" in collage_layout:
                        rows, cols = 1, 2
                        needed = 2
                    elif "2x1" in collage_layout:
                        rows, cols = 2, 1
                        needed = 2
                    elif "1x3" in collage_layout:
                        rows, cols = 1, 3
                        needed = 3
                    elif "3x1" in collage_layout:
                        rows, cols = 3, 1
                        needed = 3
                    
                    # Apkarpome jei per daug
                    edited_images = edited_images[:needed]
                    
                    # Jei per mažai - dubliuojame
                    while len(edited_images) < needed:
                        edited_images.append(edited_images[-1])
                    
                    import random
                    
                    # NUSTATOME STILIŲ PAGAL PASIRINKIMĄ
                    
                    # Automatiškai nustatome fono spalvą pagal sezoną/šventę
                    if holiday != "Nėra":
                        if "Kalėdos" in holiday:
                            bg_color = (235, 245, 240)
                        elif "Velykos" in holiday:
                            bg_color = (255, 250, 235)
                        elif "Valentino" in holiday:
                            bg_color = (255, 245, 248)
                        elif "Naujieji" in holiday:
                            bg_color = (240, 245, 255)
                        else:
                            bg_color = (245, 245, 240)
                    else:
                        if season == "Pavasaris":
                            bg_color = (248, 252, 245)
                        elif season == "Vasara":
                            bg_color = (255, 252, 240)
                        elif season == "Ruduo":
                            bg_color = (250, 245, 235)
                        else:
                            bg_color = (245, 248, 252)
                    
                    # ============ POLAROID STILIUS ============
                    if "Polaroid" in collage_style:
                        polaroid_width = 500
                        polaroid_height = 500
                        border_size = 20
                        bottom_border = 60
                        
                        if needed == 4:
                            canvas_width, canvas_height = 1800, 1800
                            positions = [(200, 150, -8), (850, 100, 12), (300, 850, 5), (950, 900, -10)]
                        elif needed == 3:
                            canvas_width, canvas_height = 2000, 1200
                            positions = [(200, 250, -10), (750, 150, 8), (450, 700, -5)]
                        else:
                            canvas_width, canvas_height = 1600, 1200
                            positions = [(250, 300, -12), (850, 350, 8)]
                        
                        collage = Image.new('RGB', (canvas_width, canvas_height), bg_color)
                        
                        for idx, img in enumerate(edited_images[:needed]):
                            img_resized = img.resize((polaroid_width, polaroid_height), Image.Resampling.LANCZOS)
                            polaroid_img = Image.new('RGB', 
                                (polaroid_width + border_size * 2, 
                                 polaroid_height + border_size + bottom_border), 
                                (255, 255, 255))
                            polaroid_img.paste(img_resized, (border_size, border_size))
                            
                            x, y, angle = positions[idx]
                            rotated = polaroid_img.rotate(angle, expand=True, fillcolor=bg_color)
                            collage.paste(rotated, (x, y))
                    
                    # ============ INSTAGRAM GRID STILIUS ============
                    elif "Instagram Grid" in collage_style:
                        img_size = 600
                        gap = 30
                        
                        canvas_width = cols * img_size + (cols + 1) * gap
                        canvas_height = rows * img_size + (rows + 1) * gap
                        
                        collage = Image.new('RGB', (canvas_width, canvas_height), bg_color)
                        
                        idx = 0
                        for row in range(rows):
                            for col in range(cols):
                                if idx < len(edited_images):
                                    img_resized = edited_images[idx].resize((img_size, img_size), Image.Resampling.LANCZOS)
                                    x = gap + col * (img_size + gap)
                                    y = gap + row * (img_size + gap)
                                    collage.paste(img_resized, (x, y))
                                    idx += 1
                    
                    # ============ SCRAPBOOK STILIUS ============
                    elif "Scrapbook" in collage_style:
                        if needed == 4:
                            canvas_width, canvas_height = 1900, 1900
                        elif needed == 3:
                            canvas_width, canvas_height = 2100, 1300
                        else:
                            canvas_width, canvas_height = 1700, 1300
                        
                        collage = Image.new('RGB', (canvas_width, canvas_height), bg_color)
                        
                        # Atsitiktiniai dydžiai ir pozicijos
                        for idx, img in enumerate(edited_images[:needed]):
                            size_var = random.randint(450, 650)
                            img_resized = img.resize((size_var, size_var), Image.Resampling.LANCZOS)
                            
                            # Pridedame atsitiktinį rėmelį
                            border_color = random.choice([(255,255,255), (250,250,240), (245,240,235)])
                            border_width = random.randint(15, 35)
                            bordered = ImageOps.expand(img_resized, border=border_width, fill=border_color)
                            
                            # Atsitiktinė pozicija ir kampas
                            max_x = canvas_width - bordered.width - 100
                            max_y = canvas_height - bordered.height - 100
                            x = random.randint(50, max(51, max_x))
                            y = random.randint(50, max(51, max_y))
                            angle = random.randint(-15, 15)
                            
                            rotated = bordered.rotate(angle, expand=True, fillcolor=bg_color)
                            collage.paste(rotated, (x, y))
                    
                    # ============ GALLERY WALL STILIUS ============
                    elif "Gallery Wall" in collage_style:
                        img_size = 550
                        gap = 40
                        
                        canvas_width = cols * img_size + (cols + 1) * gap
                        canvas_height = rows * img_size + (rows + 1) * gap
                        
                        collage = Image.new('RGB', (canvas_width, canvas_height), (240, 240, 240))
                        
                        idx = 0
                        for row in range(rows):
                            for col in range(cols):
                                if idx < len(edited_images):
                                    img_resized = edited_images[idx].resize((img_size, img_size), Image.Resampling.LANCZOS)
                                    # Juodas rėmelis
                                    framed = ImageOps.expand(img_resized, border=15, fill=(20, 20, 20))
                                    x = gap + col * (img_size + gap)
                                    y = gap + row * (img_size + gap)
                                    collage.paste(framed, (x, y))
                                    idx += 1
                    
                    # ============ MINIMALIST STILIUS ============
                    elif "Minimalist" in collage_style:
                        img_size = 600
                        gap = 60
                        
                        canvas_width = cols * img_size + (cols + 1) * gap
                        canvas_height = rows * img_size + (rows + 1) * gap
                        
                        collage = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
                        
                        idx = 0
                        for row in range(rows):
                            for col in range(cols):
                                if idx < len(edited_images):
                                    img_resized = edited_images[idx].resize((img_size, img_size), Image.Resampling.LANCZOS)
                                    # Labai plonas pilkas rėmelis
                                    framed = ImageOps.expand(img_resized, border=2, fill=(200, 200, 200))
                                    x = gap + col * (img_size + gap)
                                    y = gap + row * (img_size + gap)
                                    collage.paste(framed, (x, y))
                                    idx += 1
                    
                    # Išsaugome
                    collage_bytes = io.BytesIO()
                    collage.save(collage_bytes, format='JPEG', quality=95)
                    collage_bytes.seek(0)
                    
                    # Išsaugome į session_state
                    st.session_state.collage_result = collage_bytes.getvalue()
                    st.session_state.collage_filename = f"collage_{season}_{holiday}.jpg"
                    
                except Exception as e:
                    st.error(f"❌ Klaida kuriant collage: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    else:
        st.warning("⚠️ Collage reikia bent 2 nuotraukų!")
    
    # Rodyti collage rezultatą (jei sukurtas)
    if "collage_result" in st.session_state and st.session_state.collage_result:
        st.markdown("---")
        st.markdown("### ✅ Sukurtas Collage")
        st.image(st.session_state.collage_result, caption="Jūsų Collage", use_container_width=True)
        
        st.download_button(
            label="📥 Atsisiųsti Collage",
            data=st.session_state.collage_result,
            file_name=st.session_state.collage_filename,
            mime="image/jpeg",
            use_container_width=True,
            key="download_collage_persistent"
        )
    
    # AI TURINIO GENERAVIMAS
    st.markdown("---")
    st.markdown("### 📝 AI Turinio Generavimas")
    st.info("💡 Sukurkite tekstus socialiniams tinklams pagal jūsų nuotraukas")
    
    # Mygtukas čia
    if st.button("🚀 Sukurti AI Turinį", type="primary", use_container_width=True, key="create_ai_content_btn"):
        # Patikriname ar pasikeitė nustatymai
        current_settings = f"{season}_{holiday}"
        last_settings = st.session_state.get("last_ai_settings", None)
        
        # Jei turime išsaugotas analizes IR pasikeitė nustatymai - tiesiog perkuriame tekstą
        if last_settings and current_settings != last_settings and "ai_analyses" in st.session_state and st.session_state.ai_analyses:
            st.session_state.trigger_ai_regenerate = True
        else:
            # Kitais atvejais - pilna analizė iš naujo
            st.session_state.trigger_ai_content = True
        
        st.session_state.last_ai_settings = current_settings
    
    # Mygtukas išvalyti failus
    st.markdown("---")
    if st.button("🗑️ Išvalyti visus failus ir rezultatus", type="secondary", use_container_width=True):
        st.session_state.uploaded_files = []
        if "collage_result" in st.session_state:
            del st.session_state.collage_result
        if "ai_content_result" in st.session_state:
            del st.session_state.ai_content_result
        st.rerun()
    
    if len(files_to_process) > 4:
        st.warning("⚠️ Per daug failų! Pasirinkite iki 4 nuotraukų.")
        files_to_process = files_to_process[:4]
        st.session_state.uploaded_files = files_to_process

# JEI TIK NUSTATYMAI PASIKEITĖ - greitai perkuriame tekstą su tais pačiais nuotraukų analizėmis
if st.session_state.get("trigger_ai_regenerate", False):
    status_text = st.empty()
    status_text.text(f"🔄 Perkuriamas turinys su naujais nustatymais ({season} / {holiday})...")
    
    combined_analysis = " ".join(st.session_state.ai_analyses)
    
    try:
        captions = generate_captions(combined_analysis, season, holiday)
        st.session_state.ai_content_result = captions
        st.success(f"✅ Turinys atnaujintas! Sezonas: {season}, Šventė: {holiday}")
    except Exception as e:
        st.error(f"❌ Klaida perkuriant turinį: {e}")
    
    status_text.empty()
    st.session_state.trigger_ai_regenerate = False
    st.rerun()

# Apdorojimas tik jei yra failų ir trigger'is aktyvuotas
if "trigger_ai_content" in st.session_state and st.session_state.trigger_ai_content and files_to_process and len(files_to_process) > 0:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_analyses = []
    
    # Analizuojame REDAGUOTAS nuotraukas (su vandens ženkliu, spalvų koregavimu)
    for i, file in enumerate(files_to_process):
        status_text.text(f"🔍 Analizuojama redaguota nuotrauka {i+1}/{len(files_to_process)}...")
        progress_bar.progress((i + 1) / (len(files_to_process) + 1))
        
        try:
            file.seek(0)
            
            # SVARBU: Vandens ženklas tik ant paskutinės nuotraukos (jei jų daugiau nei 1)
            show_watermark = add_watermark and (len(files_to_process) == 1 or i == len(files_to_process) - 1)
            
            # Sukuriame redaguotą nuotrauką (su visais efektais)
            edited = add_marketing_overlay(
                file,
                add_watermark=show_watermark,
                add_border=add_border,
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
                watermark_text=watermark_text,
                watermark_size=watermark_size
            )
            edited.seek(0)
            
            # Konvertuojame REDAGUOTĄ nuotrauką į base64
            image_b64 = base64.b64encode(edited.read()).decode()
            
            # Analizuojame redaguotą nuotrauką
            analysis = analyze_image(image_b64)
            all_analyses.append(analysis)
            
        except Exception as e:
            st.error(f"❌ Klaida apdorojant nuotrauką {i+1}: {str(e)}")
            continue
    
    if all_analyses:
        status_text.text("✍️ Kuriamas turinys...")
        progress_bar.progress(1.0)
        
        # Sujungiame visas analizes
        combined_analysis = " ".join(all_analyses)
        
        # Generuojame tekstą
        try:
            captions = generate_captions(combined_analysis, season, holiday)
            
            # Išsaugome į session_state
            st.session_state.ai_content_result = captions
            st.session_state.ai_analyses = all_analyses
            
        except Exception as e:
            st.error(f"❌ Klaida generuojant turinį: {e}")
    
    progress_bar.empty()
    status_text.empty()
    
    # Reset trigger TIKTAI pabaigoje
    st.session_state.trigger_ai_content = False

# Rodyti AI turinio rezultatus (jei sukurti)
if "ai_content_result" in st.session_state and st.session_state.ai_content_result:
    st.markdown("---")
    st.success("✅ Turinys sėkmingai sukurtas!")
    
    # Rezultatai
    st.subheader("📝 Socialinių tinklų įrašai")
    
    # Rodyti sugeneruotą turinį
    st.markdown("### 🎯 Paruošti tekstai:")
    st.text_area("Kopijuokite tekstą:", value=st.session_state.ai_content_result, height=200, key="ai_content_persistent")
    
    # Analitikos informacija
    if "ai_analyses" in st.session_state:
        with st.expander("📊 Detali analizė"):
            st.markdown("**Vaizdų analizė:**")
            for i, analysis in enumerate(st.session_state.ai_analyses):
                st.markdown(f"**Nuotrauka {i+1}:** {analysis}")
    
    # SOCIAL MEDIA ŠABLONO GENERAVIMAS
    st.markdown("---")
    st.markdown("### 🎨 Social Media Šablono Generavimas")
    st.info("📱 Sukurkite 1080×1080 Instagram paruoštą šabloną su nuotraukomis ir tekstu!")
    
    # UI kontrolės šablonui
    col1, col2, col3 = st.columns(3)
    
    with col1:
        template_layout = st.selectbox(
            "📐 Nuotraukų išdėstymas:",
            ["auto", "1 foto", "2 foto", "3 foto", "4 foto", "2 foto vertical", "Kolažas (atsitiktinai)"],
            help="Automatinis - pagal įkeltų nuotraukų kiekį"
        )
    
    with col2:
        template_text_position = st.selectbox(
            "📍 Teksto vieta:",
            ["top", "bottom", "center", "top_right", "bottom_right", "top_left", "bottom_left", "full_center"],
            index=1,
            help="Pasirinkite kur bus tekstas (visos pozicijos su overlay)"
        )
    
    with col3:
        template_style = st.selectbox(
            "✨ Šablono stilius:",
            ["Classic", "Gradient", "Rounded corners", "Shadow effect", "Vignette", "Polaroid"],
            help="Prideda vizualinius efektus"
        )
    
    col4, col5 = st.columns(2)
    
    with col4:
        template_font_size = st.slider(
            "🔤 Teksto dydis (px):",
            min_value=20,
            max_value=100,
            value=40,
            step=2,
            help="Šrifto dydis pikseliais"
        )
    
    with col5:
        template_font_family = st.selectbox(
            "🔠 Šriftas:",
            ["Arial Bold", "Times New Roman", "Georgia", "Courier New", "Verdana", "Comic Sans MS"],
            help="Pasirinkite teksto šriftą"
        )
    
    col6, col7, col8 = st.columns(3)
    
    with col6:
        template_bg_color = st.color_picker(
            "🎨 Fono spalva:",
            "#FFFFFF",
            help="Pasirinkite fono spalvą tekstui"
        )
    
    with col7:
        template_text_color = st.color_picker(
            "✏️ Teksto spalva:",
            "#000000",
            help="Pasirinkite raidžių spalvą"
        )
    
    with col8:
        template_bg_opacity = st.slider(
            "🔳 Fono permatomumas:",
            min_value=0,
            max_value=255,
            value=180,
            step=10,
            help="0 = visiškai permatomas, 255 = nepermatomas"
        )
    
    # Pasirenkame kurį tekstą naudoti
    template_text_option = st.radio(
        "📝 Kuris tekstas bus šablone?",
        ["Pilnas AI turinys", "Tik pirmas variantas", "Tik antras variantas", "Tik trečias variantas", "Rankinis tekstas"],
        index=0
    )
    
    # Jei rankinis tekstas
    if template_text_option == "Rankinis tekstas":
        template_custom_text = st.text_area(
            "✍️ Įveskite tekstą šablonui:",
            height=100,
            placeholder="Jūsų tekstas čia..."
        )
    else:
        template_custom_text = None
    
    # Mygtukas generuoti šabloną
    if st.button("🚀 Generuoti Social Media Šabloną", type="primary", use_container_width=True, key="generate_template_btn"):
        with st.spinner("🎨 Kuriamas šablonas..."):
            try:
                # Paruošiame nuotraukas
                template_images = []
                for idx, file in enumerate(files_to_process):
                    file.seek(0)
                    
                    # Vandens ženklas tik ant paskutinės
                    show_watermark = add_watermark and (idx == len(files_to_process) - 1)
                    
                    edited = add_marketing_overlay(
                        file,
                        add_watermark=show_watermark,
                        add_border=False,
                        brightness=brightness,
                        contrast=contrast,
                        saturation=saturation,
                        watermark_text=watermark_text,
                        watermark_size=watermark_size
                    )
                    edited.seek(0)
                    img = Image.open(edited)
                    template_images.append(img)
                
                # Pasiruošiame tekstą
                if template_custom_text:
                    final_text = template_custom_text
                elif template_text_option == "Pilnas AI turinys":
                    final_text = st.session_state.ai_content_result
                elif template_text_option == "Tik pirmas variantas":
                    variants = st.session_state.ai_content_result.split("---")
                    final_text = variants[0].strip() if variants else st.session_state.ai_content_result
                elif template_text_option == "Tik antras variantas":
                    variants = st.session_state.ai_content_result.split("---")
                    final_text = variants[1].strip() if len(variants) > 1 else st.session_state.ai_content_result
                elif template_text_option == "Tik trečias variantas":
                    variants = st.session_state.ai_content_result.split("---")
                    final_text = variants[2].strip() if len(variants) > 2 else st.session_state.ai_content_result
                else:
                    final_text = st.session_state.ai_content_result
                
                # Išvalome nereikalingus teksto elementus (VARIANTAS 1, 2, 3, MARKETINGINIS, etc.)
                import re
                final_text = re.sub(r'VARIANTAS\s+\d+\s*[-:]*\s*', '', final_text, flags=re.IGNORECASE)
                final_text = re.sub(r'^\d+[\.\)]\s*', '', final_text, flags=re.MULTILINE)  # Numeriai pradžioje eilučių
                # Pašaliname tipo etiketes (MARKETINGINIS, DRAUGIŠKAS, SU HUMORU)
                final_text = re.sub(r'(MARKETINGINIS|DRAUGIŠKAS|DRAUGI[ŠS]KAS|SU HUMORU)\s*[💼🏡😄🎭]*\s*[-:]*\s*', '', final_text, flags=re.IGNORECASE)
                final_text = final_text.strip()
                
                # Konvertuojame layout
                layout_map = {
                    "auto": "auto",
                    "1 foto": "1",
                    "2 foto": "2",
                    "3 foto": "3",
                    "4 foto": "4",
                    "2 foto vertical": "2_vertical",
                    "Kolažas (atsitiktinai)": "collage"
                }
                layout_value = layout_map.get(template_layout, "auto")
                
                # UI Debug - matysi naršyklėje!
                st.info(f"🔍 DEBUG: Font dydis = **{template_font_size}px**, Šriftas = **{template_font_family}**, Pozicija = **{template_text_position}**")
                
                # Debug info
                print(f"\n=== ŠABLONO PARAMETRAI ===")
                print(f"Layout: {layout_value}")
                print(f"Pozicija: '{template_text_position}'")
                print(f"Font dydis: {template_font_size} (type: {type(template_font_size)})")
                print(f"Font šeima: {template_font_family}")
                print(f"Teksto spalva: {template_text_color}")
                print(f"Fono spalva: {template_bg_color}")
                print(f"Stilius: {template_style}")
                print(f"========================\n")
                
                # Generuojame šabloną
                template_result = create_social_template(
                    images=template_images,
                    text=final_text,
                    layout=layout_value,
                    text_position=template_text_position,
                    font_size=template_font_size,
                    background_color=template_bg_color,
                    style=template_style,
                    font_family=template_font_family,
                    text_color=template_text_color,
                    bg_opacity=template_bg_opacity
                )
                
                if template_result:
                    st.session_state.template_result = template_result.getvalue()
                    st.session_state.template_filename = f"social_template_{season}_{holiday}.png"
                    st.success("✅ Šablonas sukurtas sėkmingai!")
                    
            except Exception as e:
                st.error(f"❌ Klaida kuriant šabloną: {e}")
                import traceback
                st.error(traceback.format_exc())
    
    # Rodyti sugeneruotą šabloną
    if "template_result" in st.session_state and st.session_state.template_result:
        st.markdown("---")
        st.markdown("### ✅ Sugeneruotas Social Media Šablonas")
        st.image(st.session_state.template_result, caption="1080×1080 Instagram šablonas", use_container_width=True)
        
        st.download_button(
            label="📥 Atsisiųsti šabloną (PNG)",
            data=st.session_state.template_result,
            file_name=st.session_state.template_filename,
            mime="image/png",
            use_container_width=True,
            key="download_template"
        )

# AI išdėstymo generavimo funkcija
def ai_generate_layout(num_images, texts):
    """
    Naudoja OpenAI API, kad sugeneruotų nuotraukų ir tekstų išdėstymo parametrus.
    """
    prompt = f"Sugeneruok social media koliažo išdėstymo parametrus {num_images} nuotraukoms ir {len(texts)} tekstams. Atsakyk JSON formatu: nuotraukos: [{{x, y, w, h, rotation}}], tekstai: [{{x, y, size, font, color}}]. Stilius modernus, estetiškas, kiekvieną kartą skirtingas."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    import json
    try:
        layout = json.loads(response.choices[0].message.content)
    except Exception:
        # Fallback: random grid
        layout = {
            "nuotraukos": [
                {"x": 100 + i*300, "y": 100, "w": 250, "h": 250, "rotation": random.randint(-10,10)} for i in range(num_images)
            ],
            "tekstai": [
                {"x": 200, "y": 500, "size": 48, "font": "DejaVuSans-Bold.ttf", "color": "#FFFFFF"},
                {"x": 200, "y": 600, "size": 32, "font": "DejaVuSans-Bold.ttf", "color": "#CCCCCC"}
            ]
        }
    return layout

st.markdown("---")
st.header("🧠 AI generuojamas Social Media Koliažas")

uploaded_imgs = st.file_uploader("Įkelk nuotraukas (koliažui)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
input_text = st.text_input("Pagrindinis tekstas", "Žaliuzių akcija!")
extra_text = st.text_input("Papildomas tekstas", "Akcija tik šią savaitę!")
export_format = st.selectbox("Eksportuoti kaip:", ["PNG", "JPEG"])

if uploaded_imgs and (input_text or extra_text):
    texts = [input_text]
    if extra_text:
        texts.append(extra_text)
    layout = ai_generate_layout(len(uploaded_imgs), texts)
    # Sukuriame tuščią canvas
    canvas = Image.new("RGBA", (1080,1080), (30,30,30,255))
    # Sudedam nuotraukas
    for i, img_file in enumerate(uploaded_imgs):
        img = Image.open(img_file).convert("RGBA")
        params = layout["nuotraukos"][i]
        img = img.resize((params["w"], params["h"]), Image.LANCZOS)
        img = img.rotate(params["rotation"], expand=True)
        canvas.alpha_composite(img, (params["x"], params["y"]))
    # Sudedam tekstus
    draw = ImageDraw.Draw(canvas)
    for i, txt in enumerate(texts):
        tparams = layout["tekstai"][i]
        try:
            font = ImageFont.truetype(tparams["font"], tparams["size"])
        except Exception:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", tparams["size"])
        draw.text((tparams["x"], tparams["y"]), txt, font=font, fill=tparams["color"])
    st.image(canvas.convert("RGB"), caption="AI generuotas koliažas", use_column_width=True)
    buf = io.BytesIO()
    if export_format == "PNG":
        canvas.convert("RGB").save(buf, format="PNG")
    else:
        canvas.convert("RGB").save(buf, format="JPEG")
    st.download_button("Atsisiųsti koliažą", buf.getvalue(), file_name=f"ai_koliazas.{export_format.lower()}", mime=f"image/{export_format.lower()}")
# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")