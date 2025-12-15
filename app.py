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


def add_glassmorphism_effect(img, blur_amount=10, opacity=0.3):
    """Prideda glassmorphism efektą (blurred background overlay)"""
    # Sukuriame blur kopiją
    blurred = img.filter(ImageFilter.GaussianBlur(blur_amount))

    # Sumažiname opacity
    if blurred.mode != "RGBA":
        blurred = blurred.convert("RGBA")

    # Pridedame baltą overlay su opacity
    overlay = Image.new("RGBA", blurred.size, (255, 255, 255, int(255 * opacity)))
    blurred = Image.alpha_composite(blurred, overlay)

    return blurred


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


def create_modern_landing_layout(product_image, text_content="", phone_number="+370 (606) 50 414", background=None, logo_path="assets/logo.png", text_columns=1, underline_first_word=False, style="Minimalist"):
    """
    Modernus landing page layout su:
    - Produkto nuotrauka kairėje
    - Tekstu dešinėje (su rounded corners)
    - Telefono numeriu apačioje centre
    - Teksto formatavimo opcijomis (stulpeliai, pabraukimas)
    - Baltu fonu (arba custom AI fonu)
    """
    # Canvas dydis
    canvas_width = 1920
    canvas_height = 1080
    
    # Spalvų paletė - šviesus stilius
    accent_color = (30, 64, 175)   # Tamsiai mėlyna
    text_dark = (30, 41, 59)       # Tamsiai pilka tekstui
    text_gray = (100, 116, 139)    # Šviesesnė pilka
    
    # Sukuriame canvas su baltu fonu arba custom fonu
    if background is not None:
        # Naudojame custom foną (AI generated)
        canvas = background.copy()
        if canvas.size != (canvas_width, canvas_height):
            canvas = canvas.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    else:
        # Baltas gradientas (subtilus)
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Subtilus vertikalus gradientas (balta → šviesi pilka)
        for y in range(canvas_height):
            ratio = y / canvas_height
            gray_value = int(255 - (ratio * 10))  # 255 → 245
            draw.line([(0, y), (canvas_width, y)], fill=(gray_value, gray_value, gray_value))
    
    # === KAIRĖ PUSĖ: FLOATING CARD SU PRODUKTO NUOTRAUKA ===
    left_width = int(canvas_width * 0.45)
    
    # Card parametrai
    card_padding = 40
    card_width = left_width - 160
    card_height = canvas_height - 200
    card_x = 80
    card_y = 100
    
    # Sukuriame RGBA card su rounded corners
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card)
    
    # Rounded rectangle (card background)
    corner_radius = 30
    # Naudojame rounded_rectangle jei PIL palaiko, kitaip - paprastas rectangle
    try:
        card_draw.rounded_rectangle(
            [0, 0, card_width, card_height],
            radius=corner_radius,
            fill=(255, 255, 255, 15)  # Labai permatoma balta (glassmorphism)
        )
    except:
        card_draw.rectangle([0, 0, card_width, card_height], fill=(255, 255, 255, 15))
    
    # Blur efektas (glassmorphism)
    card = card.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Produkto nuotrauka į card
    product_img = product_image.copy()
    if product_img.mode != "RGBA":
        product_img = product_img.convert("RGBA")
    
    # Resize su padding
    max_img_width = card_width - card_padding * 2
    max_img_height = card_height - card_padding * 2
    product_img.thumbnail((max_img_width, max_img_height), Image.Resampling.LANCZOS)
    
    # Rounded corners nuotraukai
    mask = Image.new("L", product_img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    try:
        mask_draw.rounded_rectangle([0, 0, product_img.width, product_img.height], radius=20, fill=255)
    except:
        mask_draw.rectangle([0, 0, product_img.width, product_img.height], fill=255)
    
    product_img.putalpha(mask)
    
    # Centruojame nuotrauką card'e
    img_x_in_card = (card_width - product_img.width) // 2
    img_y_in_card = (card_height - product_img.height) // 2
    card.paste(product_img, (img_x_in_card, img_y_in_card), product_img)
    
    # Pridedame DIDELĮ drop shadow po card
    shadow_size = 60
    shadow = Image.new("RGBA", (card_width + shadow_size * 2, card_height + shadow_size * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    try:
        shadow_draw.rounded_rectangle(
            [shadow_size, shadow_size, card_width + shadow_size, card_height + shadow_size],
            radius=corner_radius,
            fill=(0, 0, 0, 100)
        )
    except:
        shadow_draw.rectangle(
            [shadow_size, shadow_size, card_width + shadow_size, card_height + shadow_size],
            fill=(0, 0, 0, 100)
        )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=40))
    
    # Paste shadow ir card
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(shadow, (card_x - shadow_size, card_y - shadow_size), shadow)
    canvas_rgba.paste(card, (card_x, card_y), card)
    canvas = canvas_rgba.convert("RGB")
    
    # === DEŠINĖ PUSĖ: TEKSTO KVADRATAS ===
    right_x_start = left_width + 80
    content_width = canvas_width - right_x_start - 80
    
    # Atnaujintas draw po RGB konversijos
    draw = ImageDraw.Draw(canvas)
    
    # === TEKSTO KVADRATAS (KAIP KITUOSE LAYOUT'UOSE) ===
    text_box_width = content_width - 40
    text_box_height = 620
    text_box_x = right_x_start + 20
    text_box_y = 180
    
    # Naudojame tą pačią create_text_box funkciją kaip ir kituose layout'uose
    if text_content and text_content.strip():
        text_box = create_text_box(
            text_box_width,
            text_box_height,
            text_content,
            style=style,  # Naudojame pasirinktą stilį iš sidebar
            font_size=70,
            columns=text_columns,  # text_columns parametras iš funkcijos
            underline_first_word=underline_first_word
        )
        
        # Paste teksto kvadratą
        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.paste(text_box, (text_box_x, text_box_y), text_box)
        canvas = canvas_rgba.convert("RGB")
    
    # === TELEFONO NUMERIS APAČIOJE PER VIDURĮ (JEI ĮJUNGTAS) ===
    if phone_number:
        draw = ImageDraw.Draw(canvas)
        
        # Telefono numerio fontas - Times New Roman 50px - keletas fallback
        font_phone = None
        font_paths = [
            "C:/Windows/Fonts/timesbd.ttf",  # Times New Roman Bold
            "C:/Windows/Fonts/times.ttf",  # Times New Roman Regular
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",  # Linux
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",  # Linux DejaVu
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/System/Library/Fonts/Times New Roman.ttf",  # macOS
            "C:/Windows/Fonts/arial.ttf",  # Arial fallback
        ]
        
        for font_path in font_paths:
            try:
                font_phone = ImageFont.truetype(font_path, 50)
                break
            except:
                continue
        
        # Jei joks fontas nerastas
        if font_phone is None:
            try:
                font_phone = ImageFont.truetype("arial.ttf", 50)
            except:
                font_phone = ImageFont.load_default()
        
        # Apskaičiuojame telefono numerio dydį
        phone_bbox = draw.textbbox((0, 0), phone_number, font=font_phone)
        phone_width = phone_bbox[2] - phone_bbox[0]
        phone_height = phone_bbox[3] - phone_bbox[1]
        
        # Centruojame telefono numerį (dinaminis Y pagal aukštį)
        phone_x = (canvas_width - phone_width) // 2
        phone_y = canvas_height - phone_height - 80
        
        # Piešiame telefono numerį (be šešėlio)
        draw.text((phone_x, phone_y), phone_number, fill=(30, 41, 59), font=font_phone)
    
    return canvas


def add_collage_text_overlay(img, text, position="bottom", style="glassmorphism", font_size=70):
    """Prideda stilingą tekstą ant collage su įvairiais efektais"""
    if not text or text.strip() == "":
        return img

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Sukuriame overlay sluoksnį
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Fontų paieška (prioritetas: Bold fontai)
    font = None
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
        "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
        "C:/Windows/Fonts/ariblk.ttf",  # Arial Black
        "C:/Windows/Fonts/arial.ttf",  # Arial Regular
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

    # Pozicijos nustatymas
    if position == "Apačioje":
        y = img.height - text_height - 120
    elif position == "Viršuje":
        y = 100
    else:  # Centre
        y = (img.height - text_height) // 2

    x = (img.width - text_width) // 2

    # STILIŲ IMPLEMENTACIJOS
    if "Glassmorphism" in style:
        # Glassmorphism: blur fonas su skaidrumu
        padding = 60
        bg_rect = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]

        # Sukuriame blur foną
        bg_blur = Image.new("RGBA", img.size, (255, 255, 255, 0))
        bg_draw = ImageDraw.Draw(bg_blur)
        bg_draw.rounded_rectangle(bg_rect, radius=30, fill=(255, 255, 255, 200))
        bg_blur = bg_blur.filter(ImageFilter.GaussianBlur(5))

        # Pridedame šešėlį
        shadow = Image.new("RGBA", img.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [bg_rect[0] + 5, bg_rect[1] + 5, bg_rect[2] + 5, bg_rect[3] + 5], radius=30, fill=(0, 0, 0, 60)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))

        img = Image.alpha_composite(img, shadow)
        img = Image.alpha_composite(img, bg_blur)

        # Tekstas su šešėliu
        for offset in [(2, 2), (1, 1), (3, 3)]:
            draw.text((x + offset[0], y + offset[1]), text, fill=(0, 0, 0, 80), font=font)
        draw.text((x, y), text, fill=(30, 30, 30, 255), font=font)

    elif "Neo-Brutalism" in style:
        # Neo-Brutalism: ryškus rėmelis su storais kraštais
        padding = 50
        border_width = 8
        bg_rect = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]

        # "3D" šešėlis (offset)
        shadow_offset = 10
        draw.rectangle(
            [
                bg_rect[0] + shadow_offset,
                bg_rect[1] + shadow_offset,
                bg_rect[2] + shadow_offset,
                bg_rect[3] + shadow_offset,
            ],
            fill=(0, 0, 0, 255),
        )

        # Ryškus geltonas fonas
        draw.rectangle(bg_rect, fill=(255, 220, 50, 255))

        # Storas juodas rėmelis
        for i in range(border_width):
            draw.rectangle(
                [bg_rect[0] + i, bg_rect[1] + i, bg_rect[2] - i, bg_rect[3] - i], outline=(0, 0, 0, 255), width=2
            )

        # Juodas tekstas be šešėlio (clean)
        draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)

    elif "Minimalist" in style:
        # Minimalist: šviesus fonas su subtiliu šešėliu
        padding = 50
        bg_rect = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]

        # Subtilus šešėlis
        shadow = Image.new("RGBA", img.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([bg_rect[0] + 3, bg_rect[1] + 3, bg_rect[2] + 3, bg_rect[3] + 3], fill=(0, 0, 0, 40))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))

        img = Image.alpha_composite(img, shadow)

        # Baltas fonas
        draw.rectangle(bg_rect, fill=(255, 255, 255, 245))

        # Tamsus tekstas su labai subtiliu šešėliu
        draw.text((x + 1, y + 1), text, fill=(0, 0, 0, 60), font=font)
        draw.text((x, y), text, fill=(40, 40, 40, 255), font=font)

    return Image.alpha_composite(img, overlay)


