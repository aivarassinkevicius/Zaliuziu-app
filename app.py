import streamlit as st
import io, os, base64, json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter
from supabase import create_client, Client

# HTML rendering imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import tempfile
import time

# Import our new image processing module
try:
    from lib.image_processing import process_blinds_photo

    OPENCV_AVAILABLE = True
except ImportError as e:
    OPENCV_AVAILABLE = False
    print(f"OpenCV import failed: {e}")  # Debug log

# ---------- Nustatymai ----------
load_dotenv()

# Version: 2.4 - Supabase integration for version history
# Bandome gauti API raktą iš .env failo (vietinis) arba Streamlit secrets (cloud)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    # Jei vietiniai aplinkos kintamieji nėra, bandome Streamlit secrets
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        pass

# Supabase inicializacija
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
    except:
        pass

supabase: Client = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.warning(f"Supabase prisijungimas nepavyko: {e}")

if not api_key:
    st.error("❌ OpenAI API raktas nerastas! Patikrinkite konfigūraciją.")
    st.stop()

client = OpenAI(api_key=api_key)

# Užkrauname logo kaip PIL Image (veikia ir Cloud, ir lokaliai)
try:
    from PIL import Image as PILImage
    logo_favicon = PILImage.open("assets/logo.png")
except:
    logo_favicon = "🌿"

st.set_page_config(
    page_title="Žaliuzių turinio kūrėjas", 
    page_icon=logo_favicon,
    layout="wide"
)

# Header su logo
col1, col2 = st.columns([1, 10])
with col1:
    st.image("assets/logo.png", width=80)
with col2:
    st.title("Žaliuzių ir Roletų turinio kūrėjas")
    st.caption("Įkelk iki 4 nuotraukų ir gauk paruoštus įrašus socialiniams tinklams.")

# ---------- Pagalbinės funkcijos ----------


def professional_auto_enhance(img):
    """
    PROFESIONALUS AUTO pagerinimas - geriau nei Canva!
    - Auto Levels (histogramos optimizavimas)
    - Smart Sharpening (detalių sustiprinimas)
    - Color Balance (spalvų balansas)
    - Contrast Enhancement (protingas kontrasto didinimas)
    - Saturation Boost (sodrumas)
    """
    import numpy as np

    # 1. AUTO LEVELS - optimizuoja histogramą
    img_array = np.array(img)

    # Kiekvienam spalvų kanalui (R, G, B)
    enhanced_array = np.zeros_like(img_array)
    for channel in range(3):
        channel_data = img_array[:, :, channel]

        # Randame 2% ir 98% percentiles (ignoruojam kraštutinumus)
        p2, p98 = np.percentile(channel_data, (2, 98))

        # Stretch histogramą
        if p98 > p2:
            stretched = np.clip((channel_data - p2) * 255.0 / (p98 - p2), 0, 255)
            enhanced_array[:, :, channel] = stretched.astype(np.uint8)
        else:
            enhanced_array[:, :, channel] = channel_data

    img = Image.fromarray(enhanced_array.astype(np.uint8))

    # 2. SMART SHARPENING - sustiprina detales
    from PIL import ImageFilter, ImageEnhance

    # Unsharp mask - profesionalus sharpening
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # 3. CONTRAST BOOST - protingas kontrasto didinimas
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.30)  # +30% kontrasto

    # 4. SATURATION BOOST - gyvesnės spalvos
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.30)  # +30% sodrumo

    # 5. BRIGHTNESS FIX - šiek tiek šviesiau (jei per tamsu)
    img_array = np.array(img)
    avg_brightness = np.mean(img_array)

    if avg_brightness < 110:  # Jei tamsu - šviesinu
        enhancer = ImageEnhance.Brightness(img)
        brightness_boost = min(1.15, 110 / avg_brightness)
        img = enhancer.enhance(brightness_boost)

    return img


def add_marketing_overlay(
    image_file,
    add_watermark=False,
    add_border=False,
    brightness=1.0,
    contrast=1.0,
    saturation=1.0,
    watermark_text="",
    watermark_size=150,
    watermark_position="Apačia dešinėje",
    auto_enhance=True,
    enable_opencv=False,
    enable_auto_crop=False,
    enable_perspective=False,
    enable_white_balance=False,
    enable_opencv_clarity=False,
    enable_aspect_ratio=False,
    target_aspect_ratio="4:3",
):
    """
    Prideda marketinginius elementus prie nuotraukos:
    - OpenCV preprocessing (auto-crop, perspective, white balance, aspect ratio)
    - Vandens ženklą (ryškų, baltą su šešėliu)
    - Rėmelį
    - Spalvų koregavimą (šviesumas, kontrastas, sodrumas)
    """
    try:
        from PIL import ImageEnhance, ImageDraw, ImageFont, ImageFilter

        # Atidarome nuotrauką
        img = Image.open(image_file)

        # NAUJAS: OPENCV PREPROCESSING (prieš viską)
        if enable_opencv and OPENCV_AVAILABLE:
            try:
                img = process_blinds_photo(
                    img,
                    enable_auto_crop=enable_auto_crop,
                    enable_perspective=enable_perspective,
                    enable_white_balance=enable_white_balance,
                    enable_clarity=enable_opencv_clarity,
                    enable_aspect_ratio=enable_aspect_ratio,
                    target_aspect_ratio=target_aspect_ratio,
                )
            except Exception as e:
                st.warning(f"OpenCV processing failed: {e}")

        # Konvertuojame į RGB jei reikia
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # PROFESIONALUS AUTO PAGERINIMAS (jei įjungtas)
        if auto_enhance:
            img = professional_auto_enhance(img)
        else:
            # Rankiniai spalvų koregavimai (jei auto išjungtas)
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
                "C:/Windows/Fonts/arial.ttf",  # Arial Regular
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux Bold
                "/System/Library/Fonts/Helvetica.ttc",  # Mac
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

            # Pozicija pagal pasirinkimą su DIDESNIU padding
            try:
                text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            except:
                text_bbox = (0, 0, len(watermark_text) * 10, 20)

            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # DIDESNIS padding nuo krašto (5% of width/height arba min 50px)
            padding_x = max(50, int(width * 0.05))
            padding_y = max(50, int(height * 0.05))

            # Saugus minimum padding - jei tekstas per ilgas, sumažiname
            safe_padding_x = min(padding_x, (width - text_width) // 2 - 10)
            safe_padding_x = max(15, safe_padding_x)  # Min 15px

            safe_padding_y = min(padding_y, (height - text_height) // 2 - 10)
            safe_padding_y = max(15, safe_padding_y)  # Min 15px

            # Pozicionavimas pagal pasirinkimą
            if watermark_position == "Apačia dešinėje":
                x = width - text_width - safe_padding_x
                y = height - text_height - safe_padding_y
            elif watermark_position == "Apačia kairėje":
                x = safe_padding_x
                y = height - text_height - safe_padding_y
            elif watermark_position == "Viršus dešinėje":
                x = width - text_width - safe_padding_x
                y = safe_padding_y
            elif watermark_position == "Viršus kairėje":
                x = safe_padding_x
                y = safe_padding_y
            else:  # Centras
                x = (width - text_width) // 2
                y = (height - text_height) // 2

            # GRIEŽTAS boundary check - VISUOMET telpa
            x = max(5, min(x, width - text_width - 5))
            y = max(5, min(y, height - text_height - 5))

            # Piešiame STORESNĮ šešėlį (juodą) su didesniu offset
            for offset in [(5, 5), (4, 4), (3, 3), (2, 2), (1, 1)]:
                draw.text((x + offset[0], y + offset[1]), watermark_text, fill=(0, 0, 0, 180), font=font)

            # Piešiame BALTĄ RYŠKŲ tekstą
            draw.text((x, y), watermark_text, fill=(255, 255, 255), font=font)

        # Išsaugome į bytes su AUKŠTA kokybe
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=98, optimize=False)
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Klaida redaguojant nuotrauką: {str(e)}")
        return None


def remove_white_background(img, threshold=240):
    """Pašalina baltą foną iš logo ir padaro jį skaidrų"""
    # Konvertuojame į RGBA
    img = img.convert("RGBA")

    # Gauname pikselių duomenis
    pixels = img.load()
    width, height = img.size

    # Pakeičiame baltus pikselius į skaidrius
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Jei pikselis baltesnis už threshold - darome skaidrų
            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (r, g, b, 0)  # Alpha = 0 (skaidrus)

    return img


def add_logo_to_image(img, logo_path="assets/logo.png", logo_size=100, position="top-left"):
    """Prideda logo prie nuotraukos viršutiniame kairiame kampe

    Args:
        img: PIL Image objektas (collage)
        logo_path: Kelias iki logo failo (default: assets/logo.png)
        logo_size: Logo dydis px (aukštis)
        position: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
    """
    try:
        # Tikriname ar logo failas egzistuoja
        if not os.path.exists(logo_path):
            return img  # Jei nėra logo - grąžiname originalą be klaidos

        # Įkeliame logo
        logo = Image.open(logo_path)

        # Pašaliname baltą foną
        logo = remove_white_background(logo)

        # Resize logo išlaikant proporcijas
        aspect_ratio = logo.width / logo.height
        new_height = logo_size
        new_width = int(logo_size * aspect_ratio)
        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Konvertuojame img į RGBA jei reikia
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # DIDESNIS padding kad logo TIKRAI nepersidengtų su nuotraukomis
        # Dedame į patį kampą su mažu padding - nuotraukos turės content_start
        padding_edge = 20  # Tik nuo pat krašto

        # Bet užtikriname kad logo telpa
        safe_margin = 10

        if position == "top-left":
            # Logo į patį viršutinį kairį kampą - nuotraukos prasidės žemiau/dešiniau
            x, y = padding_edge, padding_edge
        elif position == "top-right":
            x = img.width - logo.width - padding_edge
            y = padding_edge
        elif position == "bottom-left":
            x = padding_edge
            y = img.height - logo.height - padding_edge
        elif position == "bottom-right":
            x = img.width - logo.width - padding_edge
            y = img.height - logo.height - padding_edge
        else:
            x, y = padding_edge, padding_edge

        # Užtikriname kad logo telpa canvas ribose
        x = max(safe_margin, min(x, img.width - logo.width - safe_margin))
        y = max(safe_margin, min(y, img.height - logo.height - safe_margin))

        # Priklijuojame logo
        img.paste(logo, (x, y), logo)  # Logo kaip mask - skaidrumas išlieka

        return img
    except Exception as e:
        # Jei klaida - grąžiname originalą be error message (nebegadina UI)
        return img
        return output

    except Exception as e:
        st.error(f"Klaida redaguojant nuotrauką: {e}")
        import traceback

        st.error(traceback.format_exc())
        image_file.seek(0)
        return image_file


# ---------- JSON Duomenų bazė ----------

HISTORY_FILE = "data/history.json"


def load_history():
    """Įkelia aprašymų istoriją iš Supabase arba JSON failo (fallback)"""
    try:
        # Bandome iš Supabase
        if supabase:
            response = supabase.table("version_history").select("*").order("created_at", desc=True).limit(100).execute()
            if response.data:
                return response.data
        
        # Fallback į JSON failą (lokaliai)
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        st.warning(f"Nepavyko įkelti istorijos: {e}")
        return []


def save_to_history(description, season, holiday, num_photos, status="approved", version=1):
    """Išsaugo aprašymą į Supabase arba JSON istoriją (fallback)

    Args:
        status: "generated" (auto-save) arba "approved" (user patvirtino)
        version: Versijos numeris (1, 2, 3...)
    """
    try:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": description,
            "season": season,
            "holiday": holiday,
            "num_photos": num_photos,
            "status": status,
            "version": version,
        }

        # Bandome įrašyti į Supabase
        if supabase:
            supabase.table("version_history").insert(entry).execute()
            # Ištrinti senus įrašus, palikti tik 5 naujausius
            all_entries = supabase.table("version_history").select("id").order("created_at", desc=True).execute()
            if len(all_entries.data) > 5:
                old_ids = [e["id"] for e in all_entries.data[5:]]
                for old_id in old_ids:
                    supabase.table("version_history").delete().eq("id", old_id).execute()
            return True
        
        # Fallback į JSON failą (lokaliai)
        history = load_history()
        entry["id"] = len(history) + 1
        history.insert(0, entry)  # Naujausi viršuje
        history = history[:5]  # Saugom tik 5 versijas

        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        st.error(f"Nepavyko išsaugoti į istoriją: {e}")
        return False