def wrap_text(text, font, max_width):
    """
    Automatiškai lūžo tekstą į eilutes pagal plotį.
    Palaiko \n (Enter) simbolius - naujos eilutės išlaikomos.
    """
    # Pirmiausia padalijame pagal \n (vartotojo įvestas Enter)
    manual_lines = text.split('\n')
    wrapped_lines = []
    
    # Kiekvieną eilutę wrap'iname pagal plotį
    for manual_line in manual_lines:
        if not manual_line.strip():  # Tuščia eilutė
            wrapped_lines.append("")
            continue
            
        words = manual_line.split()
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    wrapped_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Žodis per ilgas - pridedame tokį kokis yra
                    wrapped_lines.append(word)
        
        if current_line:
            wrapped_lines.append(" ".join(current_line))
    
    return wrapped_lines


def create_text_box(width, height, text, style="glassmorphism", font_size=60, bg_color=(255, 255, 255), columns=1, underline_first_word=False):
    """
    Sukuria teksto kvadratą kaip atskirą paveikslėlį (ne overlay!)
    
    Parametrai:
    - columns: 1 (įprastas) arba 2 (stulpelinis layout kaip laikraštyje)
    - underline_first_word: True pabrauks pirmą žodį
    """
    
    # SVARBU: Išsaugome font_size į lokalų kintamąjį
    actual_font_size = int(font_size)  # Užtikrina kad tai skaičius

    # Sukuriame RGBA paveikslėlį
    text_box = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_box)

    # Fontų paieška - Times New Roman (Windows) + Linux backup
    font = None
    font_paths = [
        # Windows fonts
        "C:/Windows/Fonts/timesbd.ttf",  # Times New Roman Bold
        "C:/Windows/Fonts/timesbi.ttf",  # Times New Roman Bold Italic
        "C:/Windows/Fonts/times.ttf",  # Times New Roman Regular
        "C:/Windows/Fonts/timesi.ttf",  # Times New Roman Italic
        "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
        "C:/Windows/Fonts/arial.ttf",  # Arial Regular
        # Linux fonts (Streamlit Cloud)
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, actual_font_size)
            break
        except Exception as e:
            continue

    if font is None:
        # Fallback į default (bitmap font - fiksuotas dydis)
        font = ImageFont.load_default()

    # STILIŲ IMPLEMENTACIJOS
    if "Glassmorphism" in style:
        # Šviesus, pusiau skaidrus fonas (glassmorphism efektas)
        draw.rectangle([0, 0, width, height], fill=(255, 255, 255, 230))

        # Automatinis teksto lūžimas
        if columns == 2:
            # STULPELINIS LAYOUT
            column_gap = 30
            column_width = (width - 60 - column_gap) // 2
            max_text_width = column_width
        else:
            # ĮPRASTAS LAYOUT
            max_text_width = width - 40  # 20px padding
        
        lines = wrap_text(text, font, max_text_width)

        if columns == 2:
            # 2 STULPELIAI
            mid_point = (len(lines) + 1) // 2
            left_lines = lines[:mid_point]
            right_lines = lines[mid_point:]
            
            line_height = actual_font_size + 20
            y = 30
            
            # Kairys stulpelis
            for i, line in enumerate(left_lines):
                x = 30
                
                # Patikriname ar tai pirma eilutė ir ar reikia pabraukti pirmą žodį
                if i == 0 and underline_first_word and line.strip():
                    words = line.split(maxsplit=1)
                    first_word = words[0]
                    rest = " " + words[1] if len(words) > 1 else ""
                    
                    # Pirmą žodį su pabraukimu
                    bbox_first = draw.textbbox((0, 0), first_word, font=font)
                    first_width = bbox_first[2] - bbox_first[0]
                    
                    # Šešėlis
                    draw.text((x + 2, y + 2), first_word, fill=(0, 0, 0, 80), font=font)
                    # Tekstas
                    draw.text((x, y), first_word, fill=(40, 40, 40, 255), font=font)
                    # Pabraukimas
                    underline_y = y + bbox_first[3] + 2
                    draw.line([(x, underline_y), (x + first_width, underline_y)], fill=(40, 40, 40, 255), width=2)
                    
                    # Likęs tekstas
                    if rest:
                        draw.text((x + first_width + 2, y + 2), rest, fill=(0, 0, 0, 80), font=font)
                        draw.text((x + first_width, y), rest, fill=(40, 40, 40, 255), font=font)
                else:
                    draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 80), font=font)
                    draw.text((x, y), line, fill=(40, 40, 40, 255), font=font)
                
                y += line_height
            
            # Dešinys stulpelis
            y = 30
            x_right = 30 + column_width + column_gap
            for line in right_lines:
                draw.text((x_right + 2, y + 2), line, fill=(0, 0, 0, 80), font=font)
                draw.text((x_right, y), line, fill=(40, 40, 40, 255), font=font)
                y += line_height
        else:
            # 1 STULPELIS (CENTRUOTAS)
            total_height = len(lines) * (actual_font_size + 20)
            y_start = (height - total_height) // 2

            for i, line in enumerate(lines):
                # Patikriname ar tai pirma eilutė ir ar reikia pabraukti pirmą žodį
                if i == 0 and underline_first_word and line.strip():
                    words = line.split(maxsplit=1)
                    first_word = words[0]
                    rest = " " + words[1] if len(words) > 1 else ""
                    
                    # Skaičiuojame centravimą visai eilutei
                    bbox_full = draw.textbbox((0, 0), line, font=font)
                    full_width = bbox_full[2] - bbox_full[0]
                    x_start = (width - full_width) // 2
                    y = y_start + i * (actual_font_size + 20)
                    
                    # Pirmą žodį su pabraukimu
                    bbox_first = draw.textbbox((0, 0), first_word, font=font)
                    first_width = bbox_first[2] - bbox_first[0]
                    
                    # Šešėlis
                    draw.text((x_start + 2, y + 2), first_word, fill=(0, 0, 0, 80), font=font)
                    # Tekstas
                    draw.text((x_start, y), first_word, fill=(40, 40, 40, 255), font=font)
                    # Pabraukimas
                    underline_y = y + bbox_first[3] + 2
                    draw.line([(x_start, underline_y), (x_start + first_width, underline_y)], fill=(40, 40, 40, 255), width=2)
                    
                    # Likęs tekstas
                    if rest:
                        draw.text((x_start + first_width + 2, y + 2), rest, fill=(0, 0, 0, 80), font=font)
                        draw.text((x_start + first_width, y), rest, fill=(40, 40, 40, 255), font=font)
                else:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (width - text_width) // 2
                    y = y_start + i * (actual_font_size + 20)

                    # Šešėlis
                    draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 80), font=font)
                    # Tekstas
                    draw.text((x, y), line, fill=(40, 40, 40, 255), font=font)

    elif "Neo-Brutalism" in style:
        # Ryškus geltonas fonas su juodu rėmeliu
        border_width = 8

        # Juodas šešėlis (3D efektas)
        draw.rectangle([10, 10, width, height], fill=(0, 0, 0, 255))

        # Geltonas fonas
        draw.rectangle([0, 0, width - 10, height - 10], fill=(255, 220, 50, 255))

        # Storas juodas rėmelis
        for i in range(border_width):
            draw.rectangle([i, i, width - 10 - i, height - 10 - i], outline=(0, 0, 0, 255), width=2)

        # Automatinis teksto lūžimas
        max_text_width = width - 50  # Accounting for borders and padding
        lines = wrap_text(text, font, max_text_width)
        total_height = len(lines) * (actual_font_size + 20)
        y_start = (height - total_height) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = y_start + i * (actual_font_size + 20)
            draw.text((x, y), line, fill=(0, 0, 0, 255), font=font)

    elif "Minimalist" in style:
        # Švarus baltas fonas
        draw.rectangle([0, 0, width, height], fill=(255, 255, 255, 250))

        # Automatinis teksto lūžimas
        if columns == 2:
            # STULPELINIS LAYOUT (kaip laikraštyje)
            column_gap = 30  # Tarpas tarp stulpelių
            column_width = (width - 60 - column_gap) // 2  # 30px padding iš kiekvienos pusės + gap
            max_text_width = column_width
        else:
            # ĮPRASTAS LAYOUT
            max_text_width = width - 40  # 20px padding
        
        lines = wrap_text(text, font, max_text_width)
        
        if columns == 2:
            # Padalijame eilutes į 2 stulpelius
            mid_point = (len(lines) + 1) // 2
            left_lines = lines[:mid_point]
            right_lines = lines[mid_point:]
            
            # Kairys stulpelis
            line_height = actual_font_size + 20
            y = 30  # Top padding
            
            for i, line in enumerate(left_lines):
                # Patikriname ar tai pirma eilutė ir ar reikia pabraukti pirmą žodį
                if i == 0 and underline_first_word and line.strip():
                    words = line.split(maxsplit=1)
                    first_word = words[0]
                    rest = " " + words[1] if len(words) > 1 else ""
                    
                    # Pirmą žodį su pabraukimu
                    bbox_first = draw.textbbox((0, 0), first_word, font=font)
                    first_width = bbox_first[2] - bbox_first[0]
                    x = 30
                    
                    # Šešėlis
                    draw.text((x + 1, y + 1), first_word, fill=(0, 0, 0, 50), font=font)
                    # Tekstas
                    draw.text((x, y), first_word, fill=(50, 50, 50, 255), font=font)
                    # Pabraukimas
                    underline_y = y + bbox_first[3] + 2
                    draw.line([(x, underline_y), (x + first_width, underline_y)], fill=(50, 50, 50, 255), width=2)
                    
                    # Likęs tekstas
                    if rest:
                        draw.text((x + first_width, y), rest, fill=(50, 50, 50, 255), font=font)
                else:
                    x = 30
                    # Subtilus šešėlis
                    draw.text((x + 1, y + 1), line, fill=(0, 0, 0, 50), font=font)
                    # Tekstas
                    draw.text((x, y), line, fill=(50, 50, 50, 255), font=font)
                
                y += line_height
            
            # Dešinys stulpelis
            y = 30  # Top padding
            x_right = 30 + column_width + column_gap
            
            for line in right_lines:
                # Subtilus šešėlis
                draw.text((x_right + 1, y + 1), line, fill=(0, 0, 0, 50), font=font)
                # Tekstas
                draw.text((x_right, y), line, fill=(50, 50, 50, 255), font=font)
                y += line_height
        else:
            # ĮPRASTAS CENTRUOTAS LAYOUT
            total_height = len(lines) * (actual_font_size + 20)
            y_start = (height - total_height) // 2

            for i, line in enumerate(lines):
                # Patikriname ar tai pirma eilutė ir ar reikia pabraukti pirmą žodį
                if i == 0 and underline_first_word and line.strip():
                    words = line.split(maxsplit=1)
                    first_word = words[0]
                    rest = " " + words[1] if len(words) > 1 else ""
                    
                    # Skaičiuojame centravimą visai eilutei
                    bbox_full = draw.textbbox((0, 0), line, font=font)
                    full_width = bbox_full[2] - bbox_full[0]
                    x_start = (width - full_width) // 2
                    y = y_start + i * (actual_font_size + 20)
                    
                    # Pirmą žodį su pabraukimu
                    bbox_first = draw.textbbox((0, 0), first_word, font=font)
                    first_width = bbox_first[2] - bbox_first[0]
                    
                    # Šešėlis
                    draw.text((x_start + 1, y + 1), first_word, fill=(0, 0, 0, 50), font=font)
                    # Tekstas
                    draw.text((x_start, y), first_word, fill=(50, 50, 50, 255), font=font)
                    # Pabraukimas
                    underline_y = y + bbox_first[3] + 2
                    draw.line([(x_start, underline_y), (x_start + first_width, underline_y)], fill=(50, 50, 50, 255), width=2)
                    
                    # Likęs tekstas
                    if rest:
                        draw.text((x_start + first_width, y), rest, fill=(50, 50, 50, 255), font=font)
                else:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x = (width - text_width) // 2
                    y = y_start + i * (actual_font_size + 20)

                    # Subtilus šešėlis
                    draw.text((x + 1, y + 1), line, fill=(0, 0, 0, 50), font=font)
                    # Tekstas
                    draw.text((x, y), line, fill=(50, 50, 50, 255), font=font)

    return text_box


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