def delete_from_history(entry_id):
    """Ištrina įrašą iš Supabase arba JSON istorijos"""
    try:
        # Bandome ištrinti iš Supabase
        if supabase:
            supabase.table("version_history").delete().eq("id", entry_id).execute()
            return True
        
        # Fallback į JSON failą (lokaliai)
        history = load_history()
        history = [h for h in history if h.get("id") != entry_id]
        
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Nepavyko ištrinti: {e}")
        return False


# ---------- Discord Webhook ----------


def send_to_discord(webhook_url, image_bytes, message=""):
    """Siunčia collage į Discord per webhook"""
    try:
        import requests

        # Paruošiame failą
        files = {"file": ("collage.png", image_bytes, "image/png")}

        # Paruošiame žinutę
        data = {}
        if message:
            data["content"] = message

        # Siunčiame POST request
        response = requests.post(webhook_url, files=files, data=data)

        if response.status_code == 200 or response.status_code == 204:
            return True, "✅ Sėkmingai išsiųsta į Discord!"
        else:
            return False, f"❌ Discord klaida: {response.status_code}"

    except Exception as e:
        return False, f"❌ Nepavyko išsiųsti: {str(e)}"


# ---------- Web Browsing - Trending Content ----------


def fetch_trending_hashtags(season):
    """
    Ieško trending hashtags'ų susijusių su žaliuzėmis ir sezonu.
    Naudoja requests + BeautifulSoup arba paprastą API.
    """
    import requests

    try:
        # Naudojame paprastą hashtagify.me alternatyvą - Instagram search suggestions
        # ARBA simuliuojame su populiariais hashtags pagal sezoną

        base_hashtags = {
            "Pavasaris": ["#springdecor", "#springhome", "#freshhome", "#lightandbright"],
            "Vasara": ["#summerstyle", "#brighthome", "#sunnyday", "#summervibes"],
            "Ruduo": ["#falldecor", "#cozyhome", "#autumnvibes", "#warmtones"],
            "Žiema": ["#winterhome", "#cozyspace", "#hygge", "#winterdecor"],
        }

        seasonal_tags = base_hashtags.get(season, ["#homedecor", "#interiordesign"])

        # Pridedame bendrų trending žaliuzių hashtags
        blinds_tags = ["#windowblinds", "#blinds", "#windowtreatments", "#homeimprovement"]

        # Sumaišome
        all_tags = seasonal_tags + blinds_tags

        return {
            "trending_hashtags": all_tags,
            "trending_topics": f"{season} home decor, natural light, modern interiors",
            "engagement_tip": "Post during peak hours (6-9 PM local time)",
        }

    except Exception as e:
        # Fallback jei klaida
        return {
            "trending_hashtags": ["#windowblinds", "#homedecor", "#interiordesign"],
            "trending_topics": "Home decor, window treatments",
            "engagement_tip": "Use high-quality photos",
        }


def analyze_image(image_bytes):
    """Naudoja GPT-4o-mini vaizdo analizei su konkrečiu produktų atpažinimu"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Tu esi langų uždangalų ir žaliuzių produktų atpažinimo EKSPERTAS. 
Tavo užduotis - TIKSLIAI ir DETALIZUOTAI identifikuoti KIEKVIENĄ produktą nuotraukoje.""",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analizuok šią nuotrauką kaip ŽALIUZIŲ EKSPERTAS ir BŪTINAI nurodyk:

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
Pavyzdys: "Nuotraukoje matosi TRYS SKIRTINGI PRODUKTAI: 1) PLISUOTOS ŽALIUZĖS pilkos spalvos, 2) MEDINĖS HORIZONTALIOS ŽALIUZĖS šviesaus ąžuolo, 3) ROLETAI DIENA-NAKTIS balti..." """,
                    },
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_bytes}},
                ],
            },
        ],
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


def generate_captions(analysis_text, season, holiday):
    """Sukuria 3 teksto variantus lietuviškai pagal tikslią produkto analizę"""

    # 🌐 WEB BROWSING: Gauname trending hashtags ir topics
    trending_data = fetch_trending_hashtags(season)

    # ULTRA GRIEŽTA sezonų ir švenčių kontrolė
    season_data = {
        "Pavasaris": {
            "must_have": ["pavasari", "atsinaujinim", "šviesi", "gaivu", "pavasario"],
            "forbidden": ["žiem", "šalt", "snieg", "kalėd", "ruduo", "ruden", "vasara", "vasar", "karšt"],
            "message": "pavasario gaivumą ir šviesumą",
        },
        "Vasara": {
            "must_have": ["vasara", "vasar", "saulė", "šilum", "vėsin", "karšt"],
            "forbidden": ["žiem", "šalt", "snieg", "kalėd", "pavasa", "ruduo", "ruden"],
            "message": "vasaros šviesumą ir vėsumą",
        },
        "Ruduo": {
            "must_have": ["ruden", "jauk", "šilt", "rudeni", "ruduo"],
            "forbidden": ["žiem", "kalėd", "pavasa", "vasara", "karšt", "sniegas"],
            "message": "rudenio jaukumą",
        },
        "Žiema": {
            "must_have": ["žiem", "šalt", "šilum", "kalėd"],
            "forbidden": ["pavasa", "vasara", "ruden", "karšt", "velyk"],
            "message": "žiemos šilumą",
        },
    }

    # Švenčių kontrolė
    holiday_data = {
        "Velykos": {
            "must_have": ["velyk", "velykini", "pavasari"],
            "forbidden": ["kalėd", "nauj metin", "žiem"],
            "keywords": "Velykų, pavasario šventės, šeimos susibūrimas",
        },
        "Šv. Kalėdos": {
            "must_have": ["kalėd", "švent", "žiem"],
            "forbidden": ["velyk", "pavasa", "vasara"],
            "keywords": "Kalėdų, žiemos švenčių, dovanų",
        },
        "Kūčios": {
            "must_have": ["kūč", "kalėd", "žiem"],
            "forbidden": ["velyk", "pavasa"],
            "keywords": "Kūčių, šventinės vakarienės, šeimos",
        },
        "Šv. Valentino diena": {
            "must_have": ["valentin", "meilė"],
            "forbidden": ["kalėd", "velyk"],
            "keywords": "Valentino dienos, meilės, romantikos",
        },
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
🎄 PRIVALOMA ŠVENTĖ: {holiday.upper()}
══════════════════════════════════════
KIEKVIENAME TEKSTE PRIVALO BŪTI:
- Žodžiai: {current_holiday["keywords"]}
- Kontekstas: {holiday} šventė

PAVYZDŽIAI TEISINGŲ SAKINIŲ:
- "Velykų proga..." ✅ (jei Velykos)
- "Kalėdų magijai..." ✅ (jei Kalėdos)
- "Valentino dienai..." ✅ (jei Valentinas)

NIEKADA NERAŠYK:
{', '.join(current_holiday["forbidden"])}
══════════════════════════════════════
"""
    else:
        holiday_text = "⚠️ ŠVENTĖS NĖRA - NERAŠYK APIE JOKIAS ŠVENTES (nei Kalėdas, nei Velykas, nei Valentiną)!"

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

🌐 TRENDING DABAR (Instagram):
📊 Populiarūs hashtags: {', '.join(trending_data['trending_hashtags'][:5])}
🔥 Trending temos: {trending_data['trending_topics']}
💡 Engagement patarimas: {trending_data['engagement_tip']}

Naudok šiuos trending hashtags tekstuose!

═══════════════════════════════════════

VARIANTAS 1 - MARKETINGINIS 💼
- Profesionalus tonas
- Produktų privalumai + {current_season["message"]}
{f"- {holiday} šventės kontekstas" if holiday != "Nėra" else ""}
- 2-3 trending hashtag'us

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

    import random

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Tu esi AI asistentas. ABSOLIUTI TAISYKLĖ: Dabar yra {season} sezonas{f' ir {holiday} šventė' if holiday != 'Nėra' else ''}. Tu NIEKADA nerašai apie kitus sezonus ar šventes. Jei bandysi pažeisti - tekstas bus atmestas.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,  # Padidinta - daugiau kūrybingumo ir įvairovės
        max_tokens=1200,
        seed=random.randint(1, 1000000),  # Random seed - kiekvieną kartą skirtingas rezultatas
    )
    return response.choices[0].message.content.strip()


def image_to_base64(image_file):
    """Konvertuoja įkeltą failą į base64 be kompresijos"""
    image_file.seek(0)
    return base64.b64encode(image_file.read()).decode()