def create_modern_landing_html(product_image, text_content="", phone_number="+370 (606) 50 414", logo_path="assets/logo.png", style="Minimalist"):
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
        # NAUJAS: Social media formato pasirinkimas
        col_format, col_style = st.columns([1, 1])

        with col_format:
            social_format = st.selectbox(
                "📱 Socialinio tinklo formatas:",
                ["Instagram kvadratas (1080x1080)", "Instagram Portrait (1080x1350)", "Facebook Post (1200x630)"],
                help="Pasirinkite socialinio tinklo formatą",
            )

        with col_style:
            collage_style = st.selectbox(
                "🎨 Dizaino stilius:",
                [
                    "💎 Glassmorphism - Modernus, skaidrus",
                    "🎯 Neo-Brutalism - Ryškus, drąsus",
                    "✨ Minimalist - Švarus, elegantiškas",
                ],
                help="Bendras collage dizaino stilius",
            )

        # NAUJAS: Išdėstymas su teksto kvadratu
        st.markdown("---")
        st.markdown("#### 📐 Išdėstymas (nuotraukos + tekstas)")

        num_photos = len(files_to_process)

        if num_photos == 1:
            layout_options = [
                "🎯 Modern Landing (produktas + info)",
            ]
        elif num_photos == 2:
            layout_options = [
                "🎯 Modern Landing (produktas + info)",
                "📰 Magazine Style (2 nuotraukos + bullet list)",
                "Grid 2x2 (2 nuotraukos + 2 teksto kvadratai)",
                "Horizontal (2 nuotraukos + 1 tekstas viduryje)",
                "Asymmetric (1 didelė + 1 maža + tekstas)",
                "⚡ Dynamic (pasvirusios nuotraukos + tekstas)",
            ]
        elif num_photos == 3:
            layout_options = [
                "🎯 Modern Landing (produktas + info)",
                "Grid 2x2 (3 nuotraukos + 1 teksto kvadratas)",
                "Magazine (3 nuotraukos + teksto zona)",
                "Asymmetric (1 didelė + 2 mažos + tekstas)",
            ]
        else:  # 4 ar daugiau
            layout_options = [
                "🎯 Modern Landing (produktas + info)",
                "Grid 2x2 (4 nuotraukos be teksto)",
                "Grid 3x2 (4 nuotraukos + 2 teksto kvadratai)",
                "Mosaic (4 nuotraukos skirtingų dydžių + tekstas)",
            ]

        collage_layout = st.selectbox(
            "Pasirinkite išdėstymą:", layout_options, help="Layout su integruotu teksto kvadratu (ne overlay!)"
        )

        # NAUJAS: Teksto turinys (TIKTAI jei NE Magazine Style)
        if "Magazine Style" not in collage_layout:
            st.markdown("---")
            st.markdown("#### ✍️ Teksto kvadrato turinys")
            
            # Teksto formatavimo opcijos
            col_fmt1, col_fmt2 = st.columns(2)
            with col_fmt1:
                text_columns = st.radio("📰 Layout:", ["1 stulpelis", "2 stulpeliai (laikraštinis)"], index=0, help="Tekstas vienu stulpeliu arba dviem kaip laikraštyje")
            with col_fmt2:
                underline_first = st.checkbox("✏️ Pabraukti pirmą žodį", value=False, help="Pabraukia pirmą žodį tekste (akcentas)")
        else:
            # Default values kai Magazine Style
            text_columns = "1 stulpelis"
            underline_first = False
        
        # 🎨 HTML rendering pasirinkimas (tik Modern Landing)
        use_html_rendering = False
        if collage_layout == "🎯 Modern Landing (produktas + info)":
            use_html_rendering = st.checkbox(
                "🎨 Fancy HTML dizainas (eksperimentinis)", 
                value=False,
                help="Naudoja HTML/CSS rendering'ą - modernesnis dizainas su gradientais ir fancy efektais! Gali užtrukti ~5-10s"
            )
        
        # 📰 Magazine Style nustatymai
        magazine_header = ""
        magazine_bullets = ""
        logo_white_bg = False
        
        if "Magazine Style" in collage_layout:
            st.markdown("---")
            st.markdown("#### 📰 Magazine Style nustatymai")
            
            # Antraštė
            magazine_header = st.text_input(
                "📌 Antraštė (didelis šriftas 56px):",
                value="Tekstas",
                help="Antraštė viršuje dešinėje, dideliu šriftu"
            )
            
            # Bullet points
            magazine_bullets = st.text_area(
                "🔘 Bullet punktai (4 vnt, 24px šriftas):",
                value="Tekstas\nTekstas\nTekstas\nTekstas",
                height=120,
                help="Kiekviena eilutė = 1 punktas. Bus rodomi 4 punktai su apskritimais."
            )
        
        # Konvertuojame UI pasirinkimą į skaičių
        text_columns_num = 2 if "2 stulpeliai" in text_columns else 1

        # Jei 2 nuotraukos Grid 2x2 - rodyti 2 tekstus
        if len(files_to_process) == 2 and collage_layout == "Grid 2x2 (2 nuotraukos + 2 teksto kvadratai)":
            st.info("💡 2 nuotraukos → 2 skirtingi tekstai")

            col1, col2 = st.columns(2)

            with col1:
                text_content = st.text_area(
                    "Tekstas kvadrate 1:",
                    value=f"{season} kolekcija 2025 🌿",
                    height=80,
                    key="text_box_1",
                    help="Pirmas teksto kvadratas",
                )

            with col2:
                text_content_2 = st.text_area(
                    "Tekstas kvadrate 2:",
                    value=f"Naujiena! {season} stilius 🎨",
                    height=80,
                    key="text_box_2",
                    help="Antras teksto kvadratas",
                )

            # 2 ATSKIRI SLIDER'IAI KIEKVIENAM TEKSTUI
            st.markdown("##### 🔤 Šriftų dydžiai")
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                text_font_size = st.slider(
                    "Šrifto dydis tekstui 1:", 30, 120, 60, 10, key="font_size_1", help="Teksto dydis pirmame kvadrate"
                )

            with col_s2:
                text_font_size_2 = st.slider(
                    "Šrifto dydis tekstui 2:", 30, 120, 60, 10, key="font_size_2", help="Teksto dydis antrame kvadrate"
                )
        else:
            # Vienas tekstas visiem kitiems layoutams (NE Magazine Style)
            if "Magazine Style" not in collage_layout:
                col1, col2 = st.columns([2, 1])

                with col1:
                    text_content = st.text_area(
                        "Tekstas teksto kvadrate:",
                        value=f"{season} kolekcija 2025 🌿",
                        height=100,
                        help="Šis tekstas bus atskirame kvadrate collage (ne overlay!)",
                    )

                with col2:
                    text_font_size = st.slider("Šrifto dydis:", 30, 120, 60, 10, help="Teksto dydis teksto kvadrate")
            else:
                # Magazine Style - default values
                text_content = ""
                text_font_size = 60

            text_content_2 = None  # Nėra antro teksto
            text_font_size_2 = text_font_size  # Naudojame tą patį dydį

        # NAUJAS: Nuotraukų efektai
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

                    # ============ MODERN LANDING LAYOUT ============
                    if "Modern Landing" in collage_layout:
                        # Naudojame pirmą nuotrauką kaip produkto nuotrauką
                        product_img = edited_images[0]
                        
                        if use_html_rendering:
                            # HTML versija - FANCY!
                            with st.spinner("🎨 HTML rendering... Gali užtrukti ~5-10s"):
                                collage = create_modern_landing_html(
                                    product_img,
                                    text_content=text_content,
                                    phone_number=default_phone if show_phone_number else None,
                                    logo_path="assets/logo.png",
                                    style=collage_style
                                )
                        else:
                            # PIL versija - klasikinė
                            collage = create_modern_landing_layout(
                                product_img, 
                                text_content=text_content,
                                phone_number=default_phone if show_phone_number else None,
                                background=collage if use_themed_bg else None,  # AI fonas jei pasirinktas
                                logo_path="assets/logo.png",
                                text_columns=text_columns_num,
                                underline_first_word=underline_first,
                                style=collage_style  # Perduodame pasirinktą stilių
                            )
                        
                        collage = collage.convert("RGBA")
                    
                    # ============ MAGAZINE STYLE LAYOUT ============
                    elif "Magazine Style" in collage_layout:
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

                    # ============ GRID 2x2 LAYOUTS ============
                    elif "Grid 2x2" in collage_layout:
                        cell_size = content_width // 2
                        gap = 20

                        # Apskaičiuojame efektų įtaką dydžiui
                        border_offset = 12 if enable_white_border else 0
                        # Šešėlio offset visada 15px (nepriklausomai nuo stiprumo)
                        shadow_offset = 15 if enable_shadow_effect else 0
                        # SVARBU: Nuotrauka PRIEŠ efektus turi būti mažesnė!
                        target_size = cell_size - gap - (border_offset + shadow_offset) * 2

                        positions = [
                            (padding, padding),  # Top-left
                            (padding + cell_size + gap, padding),  # Top-right
                            (padding, padding + cell_size + gap),  # Bottom-left
                            (padding + cell_size + gap, padding + cell_size + gap),  # Bottom-right
                        ]

                        for idx in range(4):
                            # Apskaičiuojame ląstelės centrą
                            row = idx // 2  # 0 arba 1
                            col = idx % 2  # 0 arba 1
                            cell_x = padding + col * (cell_size + gap)
                            cell_y = padding + row * (cell_size + gap)

                            if idx < num_photos:
                                # Nuotrauka - automatinis crop
                                original_img = edited_images[idx]

                                # Apskaičiuojame crop (centruota)
                                aspect = original_img.width / original_img.height

                                if aspect > 1:  # Plati
                                    new_height = target_size
                                    new_width = int(target_size * aspect)
                                else:  # Aukšta
                                    new_width = target_size
                                    new_height = int(target_size / aspect)

                                # Resize ir crop
                                img_resized = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                left = (new_width - target_size) // 2
                                top = (new_height - target_size) // 2
                                img_cropped = img_resized.crop((left, top, left + target_size, top + target_size))

                                # Pridedame pasirinktus efektus
                                img_with_effects = add_photo_effects(
                                    img_cropped,
                                    enable_border=enable_white_border,
                                    border_width=12,
                                    enable_rounded=enable_rounded_corners,
                                    corner_radius=25,
                                    enable_shadow=enable_shadow_effect,
                                    shadow_strength=shadow_strength,
                                )

                                # Centruojame nuotrauką ląstelėje
                                paste_x = cell_x + (cell_size - img_with_effects.width) // 2
                                paste_y = cell_y + (cell_size - img_with_effects.height) // 2

                                collage.paste(img_with_effects, (paste_x, paste_y), img_with_effects)
                            else:
                                # Teksto kvadratas
                                # Jei 2 nuotraukos → naudojame text_content_2 ir text_font_size_2 antram tekstui
                                text_to_use = text_content
                                font_size_to_use = text_font_size

                                if num_photos == 2 and idx == 3 and text_content_2:
                                    text_to_use = text_content_2
                                    # Naudojame antrą font_size jei jis egzistuoja
                                    if "text_font_size_2" in locals():
                                        font_size_to_use = text_font_size_2

                                text_box = create_text_box(
                                    target_size,
                                    target_size,
                                    text_to_use,
                                    style=collage_style,
                                    font_size=font_size_to_use,
                                    columns=text_columns_num,
                                    underline_first_word=underline_first
                                )
                                # Pridedame tuos pačius efektus tekstui
                                text_with_effects = add_photo_effects(
                                    text_box,
                                    enable_border=enable_white_border,
                                    border_width=12,
                                    enable_rounded=enable_rounded_corners,
                                    corner_radius=25,
                                    enable_shadow=enable_shadow_effect,
                                    shadow_strength=shadow_strength,
                                )

                                # Centruojame tekstą ląstelėje
                                paste_x = cell_x + (cell_size - text_with_effects.width) // 2
                                paste_y = cell_y + (cell_size - text_with_effects.height) // 2

                                collage.paste(text_with_effects, (paste_x, paste_y), text_with_effects)

                    # ============ HORIZONTAL LAYOUT (2 nuotraukos + tekstas) ============
                    elif "Horizontal" in collage_layout and num_photos == 2:
                        cell_width = content_width // 3
                        gap = 20

                        # Nuotrauka 1 (kairėje)
                        img1 = edited_images[0].resize((cell_width - gap, content_height), Image.Resampling.LANCZOS)
                        if img1.mode != "RGBA":
                            img1 = img1.convert("RGBA")
                        styled1 = add_photo_effects(
                            img1,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        collage.paste(styled1, (padding, padding), styled1)

                        # Teksto kvadratas (viduryje)
                        text_box = create_text_box(
                            cell_width - gap,
                            content_height,
                            text_content,
                            style=collage_style,
                            font_size=text_font_size,
                            columns=text_columns_num,
                            underline_first_word=underline_first
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        collage.paste(shadowed_text, (padding + cell_width + gap, padding), shadowed_text)

                        # Nuotrauka 2 (dešinėje)
                        img2 = edited_images[1].resize((cell_width - gap, content_height), Image.Resampling.LANCZOS)
                        if img2.mode != "RGBA":
                            img2 = img2.convert("RGBA")
                        styled2 = add_photo_effects(
                            img2,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        collage.paste(styled2, (padding + cell_width * 2 + gap * 2, padding), styled2)

                    # ============ ASYMMETRIC LAYOUT ============
                    elif "Asymmetric" in collage_layout:
                        if num_photos == 2:
                            # 1 didelė kairėje + 1 maža + tekstas dešinėje
                            big_width = int(content_width * 0.6)
                            small_width = content_width - big_width - 20
                            half_height = content_height // 2
                            gap = 20

                            # Didelė nuotrauka (kairėje)
                            img_big = edited_images[0].resize((big_width, content_height), Image.Resampling.LANCZOS)
                            if img_big.mode != "RGBA":
                                img_big = img_big.convert("RGBA")
                            styled_big = add_photo_effects(
                                img_big,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength,
                            )
                            collage.paste(styled_big, (padding, padding), styled_big)

                            # Maža nuotrauka (viršuje dešinėje)
                            img_small = edited_images[1].resize(
                                (small_width, half_height - gap), Image.Resampling.LANCZOS
                            )
                            if img_small.mode != "RGBA":
                                img_small = img_small.convert("RGBA")
                            styled_small = add_photo_effects(
                                img_small,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength,
                            )
                            collage.paste(styled_small, (padding + big_width + gap, padding), styled_small)

                            # Teksto kvadratas (apačioje dešinėje)
                            text_box = create_text_box(
                                small_width,
                                half_height - gap,
                                text_content,
                                style=collage_style,
                                font_size=text_font_size,
                                columns=text_columns_num,
                                underline_first_word=underline_first
                            )
                            shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                            collage.paste(
                                shadowed_text, (padding + big_width + gap, padding + half_height + gap), shadowed_text
                            )

                        elif num_photos == 3:
                            # 1 didelė + 2 mažos + tekstas
                            big_width = int(content_width * 0.65)
                            small_width = content_width - big_width - 20
                            third_height = content_height // 3
                            gap = 20

                            # Didelė nuotrauka (kairėje)
                            img_big = edited_images[0].resize((big_width, content_height), Image.Resampling.LANCZOS)
                            if img_big.mode != "RGBA":
                                img_big = img_big.convert("RGBA")
                            styled_big = add_photo_effects(
                                img_big,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength,
                            )
                            collage.paste(styled_big, (padding, padding), styled_big)

                            # 2 mažos nuotraukos + tekstas dešinėje
                            for i in range(2):
                                img_small = edited_images[i + 1].resize(
                                    (small_width, third_height - gap), Image.Resampling.LANCZOS
                                )
                                if img_small.mode != "RGBA":
                                    img_small = img_small.convert("RGBA")
                                styled_small = add_photo_effects(
                                    img_small,
                                    enable_border=enable_white_border,
                                    enable_rounded=enable_rounded_corners,
                                    enable_shadow=enable_shadow_effect,
                                    shadow_strength=shadow_strength,
                                )
                                y_pos = padding + i * (third_height + gap)
                                collage.paste(styled_small, (padding + big_width + gap, y_pos), styled_small)

                            # Teksto kvadratas apačioje
                            text_box = create_text_box(
                                small_width,
                                third_height - gap,
                                text_content,
                                style=collage_style,
                                font_size=text_font_size,
                                columns=text_columns_num,
                                underline_first_word=underline_first
                            )
                            shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                            collage.paste(
                                shadowed_text,
                                (padding + big_width + gap, padding + third_height * 2 + gap * 2),
                                shadowed_text,
                            )

                    # ============ MAGAZINE LAYOUT ============
                    elif "Magazine" in collage_layout and num_photos == 3:
                        half_width = content_width // 2
                        half_height = content_height // 2
                        gap = 20

                        # Nuotrauka 1 (viršuje kairėje)
                        img1 = edited_images[0].resize((half_width - gap, half_height - gap), Image.Resampling.LANCZOS)
                        if img1.mode != "RGBA":
                            img1 = img1.convert("RGBA")
                        styled1 = add_photo_effects(
                            img1,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        collage.paste(styled1, (padding, padding), styled1)

                        # Nuotrauka 2 (viršuje dešinėje - didelė)
                        img2 = edited_images[1].resize((half_width - gap, content_height), Image.Resampling.LANCZOS)
                        if img2.mode != "RGBA":
                            img2 = img2.convert("RGBA")
                        styled2 = add_photo_effects(
                            img2,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        collage.paste(styled2, (padding + half_width + gap, padding), styled2)

                        # Teksto kvadratas (apačioje kairėje)
                        text_box = create_text_box(
                            half_width - gap,
                            half_height - gap,
                            text_content,
                            style=collage_style,
                            font_size=text_font_size - 10,
                            columns=text_columns_num,
                            underline_first_word=underline_first
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        collage.paste(shadowed_text, (padding, padding + half_height + gap), shadowed_text)

                    # ============ MOSAIC LAYOUT (4 nuotraukos) ============
                    elif "Mosaic" in collage_layout and num_photos >= 4:
                        # Kompleksiškas mozaikos layout
                        gap = 15

                        # Didelė nuotrauka kairėje
                        big_size = int(content_height * 0.65)
                        img_big = edited_images[0].resize((big_size, big_size), Image.Resampling.LANCZOS)
                        if img_big.mode != "RGBA":
                            img_big = img_big.convert("RGBA")
                        styled_big = add_photo_effects(
                            img_big,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        collage.paste(styled_big, (padding, padding), styled_big)

                        # 2 mažos nuotraukos dešinėje viršuje
                        small_size = (content_width - big_size - gap * 2) // 2
                        for i in range(2):
                            img_small = edited_images[i + 1].resize((small_size, small_size), Image.Resampling.LANCZOS)
                            if img_small.mode != "RGBA":
                                img_small = img_small.convert("RGBA")
                            styled_small = add_photo_effects(
                                img_small,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength,
                            )
                            x_pos = padding + big_size + gap + i * (small_size + gap)
                            collage.paste(styled_small, (x_pos, padding), styled_small)

                        # Teksto kvadratas apačioje dešinėje
                        text_width = content_width - big_size - gap
                        text_height = content_height - small_size - gap * 2
                        text_box = create_text_box(
                            text_width, text_height, text_content, style=collage_style, font_size=text_font_size,
                            columns=text_columns_num, underline_first_word=underline_first
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        collage.paste(
                            shadowed_text, (padding + big_size + gap, padding + small_size + gap), shadowed_text
                        )

                        # 1 nuotrauka apačioje kairėje
                        bottom_size = content_height - big_size - gap
                        if num_photos >= 4:
                            img_bottom = edited_images[3].resize((big_size, bottom_size), Image.Resampling.LANCZOS)
                            if img_bottom.mode != "RGBA":
                                img_bottom = img_bottom.convert("RGBA")
                            shadowed_bottom = add_modern_shadow(img_bottom, shadow_strength=50, shadow_offset=10)
                            collage.paste(shadowed_bottom, (padding, padding + big_size + gap), shadowed_bottom)

                    # ============ DYNAMIC ANGLES LAYOUT (Pasvirusios nuotraukos) ============
                    elif "Dynamic" in collage_layout and num_photos == 2:
                        # 2 nuotraukos su energingu pasisukimu
                        photo_width = int(content_width * 0.48)
                        photo_height = int(content_height * 0.5)

                        # 1-a nuotrauka (pasukta -8 laipsniai, kairėje)
                        img1 = edited_images[0].resize((photo_width, photo_height), Image.Resampling.LANCZOS)
                        if img1.mode != "RGBA":
                            img1 = img1.convert("RGBA")
                        styled1 = add_photo_effects(
                            img1,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        styled1_rotated = styled1.rotate(-8, expand=True, fillcolor=(0, 0, 0, 0))
                        x1 = padding
                        y1 = content_start_y + 30
                        collage.paste(styled1_rotated, (x1, y1), styled1_rotated)

                        # 2-a nuotrauka (pasukta +8 laipsniai, dešinėje)
                        img2 = edited_images[1].resize((photo_width, photo_height), Image.Resampling.LANCZOS)
                        if img2.mode != "RGBA":
                            img2 = img2.convert("RGBA")
                        styled2 = add_photo_effects(
                            img2,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength,
                        )
                        styled2_rotated = styled2.rotate(8, expand=True, fillcolor=(0, 0, 0, 0))
                        x2 = padding + photo_width + 20
                        y2 = content_start_y
                        collage.paste(styled2_rotated, (x2, y2), styled2_rotated)

                        # Teksto kvadratas apačioje centre
                        text_width = content_width - 100
                        text_height = 140
                        text_box = create_text_box(
                            text_width, text_height, text_content, style=collage_style, font_size=text_font_size + 10,
                            columns=text_columns_num, underline_first_word=underline_first
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        text_y = content_start_y + photo_height + 50
                        collage.paste(shadowed_text, (padding + 50, text_y), shadowed_text)

                    # === TELEFONO NUMERIS (VISIEMS LAYOUT'AMS IŠSKYRUS MODERN LANDING) ===
                    if show_phone_number and default_phone and "Modern Landing" not in collage_layout:
                        # Konvertuojame į RGB prieš piešiant tekstą
                        collage = collage.convert("RGB")
                        draw = ImageDraw.Draw(collage)
                        
                        # Telefono numerio fontas - Times New Roman 50px - keletas fallback
                        font_phone = None
                        font_paths = [
                            "C:/Windows/Fonts/timesbd.ttf",  # Times New Roman Bold
                            "C:/Windows/Fonts/times.ttf",  # Times New Roman Regular
                            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",  # Linux
                            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
                            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",  # Linux DejaVu
                            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                            "/System/Library/Fonts/Times New Roman.ttf",  # macOS
                            "C:/Windows/Fonts/arial.ttf",  # Arial fallback
                        ]
                        
                        for font_path in font_paths:
                            try:
                                font_phone = ImageFont.truetype(font_path, 50)
                                break
                            except:
                                continue
                        
                        # Jei joks fontas nerastas
                        if font_phone is None:
                            try:
                                font_phone = ImageFont.truetype("arial.ttf", 50)
                            except:
                                font_phone = ImageFont.load_default()
                        
                        # Apskaičiuojame telefono numerio dydį
                        phone_bbox = draw.textbbox((0, 0), default_phone, font=font_phone)
                        phone_width = phone_bbox[2] - phone_bbox[0]
                        phone_height = phone_bbox[3] - phone_bbox[1]
                        
                        # Centruojame telefono numerį apačioje
                        phone_x = (canvas_width - phone_width) // 2
                        phone_y = canvas_height - phone_height - 80
                        
                        # Piešiame telefono numerį (be šešėlio)
                        draw.text((phone_x, phone_y), default_phone, fill=(30, 41, 59), font=font_phone)
                    
                    # Pridedame logo (IŠSKYRUS Magazine Style - ten logo jau yra)
                    if "Magazine Style" not in collage_layout:
                        collage = add_logo_to_image(
                            collage, logo_path="assets/logo.png", logo_size=100, position="top-left"
                        )

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
                        
                        # Paruošiame visus variantus JavaScript
                        cleaned_variants = [clean_variant(v) for v in variants]
                        
                        # Sukuriame JavaScript array su visais variantais
                        js_array_parts = []
                        for v in cleaned_variants:
                            js_text = v.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$').replace('\n', '\\n').replace('\r', '').replace('"', '\\"')
                            js_array_parts.append(f'"{js_text}"')
                        
                        js_array_string = ', '.join(js_array_parts)
                        
                        # HTML radio buttons + copy mygtukas
                        entry_id = entry['id']
                        radio_html = f"""
                        <div style="margin-bottom: 10px;">
                            <input type="radio" id="v1_{entry_id}" name="variant_{entry_id}" value="0" checked>
                            <label for="v1_{entry_id}">💼</label>
                            
                            <input type="radio" id="v2_{entry_id}" name="variant_{entry_id}" value="1" {"" if len(cleaned_variants) > 1 else "disabled"}>
                            <label for="v2_{entry_id}">🏡</label>
                            
                            <input type="radio" id="v3_{entry_id}" name="variant_{entry_id}" value="2" {"" if len(cleaned_variants) > 2 else "disabled"}>
                            <label for="v3_{entry_id}">😄</label>
                        </div>
                        <button id="copy_btn_{entry_id}" onclick="
                            var selectedRadio = document.querySelector('input[name=\\'variant_{entry_id}\\']:checked');
                            var variantIndex = parseInt(selectedRadio.value);
                            var texts = [{js_array_string}];
                            var textToCopy = texts[variantIndex];
                            
                            navigator.clipboard.writeText(textToCopy).then(function() {{
                                document.getElementById('copy_btn_{entry_id}').innerHTML = '✅ Nukopijuota!';
                                document.getElementById('copy_btn_{entry_id}').style.backgroundColor = '#28a745';
                                setTimeout(function() {{
                                    document.getElementById('copy_btn_{entry_id}').innerHTML = '📋 Kopijuoti';
                                    document.getElementById('copy_btn_{entry_id}').style.backgroundColor = '#0066cc';
                                }}, 1500);
                            }});
                        " style="background-color: #0066cc; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px; width: 100%;">
                            📋 Kopijuoti
                        </button>
                        """
                        st.markdown(radio_html, unsafe_allow_html=True)
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
    st.text_area(
        "Kopijuokite tekstą:", value=st.session_state.ai_content_result, height=200, key="ai_content_persistent"
    )

    # Analitikos informacija
    if "ai_analyses" in st.session_state:
        with st.expander("📊 Detali analizė"):
            st.markdown("**Vaizdų analizė:**")
            for i, analysis in enumerate(st.session_state.ai_analyses):
                st.markdown(f"**Nuotrauka {i+1}:** {analysis}")

# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")