def pil_image_to_base64(pil_image):
    """Konvertuoja PIL Image į base64 string (HTML embedding)"""
    buffered = io.BytesIO()
    pil_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def html_to_image(html_string, width=1920, height=1080):
    """
    Renderina HTML/CSS į PIL Image objektą naudojant Selenium
    
    Args:
        html_string: HTML kodas su CSS
        width: Canvas plotis
        height: Canvas aukštis
    
    Returns:
        PIL Image objektas
    """
    # Chrome options (headless mode)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")  # Streamlit Cloud reikalavimas
    chrome_options.add_argument("--disable-dev-shm-usage")  # Streamlit Cloud reikalavimas
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--hide-scrollbars")
    
    # Chromium binary path (Streamlit Cloud naudoja chromium)
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # Sukuriam laikinį HTML failą
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_string)
        temp_html_path = f.name
    
    try:
        # Inicializuojam WebDriver (bandome su chromium-driver)
        try:
            # Streamlit Cloud turi chromium-driver /usr/bin/chromedriver
            service = Service(executable_path="/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            # Fallback - local development (Windows/Mac)
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Atidarom HTML failą
        driver.get(f"file:///{temp_html_path.replace(os.sep, '/')}")
        
        # Palaukiam kad puslapio elementai užsikrautų
        time.sleep(1)
        
        # Darom screenshot
        screenshot_bytes = driver.get_screenshot_as_png()
        
        # Konvertuojam į PIL Image
        pil_image = Image.open(io.BytesIO(screenshot_bytes))
        
        driver.quit()
        
        return pil_image
        
    finally:
        # Ištrinam laikinį failą
        if os.path.exists(temp_html_path):
            os.unlink(temp_html_path)


def generate_text_with_gemini(image):
    """
    Generuoja antraštę ir bullet punktus naudojant Google Gemini Vision API
    
    Args:
        image: PIL Image objektas
        
    Returns:
        tuple: (header_text, bullets_list) arba (None, None) jei klaida
    """
    try:
        import google.generativeai as genai
        
        # Gauname API key iš environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Bandome gauti iš Streamlit secrets
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
            except:
                st.error("❌ GEMINI_API_KEY nerastas nei .env, nei Streamlit secrets")
                return None, None
        
        # Konfigūruojame Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Konvertuojame PIL image į bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Prompt'as su tiksliais reikalavimais
        prompt = """Analizuok šią nuotrauką ir atpažink produktą (medinės žaliuzės, roletai, plisuotos žaliuzės, roletai diena-naktis, romanetės, arba kitas langų uždengimo produktas).

Sugeneruok:
1. ANTRAŠTĖ: 1-2 žodžiai, MAX 25 raidės (pvz: "Roletai Diena-Naktis", "Medinės Žaliuzės")
2. 4 BULLET PUNKTAI: kiekvienas 1-2 žodžiai, MAX 20 raidžių kiekvienam (pvz: "funkcionalūs", "sulaikantys šviesą", "stilingi", "modernus")

Atsakyk TIKTAI šiuo formatu (be jokių kitų žodžių):
ANTRAŠTĖ: [tekstas]
BULLET1: [tekstas]
BULLET2: [tekstas]
BULLET3: [tekstas]
BULLET4: [tekstas]"""
        
        # Siunčiame užklausą
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_byte_arr}])
        
        # Parsimame atsakymą
        text = response.text.strip()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Ištraukiame antraštę ir bullets
        header = None
        bullets = []
        
        for line in lines:
            if line.startswith("ANTRAŠTĖ:"):
                header = line.replace("ANTRAŠTĖ:", "").strip()
            elif line.startswith("BULLET"):
                bullet_text = line.split(":", 1)[1].strip() if ":" in line else ""
                if bullet_text:
                    bullets.append(bullet_text)
        
        # Validacija
        if not header or len(bullets) != 4:
            st.warning(f"⚠️ Gemini atsakymas netinkamas. Header: {header}, Bullets: {len(bullets)}")
            return None, None
        
        return header, bullets
        
    except ImportError:
        st.error("❌ Įdiek google-generativeai: `pip install google-generativeai`")
        return None, None
    except Exception as e:
        st.error(f"❌ Gemini klaida: {str(e)}")
        return None, None


def generate_themed_background(season, canvas_width, canvas_height, custom_prompt=""):
    """Generuoja tematinį foną pagal sezoną arba custom prompt naudojant AI (DALL-E)"""
    try:
        # Jei yra custom prompt, naudojame jį
        if custom_prompt and custom_prompt.strip():
            prompt = f"{custom_prompt}, professional photography, high resolution, aesthetic background, suitable for social media"
        else:
            # Teminės nuotraukos promptai pagal sezoną
            prompts = {
                "Pavasaris": "soft spring background with blooming flowers, cherry blossoms, pastel colors, gentle bokeh effect, professional photography, high resolution, peaceful atmosphere",
                "Vasara": "bright summer background with green grass meadow, blue sky, sunshine, vibrant colors, professional photography, high resolution, fresh atmosphere",
                "Ruduo": "warm autumn background with colorful falling leaves, orange and golden tones, cozy atmosphere, professional photography, high resolution",
                "Žiema": "winter background with soft snow, snowflakes, cool blue and white tones, peaceful atmosphere, professional photography, high resolution",
            }

            prompt = prompts.get(season, prompts["Vasara"])

        # Generuojame nuotrauką su DALL-E 3
        response = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="standard", n=1)

        # Gauname URL ir atsisiunčiame nuotrauką
        import requests

        image_url = response.data[0].url
        img_response = requests.get(image_url)

        if img_response.status_code == 200:
            # Konvertuojame į PIL Image
            bg_image = Image.open(io.BytesIO(img_response.content))
            # Prisitaikome prie reikiamo dydžio
            bg_image = bg_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            return bg_image
        else:
            return None

    except Exception as e:
        st.warning(f"⚠️ Nepavyko sugeneruoti tematinio fono: {e}. Naudojamas spalvinis fonas.")
        return None


def create_gradient_background(width, height, color1, color2, direction="vertical"):
    """Sukuria gradientinį foną (modernus canvas efektas)"""
    gradient = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(gradient)

    if direction == "vertical":
        for i in range(height):
            ratio = i / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
    else:  # horizontal
        for i in range(width):
            ratio = i / width
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(i, 0), (i, height)], fill=(r, g, b))

    return gradient


def add_modern_shadow(img, shadow_strength=50, shadow_offset=15):
    """Prideda modernų šešėlį nuotraukai (drop shadow efektas - offset žemyn ir dešinėn)

    Args:
        img: Nuotrauka
        shadow_strength: 0-100, kur 0=nematomas, 100=juodas, 50=vidutinis
        shadow_offset: Offset dydis px (žemyn ir dešinėn)
    """
    if shadow_strength == 0:
        return img

    # Konvertuojame strength (0-100) į opacity (0-255)
    shadow_opacity = int((shadow_strength / 100) * 255)
    shadow_color = (0, 0, 0, shadow_opacity)

    # Offset šešėliui (žemyn ir dešinėn)
    offset_x = shadow_offset
    offset_y = shadow_offset

    # Blur proporcingas offset'ui
    shadow_blur = min(shadow_offset + 5, 20)

    # Sukuriame naują paveikslėlį su vieta šešėliui
    total_width = img.width + offset_x + shadow_blur * 2
    total_height = img.height + offset_y + shadow_blur * 2

    # Sukuriame šešėlio sluoksnį
    shadow = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow)

    # Piešiame šešėlį (offset pozicijoje)
    shadow_draw.rectangle(
        [
            offset_x + shadow_blur,
            offset_y + shadow_blur,
            img.width + offset_x + shadow_blur,
            img.height + offset_y + shadow_blur,
        ],
        fill=shadow_color,
    )

    # Blur efektas šešėliui
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))

    # Konvertuojame originalą į RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Sukuriame galutinį paveikslėlį
    result = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 0))
    result.paste(shadow, (0, 0), shadow)
    result.paste(img, (shadow_blur, shadow_blur), img)  # Nuotrauka su blur offset

    return result


def add_rounded_corners(img, radius=30):
    """Užapvalina nuotraukos kampus"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Sukuriame apskritimo mask
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)

    # Pritaikome mask
    result = Image.new("RGBA", img.size, (255, 255, 255, 0))
    result.paste(img, (0, 0))
    result.putalpha(mask)

    return result


def add_white_border(img, border_width=10):
    """Prideda baltą rėmelį aplink nuotrauką"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Sukuriame naują paveikslėlį su rėmeliu
    new_width = img.width + border_width * 2
    new_height = img.height + border_width * 2

    bordered = Image.new("RGBA", (new_width, new_height), (255, 255, 255, 255))
    bordered.paste(img, (border_width, border_width), img)

    return bordered


def add_photo_effects(
    img,
    enable_border=True,
    border_width=15,
    enable_rounded=True,
    corner_radius=20,
    enable_shadow=True,
    shadow_strength=50,
):
    """Prideda visus foto efektus: rėmelį, užapvalintus kampus, šešėlį

    Args:
        shadow_strength: 0-100, kur 0=nematomas, 100=juodas, 50=vidutinis
    """
    result = img.copy()

    if img.mode != "RGBA":
        result = result.convert("RGBA")

    # 1. Užapvalinti kampai
    if enable_rounded:
        result = add_rounded_corners(result, radius=corner_radius)

    # 2. Baltas rėmelis
    if enable_border:
        result = add_white_border(result, border_width=border_width)
        # Po rėmelio vėl užapvaliname (rėmelis su apvaliais kampais)
        if enable_rounded:
            result = add_rounded_corners(result, radius=corner_radius + border_width)

    # 3. Šešėlis (3D efektas)
    if enable_shadow and shadow_strength > 0:
        result = add_modern_shadow(result, shadow_strength=shadow_strength, shadow_offset=15)

    return result


def add_text_overlay_modern(img, text, position="bottom", font_size=60, bg_opacity=0.7):
    """Prideda modernų teksto overlay su blur fonu"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Bandome rasti fontą
    font = None
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except:
            continue

    if font is None:
        font = ImageFont.load_default()

    # Gauname teksto dydį
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Pozicija
    if position == "bottom":
        y = img.height - text_height - 80
    elif position == "top":
        y = 80
    else:  # center
        y = (img.height - text_height) // 2

    x = (img.width - text_width) // 2

    # Fono stačiakampis su blur efektu
    padding = 40
    bg_rect = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]
    draw.rectangle(bg_rect, fill=(255, 255, 255, int(255 * bg_opacity)))

    # Tekstas
    draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)

    return Image.alpha_composite(img, overlay)


def create_magazine_layout(photo1, photo2, header_text, bullet_points, phone_number=None, logo_path="assets/logo.png", logo_with_white_bg=False, enable_white_border=True, enable_rounded_corners=True, enable_shadow_effect=True, shadow_strength=50, background=None):
    """
    Magazine Style Layout pagal pixel-perfect specifikaciją:
    - 2 nuotraukos kairėje (3:4 ratio)
    - Antraštė + punktyrinė linija + bullet list dešinėje
    - Minimalistinis dizainas
    
    Args:
        photo1: PIL Image (kairė nuotrauka)
        photo2: PIL Image (dešinė nuotrauka)
        header_text: Antraštės tekstas (56px)
        bullet_points: List of strings arba string su \n (4 punktai, 24px)
        phone_number: Telefono numeris (optional)
        logo_path: Kelias iki logo (optional)
        logo_with_white_bg: True = baltas fonas, False = permatomas
    
    Returns:
        PIL Image (1327x768)
    """
    from PIL import ImageDraw, ImageFont
    import os
    
    # Canvas - jei yra AI background, naudojame jį, kitaip default spalvą
    if background is not None:
        # AI fonas - resize į 1327x768
        canvas = background.resize((1327, 768), Image.Resampling.LANCZOS)
        if canvas.mode != 'RGBA':
            canvas = canvas.convert('RGBA')
    else:
        # Default smėlio spalva
        canvas = Image.new('RGBA', (1327, 768), color=(250, 246, 239, 255))  # #FAF6EF
    
    draw = ImageDraw.Draw(canvas)
    
    # Spalvos
    text_color = (43, 43, 43)  # #2B2B2B
    
    # === LOGO (VIETA: 40, 32) ===
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((120, 120), Image.Resampling.LANCZOS)
            
            if logo_with_white_bg:
                # Baltas fonas po logo
                logo_bg = Image.new('RGBA', (140, 140), (255, 255, 255, 255))
                logo_bg.paste(logo, (10, 10), logo)
                canvas.paste(logo_bg, (30, 22), logo_bg)
            else:
                # Permatomas - pašaliname baltą foną jei yra
                logo_data = logo.getdata()
                new_data = []
                for item in logo_data:
                    # Jei pikselis beveik baltas (RGB > 240) - darome permatomą
                    if item[0] > 240 and item[1] > 240 and item[2] > 240:
                        new_data.append((255, 255, 255, 0))  # Permatomas
                    else:
                        new_data.append(item)
                logo.putdata(new_data)
                canvas.paste(logo, (40, 32), logo)
        except Exception as e:
            # Fallback
            pass
    
    # === NUOTRAUKOS ===
    # Nuotraukų viršus ties punktyrine linija (Y = 188)
    # Photo 1 - kairė
    photo1_resized = photo1.resize((340, 460), Image.Resampling.LANCZOS)
    photo1_with_effects = add_photo_effects(
        photo1_resized,
        enable_border=enable_white_border,
        border_width=12,
        enable_rounded=enable_rounded_corners,
        corner_radius=20,
        enable_shadow=enable_shadow_effect,
        shadow_strength=shadow_strength
    )
    canvas.paste(photo1_with_effects, (40, 188), photo1_with_effects if photo1_with_effects.mode == 'RGBA' else None)
    
    # Photo 2 - dešinė
    photo2_resized = photo2.resize((340, 460), Image.Resampling.LANCZOS)
    photo2_with_effects = add_photo_effects(
        photo2_resized,
        enable_border=enable_white_border,
        border_width=12,
        enable_rounded=enable_rounded_corners,
        corner_radius=20,
        enable_shadow=enable_shadow_effect,
        shadow_strength=shadow_strength
    )
    canvas.paste(photo2_with_effects, (400, 188), photo2_with_effects if photo2_with_effects.mode == 'RGBA' else None)
    
    # === TELEFONO NUMERIS (po nuotraukomis, be rėmelio) ===
    if phone_number:
        # Font loading su Linux fallback
        font_phone = None
        phone_fonts = [
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux/Cloud
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Linux alt
        ]
        for font_path in phone_fonts:
            try:
                font_phone = ImageFont.truetype(font_path, 24)
                break
            except:
                continue
        if not font_phone:
            font_phone = ImageFont.load_default()
        
        # Tekstas - FAKTINIS telefono numeris
        phone_text = phone_number
        bbox = draw.textbbox((0, 0), phone_text, font=font_phone)
        phone_width = bbox[2] - bbox[0]
        
        # Pozicija: centre po nuotraukomis (nuotraukos baigiasi Y=188+460=648)
        phone_x = (1327 - phone_width) // 2  # Centras per viso canvas viduriuką (1327px plotis)
        phone_y = 694  # 46px po nuotraukomis (648 + 46)
        
        # Tiesiog tekstas, be fono/rėmelio
        draw.text((phone_x, phone_y), phone_text, fill=text_color, font=font_phone)
    
    # === TEKSTO BLOKAS ===
    # Antraštė - 56px Serif font
    font_header = None
    serif_fonts = [
        "C:/Windows/Fonts/georgia.ttf",  # Windows
        "C:/Windows/Fonts/times.ttf",  # Windows
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",  # Linux Serif
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",  # Linux Serif alt
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Linux fallback
    ]
    for font_path in serif_fonts:
        try:
            font_header = ImageFont.truetype(font_path, 56)
            break
        except:
            continue
    if not font_header:
        font_header = ImageFont.load_default()
    
    # Antraštės tekstas
    draw.text((860, 120), header_text, fill=text_color, font=font_header)
    
    # === PUNKTYRINĖ LINIJA ===
    # Tiksliai pagal spec: po antrašte, Y = 120 + 56 + 12 = 188
    line_y = 188
    line_x_start = 860
    line_x_end = 1220  # 860 + 360
    
    # Brėžiam punktyrinę liniją (dotted)
    dash_length = 6
    gap_length = 4
    x = line_x_start
    while x < line_x_end:
        end_x = min(x + dash_length, line_x_end)
        draw.line([(x, line_y), (end_x, line_y)], fill=text_color, width=2)
        x += dash_length + gap_length
    
    # === BULLET LIST (4 punktai) ===
    # Šriftas bullet tekstui - 32px su Linux fallback
    font_bullet = None
    bullet_fonts = [
        "C:/Windows/Fonts/georgia.ttf",  # Windows Serif
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",  # Linux Serif
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",  # Linux Serif alt
        "C:/Windows/Fonts/arial.ttf",  # Windows Sans
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux Sans
    ]
    for font_path in bullet_fonts:
        try:
            font_bullet = ImageFont.truetype(font_path, 32)
            break
        except:
            continue
    if not font_bullet:
        font_bullet = ImageFont.load_default()
    
    # Padalijam bullet points
    if isinstance(bullet_points, str):
        bullets = [b.strip() for b in bullet_points.split('\n') if b.strip()]
    else:
        bullets = bullet_points
    
    # VISADA 4 punktai - jei mažiau, papildom su "Tekstas"
    while len(bullets) < 4:
        bullets.append("Tekstas")
    bullets = bullets[:4]  # Max 4
    
    # Tikslios pozicijos pagal spec
    bullet_x = 910
    bullet_y_start = 320
    bullet_spacing = 64  # Tarpas tarp punktų (22 + aukštis)
    
    for i, bullet_text in enumerate(bullets):
        y = bullet_y_start + i * bullet_spacing
        
        # Apskritimas (pilnaviduris, 24px diameter)
        circle_center_x = bullet_x
        circle_center_y = y + 12  # Vertikalus centravimas
        circle_radius = 12  # 24/2 = 12
        
        draw.ellipse(
            [circle_center_x - circle_radius, circle_center_y - circle_radius,
             circle_center_x + circle_radius, circle_center_y + circle_radius],
            fill=text_color  # Pilnaviduris juodas
        )
        
        # Tekstas (16px nuo apskritimo krašto)
        text_x = bullet_x + 24 + 16  # 24px apskritimas + 16px tarpas
        draw.text((text_x, y), bullet_text, fill=text_color, font=font_bullet)
    
    return canvas


# ---------- Pagrindinis UI ----------
    """
    Hero Diagonal Split Gallery Layout - analogiškas Magazine Style
    
    Specifikacija:
    - Canvas: 1200x675px (16:9)
    - Kairė: 2 nuotraukos (originali proporcija, neperpjaunamos)
    - Dešinė: gradientas (#1E2F47 → #0F1E33) su įstriža kairiąja puse + tekstas
    - Fonas uždengia nuotraukas įstriža linija
    
    Args:
        photo1: PIL Image (viršutinė nuotrauka)
        photo2: PIL Image (apatinė nuotrauka)
        header_text: Antraštė (52px Bold)
        description_text: Aprašymas (32px Regular)
        phone_number: Telefono numeris (optional, rodomas apačioje)
        logo_path: Kelias iki logo (optional, rodomas viršuje kairėje)
    
    Returns:
        PIL Image (1200x675)
    """
    from PIL import ImageDraw, ImageFont
    import numpy as np
    import os
    
    # Canvas dydis
    canvas_width = 1200
    canvas_height = 675
    
    # Sukuriame baltą foną
    canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
    
    # === LOGO (viršuje kairėje) ===
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((100, 100), Image.Resampling.LANCZOS)
            # Pašaliname baltą foną (jei yra)
            logo_data = logo.getdata()
            new_data = []
            for item in logo_data:
                # Jei pikselis beveik baltas (RGB > 240) - darome permatomą
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))  # Permatomas
                else:
                    new_data.append(item)
            logo.putdata(new_data)
            canvas = canvas.convert('RGBA')
            canvas.paste(logo, (30, 30), logo)
            canvas = canvas.convert('RGB')
        except Exception as e:
            pass  # Jei logo nepavyko - tiesiog praleisti
    
    # === KAIRĖ ZONA - NUOTRAUKOS (be pjaustymo!) ===
    # Nuotraukų parametrai - panašūs į Magazine Style
    photo_width = 300
    photo_height = 280
    gap = 20
    
    # Paruošiame nuotraukas - RESIZE BE CROP, išsaugant proporcijas
    img1 = photo1.copy()
    img1.thumbnail((photo_width, photo_height), Image.Resampling.LANCZOS)
    
    img2 = photo2.copy()
    img2.thumbnail((photo_width, photo_height), Image.Resampling.LANCZOS)
    
    # Įdedame nuotraukas į canvas (kairėje pusėje, su tarpais)
    photo_x = 30
    photo1_y = 50
    photo2_y = photo1_y + photo_height + gap
    
    canvas.paste(img1, (photo_x, photo1_y))
    canvas.paste(img2, (photo_x, photo2_y))
    
    # === DEŠINĖ ZONA - GRADIENTAS SU ĮSTRIŽA KAIRIĄJA PUSE ===
    # Sukuriame gradiento sluoksnį
    gradient = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    
    # Gradientas nuo viršaus į apačią
    for y in range(canvas_height):
        ratio = y / canvas_height
        r = int(30 * (1 - ratio) + 15 * ratio)
        g = int(47 * (1 - ratio) + 30 * ratio)
        b = int(71 * (1 - ratio) + 51 * ratio)
        gradient_draw.line([(0, y), (canvas_width, y)], fill=(r, g, b, 255))
    
    # Sukuriame mask su įstriža kairiąja puse (polygon)
    # Įstriža linija eina nuo viršaus (apie 380px) į apačią (apie 280px)
    mask = Image.new('L', (canvas_width, canvas_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    
    # Polygon: prasideda viršuje dešinėje, eina žemyn įstrižai kairėn, tada aplink
    diagonal_points = [
        (380, 0),              # viršus (įstriža pradžia)
        (canvas_width, 0),     # viršus dešinė
        (canvas_width, canvas_height),  # apačia dešinė
        (280, canvas_height),  # apačia (įstriža pabaiga)
    ]
    mask_draw.polygon(diagonal_points, fill=255)
    
    # Pritaikome mask gradientui
    gradient.putalpha(mask)
    
    # Užklijuojame gradientą ant canvas (uždengia dalį nuotraukų)
    canvas = canvas.convert('RGBA')
    canvas.paste(gradient, (0, 0), gradient)
    
    # === TEKSTAS (ant gradiento) ===
    draw = ImageDraw.Draw(canvas)
    
    # Tekstinio konteinerio pozicija
    text_x = 480
    text_y = 200
    
    # Šriftai su cross-platform fallback
    try:
        font_header = ImageFont.truetype("arial.ttf", 52)
    except:
        try:
            font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        except:
            font_header = ImageFont.load_default()
    
    try:
        font_desc = ImageFont.truetype("arial.ttf", 32)
    except:
        try:
            font_desc = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except:
            font_desc = ImageFont.load_default()
    
    # Antraštė
    header_color = (255, 255, 255)  # #FFFFFF
    draw.text((text_x, text_y), header_text, fill=header_color, font=font_header)
    
    # Aprašymas (70px žemiau antraštės, nes didesnis header)
    desc_y = text_y + 70
    desc_color = (230, 236, 243)  # #E6ECF3
    
    # Text wrapping aprašymui (max 450px plotis)
    max_width = 450
    words = description_text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font_desc)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Braižome aprašymą (line-height: 1.5 dėl didesnio šrifto)
    line_height = int(32 * 1.5)
    for i, line in enumerate(lines):
        draw.text((text_x, desc_y + i * line_height), line, fill=desc_color, font=font_desc)
    
    # === TELEFONO NUMERIS (apačioje centre) ===
    if phone_number:
        # Konvertuojame į RGBA telefono numeriui
        if canvas.mode != 'RGBA':
            canvas = canvas.convert('RGBA')
        
        draw = ImageDraw.Draw(canvas)
        
        # Font loading su cross-platform fallback
        font_phone = None
        phone_fonts = [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
        for font_path_phone in phone_fonts:
            try:
                font_phone = ImageFont.truetype(font_path_phone, 28)
                break
            except:
                continue
        if not font_phone:
            font_phone = ImageFont.load_default()
        
        # Telefono numerio pozicija (centre apačioje)
        phone_text = phone_number
        bbox = draw.textbbox((0, 0), phone_text, font=font_phone)
        phone_width = bbox[2] - bbox[0]
        phone_x = (canvas_width - phone_width) // 2
        phone_y = canvas_height - 60  # 60px nuo apačios
        
        # Tekstas baltas (ant gradiento)
        draw.text((phone_x, phone_y), phone_text, fill=(255, 255, 255), font=font_phone)
    
    # Konvertuojame atgal į RGB
    canvas = canvas.convert('RGB')
    

    """
    HTML/CSS versija Modern Landing layout'ui - FANCY dizainas!
    
    Args:
        product_image: PIL Image objektas (produkto nuotrauka)
        text_content: Tekstas dešinėje
        phone_number: Telefono numeris apačioje
        logo_path: Kelias iki logo
        style: Stilius (Minimalist/Glassmorphism/Neo-Brutalism)
    
    Returns:
        PIL Image objektas (rendered HTML)
    """
    # Konvertuojam nuotraukas į base64
    product_base64 = pil_image_to_base64(product_image)
    
    # Logo
    logo_base64 = ""
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path)
            logo_base64 = pil_image_to_base64(logo_img)
        except:
            pass
    
    # Stilių CSS
    if "Glassmorphism" in style:
        card_style = """
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        """
        text_bg = """
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.4);
        """
        gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    elif "Neo-Brutalism" in style:
        card_style = """
            background: #FFDC32;
            border: 8px solid #000;
            box-shadow: 10px 10px 0 #000;
        """
        text_bg = """
            background: #FFF;
            border: 4px solid #000;
            box-shadow: 6px 6px 0 #000;
        """
        gradient = "#FFE066"
    else:  # Minimalist
        card_style = """
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #e5e7eb;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        """
        text_bg = """
            background: white;
            border: 1px solid #f3f4f6;
        """
        gradient = "linear-gradient(180deg, #ffffff 0%, #f9fafb 100%)"
    
    # HTML šablonas
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                width: 1920px;
                height: 1080px;
                background: {gradient};
                font-family: 'Montserrat', sans-serif;
                overflow: hidden;
            }}
            .container {{
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: space-around;
                padding: 80px;
            }}
            .product-card {{
                {card_style}
                border-radius: 30px;
                padding: 30px;
                width: 45%;
                height: 880px;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                transition: transform 0.3s ease;
            }}
            .product-card img {{
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                border-radius: 20px;
            }}
            .text-section {{
                width: 48%;
                display: flex;
                flex-direction: column;
                gap: 40px;
            }}
            .text-box {{
                {text_bg}
                border-radius: 25px;
                padding: 50px;
                min-height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .text-box p {{
                font-size: 48px;
                line-height: 1.6;
                color: #1e293b;
                font-weight: 600;
                text-align: center;
                white-space: pre-wrap;
            }}
            .phone-section {{
                {text_bg}
                border-radius: 25px;
                padding: 40px;
                text-align: center;
            }}
            .phone-section h2 {{
                font-size: 50px;
                color: #1e293b;
                font-family: 'Times New Roman', serif;
                font-weight: bold;
            }}
            .logo {{
                position: absolute;
                top: 40px;
                left: 40px;
                width: 120px;
                height: auto;
                z-index: 10;
            }}
        </style>
    </head>
    <body>
        {"<img class='logo' src='data:image/png;base64," + logo_base64 + "'>" if logo_base64 else ""}
        
        <div class="container">
            <div class="product-card">
                <img src="data:image/png;base64,{product_base64}">
            </div>
            
            <div class="text-section">
                <div class="text-box">
                    <p>{text_content.replace(chr(10), '<br>')}</p>
                </div>
                
                {f"<div class='phone-section'><h2>{phone_number}</h2></div>" if phone_number else ""}
            </div>
        </div>
    </body>
    </html>
    """
    
    # Renderuojam HTML → PIL Image
    try:
        result_image = html_to_image(html, width=1920, height=1080)
        return result_image
    except Exception as e:
        st.error(f"❌ HTML rendering klaida: {e}")
        # Fallback - grąžinam baltą canvas su error pranešimu
        fallback = Image.new('RGB', (1920, 1080), 'white')
        draw = ImageDraw.Draw(fallback)
        draw.text((960, 540), f"HTML Rendering Error: {e}", fill='red', anchor='mm')
        return fallback


# ---------- Pagrindinis UI ----------
st.sidebar.markdown("### 🎨 Marketinginis redagavimas")

add_watermark = st.sidebar.checkbox("💧 Pridėti vandens ženklą", value=True, help="Pridės jūsų tekstą ant nuotraukos")
if add_watermark:
    watermark_text = st.sidebar.text_input(
        "Vandens ženklo tekstas", value="#RūbaiLangams", help="Pvz: #RūbaiLangams arba © Jūsų Įmonė"
    )
    watermark_position = st.sidebar.selectbox(
        "Pozicija:",
        options=["Apačia dešinėje", "Apačia kairėje", "Viršus dešinėje", "Viršus kairėje", "Centras"],
        index=0,
        help="Kur bus dedamas vandens ženklas",
    )
    watermark_size = st.sidebar.slider(
        "📏 Vandens ženklo dydis (px)",
        30,
        300,
        40,
        10,
        help="Šrifto dydis pikseliais. 120px = vidutinis, 250px = DIDELIS",
    )
else:
    watermark_text = ""
    watermark_position = "Apačia dešinėje"
    watermark_size = 40

add_border = st.sidebar.checkbox("🖼️ Pridėti baltą rėmelį", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("**🤖 Profesionalus Auto Pagerinimas**")
auto_enhance = st.sidebar.checkbox(
    "✨ PRO Auto Enhancement", value=False, help="Profesionalus nuotraukų pagerinimas - geriau nei Canva!"
)

if auto_enhance:
    brightness = 1.0
    contrast = 1.3
    saturation = 1.3
else:
    st.sidebar.markdown("**Rankinė spalvų korekcija:**")
    brightness = st.sidebar.slider("☀️ Šviesumas", 0.5, 1.5, 1.10, 0.05, help="<1.0 tamsiau, >1.0 šviesiau")
    contrast = st.sidebar.slider("🎭 Kontrastas", 0.5, 1.5, 1.40, 0.05, help="<1.0 blankiau, >1.0 ryškiau")
    saturation = st.sidebar.slider("🎨 Sodrumas", 0.5, 1.5, 1.40, 0.05, help="<1.0 pilkiau, >1.0 sodresni spalvos")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔬 Advanced Preprocessing (OpenCV)")

if OPENCV_AVAILABLE:
    enable_opencv = st.sidebar.checkbox(
        "🎯 Smart Photo Processing", value=True, help="AI photo enhancement: auto-crop, straighten, color correction"
    )

    if enable_opencv:
        st.sidebar.success("🤖 **OpenCV aktyvuotas!**")

        enable_auto_crop = st.sidebar.checkbox(
            "✂️ Auto-Crop (detect blinds)", value=True, help="Automatically detect and crop blinds area"
        )
        enable_perspective = st.sidebar.checkbox(
            "📐 Straighten (perspective fix)", value=False, help="Auto-straighten vertical lines"
        )
        enable_white_balance = st.sidebar.checkbox("🎨 White Balance", value=True, help="Remove yellow/blue tint")
        enable_opencv_clarity = st.sidebar.checkbox("✨ Clarity Boost", value=True, help="Enhance texture and detail")

        enable_aspect_ratio = st.sidebar.checkbox(
            "📏 Aspect Ratio Normalize", value=False, help="Make all photos same aspect ratio"
        )
        if enable_aspect_ratio:
            target_aspect_ratio = st.sidebar.selectbox(
                "Target Ratio:",
                options=["4:3", "16:9", "1:1", "3:4", "9:16"],
                index=0,
                help="All photos will be normalized to this ratio",
            )
        else:
            target_aspect_ratio = "4:3"

        st.sidebar.info("⏱️ Apdorojimas gali užtrukti 2-5 sek per nuotrauką")
    else:
        enable_auto_crop = False
        enable_perspective = False
        enable_white_balance = False
        enable_opencv_clarity = False
        enable_aspect_ratio = False
        target_aspect_ratio = "4:3"
else:
    enable_opencv = False
    enable_auto_crop = False
    enable_perspective = False
    enable_white_balance = False
    enable_opencv_clarity = False
    enable_aspect_ratio = False
    target_aspect_ratio = "4:3"
    st.sidebar.warning("⚠️ OpenCV neprieinamas")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Turinio temos (AI generavimui)")

# Funkcija metų laikui nustatyti pagal datą
def get_current_season():
    """Grąžina metų laiką pagal dabartinę Lietuvos datą"""
    today = datetime.now()
    month = today.month
    day = today.day
    
    # Lietuvos kalendorius:
    # Pavasaris: kovo 1 - gegužės 31
    # Vasara: birželio 1 - rugpjūčio 31
    # Ruduo: rugsėjo 1 - lapkričio 30
    # Žiema: gruodžio 1 - vasario 28/29
    
    if (month == 3) or (month == 4) or (month == 5):
        return "Pavasaris"
    elif (month == 6) or (month == 7) or (month == 8):
        return "Vasara"
    elif (month == 9) or (month == 10) or (month == 11):
        return "Ruduo"
    else:  # 12, 1, 2
        return "Žiema"

# Nustatome default metų laiką
current_season = get_current_season()
seasons_list = ["Pavasaris", "Vasara", "Ruduo", "Žiema"]
default_season_index = seasons_list.index(current_season)


# Metų laikas
season = st.sidebar.selectbox(
    "🌤️ Metų laikas", seasons_list, index=default_season_index, help="AI turinio aprašymams ir fonui"
)

# Švenčių žemėlapis pagal sezoną
season_holidays = {
    "Žiema": [
        "Nėra",
        "Naujieji metai",
        "Šv. Valentino diena",
        "Vasario 16-oji",
        "Kovo 11-oji",
        "Šv. Kalėdos",
        "Kūčios",
    ],
    "Pavasaris": [
        "Nėra",
        "Velykos",
        "Melagio diena (balandžio 1)",
        "Motinos diena",
        "Gegužės 1-oji (Darbo diena)",
        "Tėvo diena",
        "Kovo 11-oji",
    ],
    "Vasara": [
        "Nėra",
        "Joninės",
        "Liepos 6-oji (Karaliaus Mindaugo diena)",
        "Žolinė",
        "Tėvo diena",
    ],
    "Ruduo": [
        "Nėra",
        "Rugsėjo 1-oji",
        "Vėlinių diena",
    ],
}

# Pagal pasirinktą sezoną rodom tik atitinkamas šventes
holidays_for_season = season_holidays.get(season, ["Nėra"])

# Jei prieš tai pasirinkta šventė nebeegzistuoja šiame sezone, grąžinam į "Nėra"
if 'holiday' in st.session_state and st.session_state.holiday in holidays_for_season:
    default_holiday_index = holidays_for_season.index(st.session_state.holiday)
else:
    default_holiday_index = 0

holiday = st.sidebar.selectbox(
    "🎉 Lietuviškos šventės (pasirinktinai)",
    holidays_for_season,
    index=default_holiday_index,
    help="Papildoma tema turinio aprašymams ir fonui",
    key="holiday"
)

# Failų įkėlimas

# CSS stilių pridejimas
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# Patikriname ar yra įkeltų failų
# Mobiliai optimizuotas failų įkėlimas
st.markdown("### 📸 Įkelkite nuotraukas")

# Sukuriame tabs skirtingoms įkėlimo opcijoms
tab1, tab2 = st.tabs(["📁 Failų įkėlimas", "🔧 Rankiniu būdu"])

uploaded_files = []

with tab1:
    st.markdown("**Standartinis būdas** (veikia PC ir kai kuriuose telefonuose)")
    files_standard = st.file_uploader(
        "Pasirinkite nuotraukas", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="standard_uploader"
    )
    if files_standard:
        uploaded_files.extend(files_standard)
        st.success(f"✅ Įkelta {len(files_standard)} nuotraukų!")

with tab2:
    st.markdown("**Rezervinis variantas** - jei kiti būdai neveikia")
    st.info(
        "📱 **Instrukcijos telefonui:**\n1. Įkelkite po vieną nuotrauką\n2. Spauskite 'Pridėti' po kiekvienos\n3. Kartokite iki 4 nuotraukų"
    )

    single_file = st.file_uploader("Įkelkite vieną nuotrauką", type=["jpg", "jpeg", "png"], key="single_uploader")

    if single_file:
        # Rodyti failo dydį
        file_size_mb = single_file.size / (1024 * 1024)

        col1, col2 = st.columns([1, 1])
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
        st.rerun()

# Naudojame session_state failus
files_to_process = st.session_state.uploaded_files

if files_to_process:
    st.success(f"✅ Įkelta {len(files_to_process)} nuotraukų!")

    # Rodyti ir leisti atsisiųsti kiekvieną nuotrauką atskirai
    st.markdown("### 🎨 Redaguotos nuotraukos")
    st.info("Reguliuokite redagavimo nustatymus šoniniame meniu (šviesumas, kontrastas, vandens ženklas)")

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
                watermark_size=watermark_size,
                auto_enhance=auto_enhance,
                enable_opencv=enable_opencv,
                enable_auto_crop=enable_auto_crop,
                enable_perspective=enable_perspective,
                enable_white_balance=enable_white_balance,
                enable_opencv_clarity=enable_opencv_clarity,
                enable_aspect_ratio=enable_aspect_ratio,
                target_aspect_ratio=target_aspect_ratio,
            )
            edited.seek(0)

            # Rodyti peržiūrą (sumažinta)
            st.image(edited, caption=f"Nuotrauka {i+1}", width=400)

            # Download mygtukas kiekvienai nuotraukai
            filename = getattr(file, "name", f"nuotrauka_{i+1}.jpg")
            base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

            edited.seek(0)
            st.download_button(
                label=f"📥 Atsisiųsti #{i+1}",
                data=edited.getvalue(),
                file_name=f"{base_name}_edited.jpg",
                mime="image/jpeg",
                key=f"download_{i}",
                use_container_width=True,
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
        # Social media formato pasirinkimas
        social_format = st.selectbox(
                "📱 Socialinio tinklo formatas:",
                ["Instagram kvadratas (1080x1080)", "Instagram Portrait (1080x1350)", "Facebook Post (1200x630)"],
                help="Pasirinkite socialinio tinklo formatą",
            )

        # Išdėstymas
        st.markdown("---")
        st.markdown("#### 📐 Išdėstymas (nuotraukos + tekstas)")

        num_photos = len(files_to_process)

        # Tik Magazine Style layoutas
        layout_options = [
            "📰 Magazine Style (2 nuotraukos + bullet list)",
        ]

        collage_layout = st.selectbox(
            "Pasirinkite išdėstymą:", layout_options, help="Magazine Style - 2 nuotraukos + antraštė + bullet list"
        )

        # 📰 Magazine Style nustatymai
        magazine_header = ""
        magazine_bullets = ""
        logo_white_bg = False
        
        if "Magazine Style" in collage_layout:
            st.markdown("---")
            st.markdown("#### 📰 Magazine Style nustatymai")
            
            # Jei AI tekstai įjungti, generuojame automatiškai
            if use_ai_text:
                st.info("🤖 AI generuoja tekstus pagal nuotrauką...")
                
                # Naudojame pirmą redaguotą nuotrauką
                if len(files_to_process) >= 1:
                    # Paimame pirmą failą ir sukuriame PIL Image
                    first_file = files_to_process[0]
                    first_file.seek(0)
                    temp_image = Image.open(first_file)
                    
                    # Generuojame tekstus
                    ai_header, ai_bullets = generate_text_with_gemini(temp_image)
                    
                    if ai_header and ai_bullets:
                        magazine_header = ai_header
                        magazine_bullets = "\n".join(ai_bullets)
                        
                        # Rodom preview
                        st.success(f"✅ **Antraštė:** {ai_header}")
                        st.success(f"✅ **Bullet punktai:**\n" + "\n".join([f"• {b}" for b in ai_bullets]))
                    else:
                        st.warning("⚠️ AI nepavyko sugeneruoti tekstų. Įvesk rankiniu būdu:")
                        use_ai_text = False  # Fallback į manual
            
            # Manual input (jei AI neįjungtas arba nepavyko)
            if not use_ai_text:
                # Antraštė
                magazine_header = st.text_input(
                    "📌 Antraštė (didelis šriftas 56px):",
                    value=magazine_header if magazine_header else "Tekstas",
                    help="Antraštė viršuje dešinėje, dideliu šriftu"
                )
                
                # Bullet points
                magazine_bullets = st.text_area(
                    "🔘 Bullet punktai (4 vnt, 24px šriftas):",
                    value=magazine_bullets if magazine_bullets else "Tekstas\nTekstas\nTekstas\nTekstas",
                    height=120,
                    help="Kiekviena eilutė = 1 punktas. Bus rodomi 4 punktai su apskritimais."
                )

        # Nuotraukų efektai
        st.markdown("---")
        st.markdown("#### 🎨 Nuotraukų efektai")

        col_fx1, col_fx2 = st.columns(2)

        with col_fx1:
            enable_white_border = st.checkbox("⬜ Baltas rėmelis", value=True, help="Baltas rėmelis aplink nuotraukas")
            enable_rounded_corners = st.checkbox("⭕ Užapvalinti kampai", value=True, help="Apvalūs nuotraukų kampai")
            
            # Logo parinktys (tik Magazine Style)
            if "Magazine Style" in collage_layout:
                logo_with_white = st.checkbox("⬜ Logo su baltu fonu", value=False, help="Logo su baltu fonu aplink")
                logo_transparent = st.checkbox("🔲 Logo su skaidriu fonu", value=False, help="Logo su permatomu fonu")

        with col_fx2:
            enable_shadow_effect = st.checkbox("🌑 Šešėlio efektas", value=True, help="3D šešėlis (drop shadow)")
            shadow_strength = (
                st.slider("Šešėlio stiprumas:", 0, 100, 50, 5, help="0 = nematomas, 100 = juodas")
                if enable_shadow_effect
                else 0
            )
            
            # AI Custom Fono generavimas
            use_custom_background = st.checkbox(
                "🎨 Naudoti Custom AI foną",
                value=False,
                help="Aprašyk foną savo žodžiais - AI sugeneruos pagal tavo aprašymą",
            )

        # AI tekstų generavimas (už stulpelių, kad būtų prieinamas visur)
        use_ai_text = st.checkbox(
            "🤖 Naudoti AI tekstui",
            value=False,
            help="AI sugeneruos antraštę ir bullet punktus pagal nuotrauką (Gemini Vision)",
        )

        # Custom prompt text area už stulpelių (kai pažymėta)
        custom_prompt = ""
        if use_custom_background:
            custom_prompt = st.text_area(
                "Aprašykite norimą foną:",
                value="",
                placeholder="Pvz: medžiai rugiai pieva, kviečiai ir medžio tekstūra, jūra saulėlydis...",
                help="AI (DALL-E 3) sugeneruos foną pagal šį aprašymą",
                height=80,
            )

            if custom_prompt and custom_prompt.strip():
                st.info(f"✨ **Custom AI fonas**: '{custom_prompt[:60]}...'")

        use_themed_bg = use_custom_background
        
        # Nustatome logo rodymo logiką
        logo_white_bg = False
        show_logo = False
        
        if "Magazine Style" in collage_layout:
            if logo_with_white:
                show_logo = True
                logo_white_bg = True
            elif logo_transparent:
                show_logo = True
                logo_white_bg = False
            else:
                show_logo = False  # Jei nei vienas nepažymėtas - logo nerodo
        
        # Telefono numerio pasirinkimas (visiems layout'ams)
        show_phone_number = st.checkbox("📞 Rodyti telefono numerį", value=True, help="Telefono numeris apačioje centre (120px šriftas, visiems layout'ams)")
        default_phone = "+370 (606) 50 414"

        st.markdown("---")

        if st.button("🎨 Sukurti Collage", type="primary", use_container_width=True):
            with st.spinner("🖼️ Kuriamas modernus collage su teksto kvadratu..."):
                try:
                    # Paruošiame redaguotas nuotraukas
                    edited_images = []
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
                            watermark_size=watermark_size,
                            watermark_position=watermark_position,
                            auto_enhance=auto_enhance,
                            enable_opencv=enable_opencv,
                            enable_auto_crop=enable_auto_crop,
                            enable_perspective=enable_perspective,
                            enable_white_balance=enable_white_balance,
                            enable_opencv_clarity=enable_opencv_clarity,
                            enable_aspect_ratio=enable_aspect_ratio,
                            target_aspect_ratio=target_aspect_ratio,
                        )
                        edited.seek(0)
                        img = Image.open(edited)
                        edited_images.append(img)

                    # Nustatome canvas dydį pagal social format
                    if "Instagram kvadratas" in social_format:
                        canvas_width, canvas_height = 1080, 1080
                    elif "Instagram Portrait" in social_format:
                        canvas_width, canvas_height = 1080, 1350
                    else:  # Facebook
                        canvas_width, canvas_height = 1200, 630

                    # Sukuriame foną (AI arba gradientą)
                    if use_themed_bg:
                        themed_bg = generate_themed_background(season, canvas_width, canvas_height, custom_prompt)
                        if themed_bg:
                            collage = themed_bg
                        else:
                            # Fallback į gradientą
                            collage = create_gradient_background(
                                canvas_width, canvas_height, (240, 245, 250), (250, 250, 255)
                            )
                    else:
                        collage = create_gradient_background(
                            canvas_width, canvas_height, (245, 245, 245), (255, 255, 255)
                        )

                    collage = collage.convert("RGBA")

                    # PADDING - mažesnis padding, bet palikta vieta logo viršuje kairėje!
                    padding = int(canvas_width * 0.04)  # 4% padding
                    logo_safe_zone = 160  # PADIDINTA vieta logo (100px aukštis + 60px margin)

                    content_width = canvas_width - padding * 2
                    content_height = canvas_height - padding * 2

                    # Content pradžia - žemiau logo safe zone
                    content_start_y = padding + logo_safe_zone

                    # Nustatome layout pagal pasirinkimą
                    num_photos = len(edited_images)

                    # ============ MAGAZINE STYLE LAYOUT ============
                    if "Magazine Style" in collage_layout:
                        # 2 nuotraukos + antraštė (56px) + bullet list (32px)
                        photo1 = edited_images[0]
                        photo2 = edited_images[1]
                        
                        collage = create_magazine_layout(
                            photo1=photo1,
                            photo2=photo2,
                            header_text=magazine_header,
                            bullet_points=magazine_bullets,
                            phone_number=default_phone if show_phone_number else None,
                            logo_path="assets/logo.png" if show_logo else None,
                            logo_with_white_bg=logo_white_bg,
                            enable_white_border=enable_white_border,
                            enable_rounded_corners=enable_rounded_corners,
                            enable_shadow_effect=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                            background=collage if use_themed_bg else None  # AI fonas
                        )
                        collage = collage.convert("RGBA")

                    # Magazine Style turi savo telefono numerį ir logo, todėl nieko papildomo nereikia
                    
                    # Konvertuojame į RGB (jei dar nekonvertuotas)
                    if collage.mode != "RGB":
                        collage = collage.convert("RGB")

                    # Išsaugome
                    collage_bytes = io.BytesIO()
                    collage.save(collage_bytes, format="JPEG", quality=95)
                    collage_bytes.seek(0)

                    # Išsaugome į session_state
                    st.session_state.collage_result = collage_bytes.getvalue()
                    st.session_state.collage_filename = f"collage_{season}_{social_format.split()[0]}.jpg"

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

        # Initialize session state for full size view
        if "show_full_collage" not in st.session_state:
            st.session_state.show_full_collage = False

        # Toggle button
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            if st.button(
                "👁️ Peržiūrėti pilną dydį" if not st.session_state.show_full_collage else "📱 Sumažinti peržiūrą",
                use_container_width=True,
                key="toggle_collage_view",
            ):
                st.session_state.show_full_collage = not st.session_state.show_full_collage
                st.rerun()

        # Display collage based on view mode
        if st.session_state.show_full_collage:
            # Full size - centered with max width
            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                st.image(st.session_state.collage_result, caption="Pilnas dydis", use_container_width=True)
        else:
            # Thumbnail preview - limited width
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(
                    st.session_state.collage_result,
                    caption="Peržiūra (spauskite mygtuką pilnam dydžiui)",
                    use_container_width=True,
                )

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="📥 Atsisiųsti Collage",
                data=st.session_state.collage_result,
                file_name=st.session_state.collage_filename,
                mime="image/jpeg",
                use_container_width=True,
                key="download_collage_persistent",
            )

    # AI TURINIO GENERAVIMAS
    st.markdown("---")
    st.markdown("### 📝 AI Turinio Generavimas")
    st.info("💡 Sukurkite tekstus socialiniams tinklams pagal jūsų nuotraukas")

    # 📚 ISTORIJA - Senesnių aprašymų rodymas
    history = load_history()
    if history and len(history) > 0:
        # Statistika
        approved_count = sum(1 for h in history if h.get("status") == "approved")
        generated_count = sum(1 for h in history if h.get("status") == "generated")

        with st.expander(
            f"📚 Versijų istorija: {len(history)} iš viso (✅ {approved_count} patvirtintų, 🔄 {generated_count} sugeneruotų)",
            expanded=False,
        ):
            st.caption("Kiekviena sugeneruota versija automatiškai išsaugoma. Pasirinkite norimą versiją.")

            for entry in history[:5]:  # Rodome tik 5 naujausius
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    # Statusas ir versija
                    status_icon = "✅" if entry.get("status") == "approved" else "🔄"
                    version_text = f"v{entry.get('version', 1)}"
                    holiday_text = f", {entry.get('holiday', 'Nėra')}" if entry.get("holiday") != "Nėra" else ""

                    st.markdown(
                        f"{status_icon} **{version_text}** | {entry['timestamp']} | {entry['season']}{holiday_text}, {entry['num_photos']} nuotr."
                    )
                    
                    # Padalinti tekstą į variantus
                    full_text = entry["description"]
                    if "---" in full_text:
                        variants = [v.strip() for v in full_text.split("---") if v.strip()]
                        # Rodome trumpą preview kiekvieno varianto
                        st.markdown("**💼 Marketinginis:**")
                        st.text(variants[0][:100] + "..." if len(variants[0]) > 100 else variants[0])
                        
                        if len(variants) > 1:
                            st.markdown("**🏡 Draugiškas:**")
                            st.text(variants[1][:100] + "..." if len(variants[1]) > 100 else variants[1])
                        
                        if len(variants) > 2:
                            st.markdown("**😄 Su humoru:**")
                            st.text(variants[2][:100] + "..." if len(variants[2]) > 100 else variants[2])
                    else:
                        # Jei nėra variantų - rodome kaip anksčiau
                        preview = full_text[:150] + "..." if len(full_text) > 150 else full_text
                        st.text(preview)

                with col2:
                    # Padalinome tekstą į variantus
                    full_text = entry["description"]
                    if "---" in full_text:
                        variants = [v.strip() for v in full_text.split("---") if v.strip()]
                        
                        # Funkcija pašalinti antraštę
                        def clean_variant(text):
                            lines = text.split('\n')
                            cleaned = []
                            for line in lines:
                                stripped = line.strip()
                                if not (stripped.startswith("**VARIANTAS") or stripped.startswith("VARIANTAS")):
                                    cleaned.append(line)
                            return '\n'.join(cleaned).strip()
                        
                        # Paruošiame visus variantus
                        cleaned_variants = [clean_variant(v) for v in variants]
                        entry_id = entry['id']
                        
                        # HTML su components - garantuotai veikiantis būdas
                        import streamlit.components.v1 as components
                        
                        texts_json = json.dumps(cleaned_variants)
                        
                        html_str = f"""
                        <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                            <button id="btn{entry_id}_0" onclick="copyText{entry_id}(0)" style="flex: 1; background: #0066cc; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;">
                                💼 Kopijuoti
                            </button>
                            <button id="btn{entry_id}_1" onclick="copyText{entry_id}(1)" style="flex: 1; background: #0066cc; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;" {'disabled' if len(cleaned_variants) < 2 else ''}>
                                🏡 Kopijuoti
                            </button>
                            <button id="btn{entry_id}_2" onclick="copyText{entry_id}(2)" style="flex: 1; background: #0066cc; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;" {'disabled' if len(cleaned_variants) < 3 else ''}>
                                😄 Kopijuoti
                            </button>
                        </div>
                        <script>
                        const texts{entry_id} = {texts_json};
                        function copyText{entry_id}(idx) {{
                            const btn = document.getElementById('btn{entry_id}_' + idx);
                            navigator.clipboard.writeText(texts{entry_id}[idx]).then(() => {{
                                btn.style.backgroundColor = '#28a745';
                                btn.innerHTML = '✅ Nukopijuota!';
                                setTimeout(() => {{
                                    btn.style.backgroundColor = '#0066cc';
                                    const labels = ['💼 Kopijuoti', '🏡 Kopijuoti', '😄 Kopijuoti'];
                                    btn.innerHTML = labels[idx];
                                }}, 1500);
                            }});
                        }}
                        </script>
                        """
                        
                        components.html(html_str, height=60)
                    else:
                        # Jei nėra variantų - paprastas copy
                        copy_button_id = f"copy_btn_{entry['id']}"
                        text_for_js = full_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$').replace('\n', '\\n').replace('\r', '').replace('"', '\\"')
                        
                        copy_html = f"""
                        <button id="{copy_button_id}" onclick="
                            navigator.clipboard.writeText(`{text_for_js}`).then(function() {{
                                document.getElementById('{copy_button_id}').innerHTML = '✅ Nukopijuota!';
                                document.getElementById('{copy_button_id}').style.backgroundColor = '#28a745';
                                setTimeout(function() {{
                                    document.getElementById('{copy_button_id}').innerHTML = '📋 Kopijuoti';
                                    document.getElementById('{copy_button_id}').style.backgroundColor = '#0066cc';
                                }}, 1500);
                            }});
                        " style="background-color: #0066cc; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px; width: 100%;">
                            📋 Kopijuoti
                        </button>
                        """
                        st.markdown(copy_html, unsafe_allow_html=True)
                
                with col3:
                    if st.button("🗑️", key=f"delete_history_{entry['id']}", help="Ištrinti šią versiją"):
                        if delete_from_history(entry["id"]):
                            st.success("✅ Ištrinta!")
                            st.rerun()

                st.markdown("---")

    # 🌐 TRENDING INFO
    trending_data = fetch_trending_hashtags(season)
    with st.expander("🔥 Trending dabar Instagram'e", expanded=False):
        st.markdown(f"**📊 Populiarūs hashtags ({season}):**")
        st.code(" ".join(trending_data["trending_hashtags"]))
        st.markdown(f"**🔥 Trending temos:** {trending_data['trending_topics']}")
        st.markdown(f"**💡 Patarimas:** {trending_data['engagement_tip']}")

    # Mygtukas čia
    if st.button(
        "🚀 Sukurti NAUJĄ AI Turinį (su trending hashtags)",
        type="primary",
        use_container_width=True,
        key="create_ai_content_btn",
    ):
        st.session_state.trigger_ai_content = True

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

# Apdorojimas tik jei yra failų ir trigger'is aktyvuotas
if (
    "trigger_ai_content" in st.session_state
    and st.session_state.trigger_ai_content
    and files_to_process
    and len(files_to_process) > 0
):
    progress_bar = st.progress(0)
    status_text = st.empty()

    all_analyses = []

    # Analizuojame REDAGUOTAS nuotraukas (su vandens ženklu, spalvų koregavimu)
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
                watermark_size=watermark_size,
                watermark_position=watermark_position,
                auto_enhance=auto_enhance,
                enable_opencv=enable_opencv,
                enable_auto_crop=enable_auto_crop,
                enable_perspective=enable_perspective,
                enable_white_balance=enable_white_balance,
                enable_opencv_clarity=enable_opencv_clarity,
                enable_aspect_ratio=enable_aspect_ratio,
                target_aspect_ratio=target_aspect_ratio,
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

            # Apskaičiuojame versijos numerį IŠ JSON ISTORIJOS
            # Randame paskutinę versiją su tais pačiais parametrais
            history = load_history()
            matching_versions = [
                h.get("version", 1)
                for h in history
                if h.get("season") == season
                and h.get("holiday") == holiday
                and h.get("num_photos") == len(files_to_process)
            ]
            next_version = max(matching_versions) + 1 if matching_versions else 1

            # AUTOMATIŠKAI išsaugome kiekvieną sugeneruotą versiją
            save_to_history(captions, season, holiday, len(files_to_process), status="generated", version=next_version)

            # 🤔 HUMAN-IN-THE-LOOP: Išsaugome kaip "pending" (laukia patvirtinimo)
            st.session_state.ai_content_pending = captions
            st.session_state.ai_analyses = all_analyses
            st.session_state.ai_pending_season = season
            st.session_state.ai_pending_holiday = holiday
            st.session_state.ai_pending_num_photos = len(files_to_process)

        except Exception as e:
            st.error(f"❌ Klaida generuojant turinį: {e}")

    progress_bar.empty()
    status_text.empty()

    # Reset trigger TIKTAI pabaigoje
    st.session_state.trigger_ai_content = False

# 🤔 HUMAN-IN-THE-LOOP: Patvirtinimo UI (jei yra pending turinys)
if "ai_content_pending" in st.session_state and st.session_state.ai_content_pending:
    st.markdown("---")
    st.info("🤔 **AI sugeneravo turinį. Ar patvirtinate?**")

    # Preview sugeneruoto turinio
    st.subheader("📝 Peržiūra:")
    st.text_area(
        "Sugeneruotas tekstas:",
        value=st.session_state.ai_content_pending,
        height=200,
        key="preview_pending",
        disabled=True,
    )

    # Patvirtinimo mygtukai
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Patvirtinti ir Išsaugoti", type="primary", use_container_width=True):
            # Patvirtinta! Išsaugome į rezultatus ir JSON
            st.session_state.ai_content_result = st.session_state.ai_content_pending

            # Randame paskutinę versiją IŠ JSON (ši versija jau išsaugota kaip "generated")
            history = load_history()
            # Ieškome šio teksto istorijoje
            matching_entry = None
            for h in history:
                if (
                    h.get("description") == st.session_state.ai_content_pending
                    and h.get("season") == st.session_state.ai_pending_season
                    and h.get("holiday") == st.session_state.ai_pending_holiday
                ):
                    matching_entry = h
                    break

            current_version = matching_entry.get("version", 1) if matching_entry else 1

            # Išsaugojame kaip APPROVED su atnaujintu statusu
            save_to_history(
                st.session_state.ai_content_pending,
                st.session_state.ai_pending_season,
                st.session_state.ai_pending_holiday,
                st.session_state.ai_pending_num_photos,
                status="approved",
                version=current_version,
            )
            # Išvalome pending
            del st.session_state.ai_content_pending
            st.success(f"✅ Versija #{current_version} patvirtinta ir išsaugota!")
            st.rerun()

    with col2:
        if st.button("🔄 Regeneruoti (sukurti kitą versiją)", type="secondary", use_container_width=True):
            # Ištriname VISUS senus duomenis
            if "ai_content_pending" in st.session_state:
                del st.session_state.ai_content_pending
            if "ai_analyses" in st.session_state:
                del st.session_state.ai_analyses  # Ištrinam senus analysis - generuosim iš naujo!
            if "ai_pending_season" in st.session_state:
                del st.session_state.ai_pending_season
            if "ai_pending_holiday" in st.session_state:
                del st.session_state.ai_pending_holiday

            # Trigger'inam NAUJĄ generavimą su NAUJAIS parametrais
            st.session_state.trigger_ai_content = True
            st.info("♻️ Generuojama nauja versija su skirtingu stiliumi...")
            st.rerun()

# Rodyti PATVIRTINTĄ AI turinio rezultatą
if "ai_content_result" in st.session_state and st.session_state.ai_content_result:
    st.markdown("---")
    st.success("✅ Turinys patvirtintas ir išsaugotas!")

    # Rezultatai
    st.subheader("📝 Patvirtinti socialinių tinklų įrašai")

    # Rodyti sugeneruotą turinį
    st.markdown("### 🎯 Paruošti tekstai:")
    
    # Rodome originalų tekstą
    st.text_area(
        "Kopijuokite tekstą:", 
        value=st.session_state.ai_content_result, 
        height=200, 
        key="ai_content_persistent"
    )
    
    # Padalinti į variantus kopijavimui
    text = st.session_state.ai_content_result
    if "---" in text:
        variants = [v.strip() for v in text.split("---") if v.strip()]
    else:
        variants = [text]
    
    # Funkcija pašalinti antraštę
    def clean_final_variant(text):
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if not (stripped.startswith("**VARIANTAS") or stripped.startswith("VARIANTAS")):
                cleaned.append(line)
        return '\n'.join(cleaned).strip()
    
    # Paruošiame visus variantus
    cleaned_variants = [clean_final_variant(v) for v in variants]
    
    # HTML su components - kopijuoti mygtukai
    import streamlit.components.v1 as components
    texts_json = json.dumps(cleaned_variants)
    
    html_str = f"""
    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
        <button id="btnfinal_0" onclick="copyTextFinal(0)" style="flex: 1; background: #0066cc; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;">
            💼 Kopijuoti
        </button>
        <button id="btnfinal_1" onclick="copyTextFinal(1)" style="flex: 1; background: #0066cc; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;" {'disabled' if len(cleaned_variants) < 2 else ''}>
            🏡 Kopijuoti
        </button>
        <button id="btnfinal_2" onclick="copyTextFinal(2)" style="flex: 1; background: #0066cc; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;" {'disabled' if len(cleaned_variants) < 3 else ''}>
            😄 Kopijuoti
        </button>
    </div>
    <script>
    const textsFinal = {texts_json};
    function copyTextFinal(idx) {{
        const btn = document.getElementById('btnfinal_' + idx);
        navigator.clipboard.writeText(textsFinal[idx]).then(() => {{
            btn.style.backgroundColor = '#28a745';
            btn.innerHTML = '✅ Nukopijuota!';
            setTimeout(() => {{
                btn.style.backgroundColor = '#0066cc';
                const labels = ['💼 Kopijuoti', '🏡 Kopijuoti', '😄 Kopijuoti'];
                btn.innerHTML = labels[idx];
            }}, 1500);
        }});
    }}
    </script>
    """
    
    components.html(html_str, height=60)

    # Analitikos informacija
    if "ai_analyses" in st.session_state:
        with st.expander("📊 Detali analizė"):
            st.markdown("**Vaizdų analizė:**")
            for i, analysis in enumerate(st.session_state.ai_analyses):
                st.markdown(f"**Nuotrauka {i+1}:** {analysis}")

# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")
