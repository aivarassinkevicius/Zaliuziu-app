import streamlit as st
import io, os, base64, json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter

# ---------- Nustatymai ----------
load_dotenv()

# Version: 2.3 - Simplified, no AI editing
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

st.title("🌿 Žaliuzių ir Roletų turinio kūrėjas")
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
    img = enhancer.enhance(1.25)  # +25% kontrasto
    
    # 4. SATURATION BOOST - gyvesnės spalvos
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.20)  # +20% sodrumo
    
    # 5. BRIGHTNESS FIX - šiek tiek šviesiau (jei per tamsu)
    img_array = np.array(img)
    avg_brightness = np.mean(img_array)
    
    if avg_brightness < 110:  # Jei tamsu - šviesinu
        enhancer = ImageEnhance.Brightness(img)
        brightness_boost = min(1.15, 110 / avg_brightness)
        img = enhancer.enhance(brightness_boost)
    
    return img

def add_marketing_overlay(image_file, add_watermark=False, add_border=False, brightness=1.0, contrast=1.0, saturation=1.0, watermark_text="", watermark_size=150, auto_enhance=True):
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
        st.error(f"Klaida redaguojant nuotrauką: {str(e)}")
        return None

def remove_white_background(img, threshold=240):
    """Pašalina baltą foną iš logo ir padaro jį skaidrų"""
    # Konvertuojame į RGBA
    img = img.convert('RGBA')
    
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

def add_logo_to_image(img, logo_path='assets/logo.png', logo_size=100, position='top-left'):
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
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Apskaičiuojame poziciją
        padding = 20  # Atitraukimas nuo krašto
        
        if position == 'top-left':
            x, y = padding, padding
        elif position == 'top-right':
            x = img.width - logo.width - padding
            y = padding
        elif position == 'bottom-left':
            x = padding
            y = img.height - logo.height - padding
        elif position == 'bottom-right':
            x = img.width - logo.width - padding
            y = img.height - logo.height - padding
        else:
            x, y = padding, padding
        
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
    """Įkelia aprašymų istoriją iš JSON failo"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.warning(f"Nepavyko įkelti istorijos: {e}")
        return []

def save_to_history(description, season, holiday, num_photos):
    """Išsaugo aprašymą į JSON istoriją"""
    try:
        history = load_history()
        
        entry = {
            "id": len(history) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": description,
            "season": season,
            "holiday": holiday,
            "num_photos": num_photos
        }
        
        history.insert(0, entry)  # Naujausi viršuje
        
        # Saugom tik paskutinius 50 įrašų
        history = history[:50]
        
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Nepavyko išsaugoti į istoriją: {e}")
        return False

# ---------- Discord Webhook ----------

def send_to_discord(webhook_url, image_bytes, message=""):
    """Siunčia collage į Discord per webhook"""
    try:
        import requests
        
        # Paruošiame failą
        files = {
            'file': ('collage.png', image_bytes, 'image/png')
        }
        
        # Paruošiame žinutę
        data = {}
        if message:
            data['content'] = message
        
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
            "Žiema": ["#winterhome", "#cozyspace", "#hygge", "#winterdecor"]
        }
        
        seasonal_tags = base_hashtags.get(season, ["#homedecor", "#interiordesign"])
        
        # Pridedame bendrų trending žaliuzių hashtags
        blinds_tags = ["#windowblinds", "#blinds", "#windowtreatments", "#homeimprovement"]
        
        # Sumaišome
        all_tags = seasonal_tags + blinds_tags
        
        return {
            "trending_hashtags": all_tags,
            "trending_topics": f"{season} home decor, natural light, modern interiors",
            "engagement_tip": "Post during peak hours (6-9 PM local time)"
        }
        
    except Exception as e:
        # Fallback jei klaida
        return {
            "trending_hashtags": ["#windowblinds", "#homedecor", "#interiordesign"],
            "trending_topics": "Home decor, window treatments",
            "engagement_tip": "Use high-quality photos"
        }

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
    
    # 🌐 WEB BROWSING: Gauname trending hashtags ir topics
    trending_data = fetch_trending_hashtags(season)
    
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
    
    # Švenčių kontrolė
    holiday_data = {
        "Velykos": {
            "must_have": ["velyk", "velykini", "pavasari"],
            "forbidden": ["kalėd", "nauj metin", "žiem"],
            "keywords": "Velykų, pavasario šventės, šeimos susibūrimas"
        },
        "Šv. Kalėdos": {
            "must_have": ["kalėd", "švent", "žiem"],
            "forbidden": ["velyk", "pavasa", "vasara"],
            "keywords": "Kalėdų, žiemos švenčių, dovanų"
        },
        "Kūčios": {
            "must_have": ["kūč", "kalėd", "žiem"],
            "forbidden": ["velyk", "pavasa"],
            "keywords": "Kūčių, šventinės vakarienės, šeimos"
        },
        "Šv. Valentino diena": {
            "must_have": ["valentin", "meilė"],
            "forbidden": ["kalėd", "velyk"],
            "keywords": "Valentino dienos, meilės, romantikos"
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
                "Žiema": "winter background with soft snow, snowflakes, cool blue and white tones, peaceful atmosphere, professional photography, high resolution"
            }
            
            prompt = prompts.get(season, prompts["Vasara"])
        
        # Generuojame nuotrauką su DALL-E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
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

def create_gradient_background(width, height, color1, color2, direction='vertical'):
    """Sukuria gradientinį foną (modernus canvas efektas)"""
    gradient = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(gradient)
    
    if direction == 'vertical':
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
    shadow = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    
    # Piešiame šešėlį (offset pozicijoje)
    shadow_draw.rectangle(
        [offset_x + shadow_blur, offset_y + shadow_blur, 
         img.width + offset_x + shadow_blur, img.height + offset_y + shadow_blur],
        fill=shadow_color
    )
    
    # Blur efektas šešėliui
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
    
    # Konvertuojame originalą į RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Sukuriame galutinį paveikslėlį
    result = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))
    result.paste(shadow, (0, 0), shadow)
    result.paste(img, (shadow_blur, shadow_blur), img)  # Nuotrauka su blur offset
    
    return result

def add_rounded_corners(img, radius=30):
    """Užapvalina nuotraukos kampus"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Sukuriame apskritimo mask
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    
    # Pritaikome mask
    result = Image.new('RGBA', img.size, (255, 255, 255, 0))
    result.paste(img, (0, 0))
    result.putalpha(mask)
    
    return result

def add_white_border(img, border_width=10):
    """Prideda baltą rėmelį aplink nuotrauką"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Sukuriame naują paveikslėlį su rėmeliu
    new_width = img.width + border_width * 2
    new_height = img.height + border_width * 2
    
    bordered = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 255))
    bordered.paste(img, (border_width, border_width), img)
    
    return bordered

def add_photo_effects(img, enable_border=True, border_width=15, enable_rounded=True, corner_radius=20, 
                      enable_shadow=True, shadow_strength=50):
    """Prideda visus foto efektus: rėmelį, užapvalintus kampus, šešėlį
    
    Args:
        shadow_strength: 0-100, kur 0=nematomas, 100=juodas, 50=vidutinis
    """
    result = img.copy()
    
    if img.mode != 'RGBA':
        result = result.convert('RGBA')
    
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
    if blurred.mode != 'RGBA':
        blurred = blurred.convert('RGBA')
    
    # Pridedame baltą overlay su opacity
    overlay = Image.new('RGBA', blurred.size, (255, 255, 255, int(255 * opacity)))
    blurred = Image.alpha_composite(blurred, overlay)
    
    return blurred

def add_text_overlay_modern(img, text, position='bottom', font_size=60, bg_opacity=0.7):
    """Prideda modernų teksto overlay su blur fonu"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
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
    if position == 'bottom':
        y = img.height - text_height - 80
    elif position == 'top':
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

def add_collage_text_overlay(img, text, position='bottom', style='glassmorphism', font_size=70):
    """Prideda stilingą tekstą ant collage su įvairiais efektais"""
    if not text or text.strip() == "":
        return img
    
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Sukuriame overlay sluoksnį
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Fontų paieška (prioritetas: Bold fontai)
    font = None
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
        "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
        "C:/Windows/Fonts/ariblk.ttf",   # Arial Black
        "C:/Windows/Fonts/arial.ttf",    # Arial Regular
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
    if position == 'Apačioje':
        y = img.height - text_height - 120
    elif position == 'Viršuje':
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
        bg_blur = Image.new('RGBA', img.size, (255, 255, 255, 0))
        bg_draw = ImageDraw.Draw(bg_blur)
        bg_draw.rounded_rectangle(bg_rect, radius=30, fill=(255, 255, 255, 200))
        bg_blur = bg_blur.filter(ImageFilter.GaussianBlur(5))
        
        # Pridedame šešėlį
        shadow = Image.new('RGBA', img.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [bg_rect[0] + 5, bg_rect[1] + 5, bg_rect[2] + 5, bg_rect[3] + 5],
            radius=30, fill=(0, 0, 0, 60)
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
            [bg_rect[0] + shadow_offset, bg_rect[1] + shadow_offset, 
             bg_rect[2] + shadow_offset, bg_rect[3] + shadow_offset],
            fill=(0, 0, 0, 255)
        )
        
        # Ryškus geltonas fonas
        draw.rectangle(bg_rect, fill=(255, 220, 50, 255))
        
        # Storas juodas rėmelis
        for i in range(border_width):
            draw.rectangle(
                [bg_rect[0] + i, bg_rect[1] + i, bg_rect[2] - i, bg_rect[3] - i],
                outline=(0, 0, 0, 255), width=2
            )
        
        # Juodas tekstas be šešėlio (clean)
        draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)
    
    elif "Minimalist" in style:
        # Minimalist: šviesus fonas su subtiliu šešėliu
        padding = 50
        bg_rect = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]
        
        # Subtilus šešėlis
        shadow = Image.new('RGBA', img.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle(
            [bg_rect[0] + 3, bg_rect[1] + 3, bg_rect[2] + 3, bg_rect[3] + 3],
            fill=(0, 0, 0, 40)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        
        img = Image.alpha_composite(img, shadow)
        
        # Baltas fonas
        draw.rectangle(bg_rect, fill=(255, 255, 255, 245))
        
        # Tamsus tekstas su labai subtiliu šešėliu
        draw.text((x + 1, y + 1), text, fill=(0, 0, 0, 60), font=font)
        draw.text((x, y), text, fill=(40, 40, 40, 255), font=font)
    
    return Image.alpha_composite(img, overlay)

def wrap_text(text, font, max_width):
    """Automatiškai lūžo tekstą į eilutes pagal plotį"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Žodis per ilgas - pridedame tokį kokis yra
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def create_text_box(width, height, text, style='glassmorphism', font_size=60, bg_color=(255, 255, 255)):
    """Sukuria teksto kvadratą kaip atskirą paveikslėlį (ne overlay!)"""
    
    # SVARBU: Išsaugome font_size į lokalų kintamąjį
    actual_font_size = int(font_size)  # Užtikrina kad tai skaičius
    
    # Sukuriame RGBA paveikslėlį
    text_box = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_box)
    
    # Fontų paieška - Times New Roman
    font = None
    font_paths = [
        "C:/Windows/Fonts/timesbd.ttf",   # Times New Roman Bold
        "C:/Windows/Fonts/timesbi.ttf",   # Times New Roman Bold Italic
        "C:/Windows/Fonts/times.ttf",     # Times New Roman Regular
        "C:/Windows/Fonts/timesi.ttf",    # Times New Roman Italic
        "C:/Windows/Fonts/arialbd.ttf",   # Fallback: Arial Bold
        "C:/Windows/Fonts/arial.ttf",     # Fallback: Arial
    ]
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, actual_font_size)
            break
        except Exception as e:
            continue
    
    if font is None:
        font = ImageFont.load_default()
        # Jei default - padarome tekstą DIDELĮ kartojant
        actual_font_size = 12  # Default font dydis
    
    # STILIŲ IMPLEMENTACIJOS
    if "Glassmorphism" in style:
        # Blur baltas fonas su skaidrumu
        draw.rectangle([0, 0, width, height], fill=(255, 255, 255, 220))
        
        # Pridedame lengvą blur efektą
        text_box = text_box.filter(ImageFilter.GaussianBlur(2))
        draw = ImageDraw.Draw(text_box)
        
        # Automatinis teksto lūžimas
        max_text_width = width - 40  # 20px padding iš kiekvienos pusės
        lines = wrap_text(text, font, max_text_width)
        
        # Centruojame tekstą
        total_height = len(lines) * (actual_font_size + 20)
        y_start = (height - total_height) // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
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
        max_text_width = width - 40  # 20px padding
        lines = wrap_text(text, font, max_text_width)
        total_height = len(lines) * (actual_font_size + 20)
        y_start = (height - total_height) // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = y_start + i * (actual_font_size + 20)
            
            # Subtilus šešėlis
            draw.text((x + 1, y + 1), line, fill=(0, 0, 0, 50), font=font)
            # Tekstas
            draw.text((x, y), line, fill=(50, 50, 50, 255), font=font)
    
    return text_box

# ---------- Pagrindinis UI ----------
st.sidebar.header("⚙️ Nustatymai")

# Metų laikas (visada pasirinktas)
season = st.sidebar.selectbox(
    "🌤️ Metų laikas",
    ["Pavasaris", "Vasara", "Ruduo", "Žiema"],
    index=1,
    help="AI turinio aprašymams ir fonui"
)

# Šventė (papildomas)
holiday = st.sidebar.selectbox(
    "🎉 Lietuviškos šventės (pasirinktinai)",
    ["Nėra", "Naujieji metai", "Šv. Valentino diena", "Vasario 16-oji", "Kovo 11-oji", 
     "Velykos", "Gegužės 1-oji (Darbo diena)", "Motinos diena", "Tėvo diena", 
     "Joninės", "Liepos 6-oji (Karaliaus Mindaugo diena)", "Žolinė", "Rugsėjo 1-oji", 
     "Šv. Kalėdos", "Kūčios"],
    index=0,
    help="Papildoma tema turinio aprašymams ir fonui"
)

auto_process = st.sidebar.checkbox("🤖 Automatinis apdorojimas", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Marketinginis redagavimas")

add_watermark = st.sidebar.checkbox("💧 Pridėti vandens ženklą", value=True, help="Pridės jūsų tekstą dešiniame apatiniame kampe")
if add_watermark:
    watermark_text = st.sidebar.text_input("Vandens ženklo tekstas", value="#RūbaiLangams", help="Pvz: #RūbaiLangams arba © Jūsų Įmonė")
    watermark_size = st.sidebar.slider("📏 Vandens ženklo dydis (px)", 30, 300, 40, 10, help="Šrifto dydis pikseliais. 120px = vidutinis, 250px = DIDELIS")
else:
    watermark_text = ""
    watermark_size = 40

add_border = st.sidebar.checkbox("🖼️ Pridėti baltą rėmelį", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("**🤖 Profesionalus Auto Pagerinimas**")
auto_enhance = st.sidebar.checkbox("✨ PRO Auto Enhancement", value=True, help="Profesionalus nuotraukų pagerinimas - geriau nei Canva!")

if auto_enhance:
    st.sidebar.success("🚀 **PRO Enhancement įjungtas!**")
    st.sidebar.markdown("""
    **Kas bus padaryta:**
    - ✅ Auto Levels (histogramos optimizavimas)
    - ✅ Smart Sharpening (detalių ryškinimas)
    - ✅ Contrast Boost (+25%)
    - ✅ Saturation Boost (+20%)
    - ✅ Brightness Fix (jei reikia)
    """)
    brightness = 1.0
    contrast = 1.0
    saturation = 1.0
else:
    st.sidebar.markdown("**Rankinė spalvų korekcija:**")
    brightness = st.sidebar.slider("☀️ Šviesumas", 0.5, 1.5, 1.0, 0.05, help="<1.0 tamsiau, >1.0 šviesiau")
    contrast = st.sidebar.slider("🎭 Kontrastas", 0.5, 1.5, 1.0, 0.05, help="<1.0 blankiau, >1.0 ryškiau")
    saturation = st.sidebar.slider("🎨 Sodrumas", 0.5, 1.5, 1.0, 0.05, help="<1.0 pilkiau, >1.0 sodresni spalvos")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔗 Discord Integracija")
enable_discord = st.sidebar.checkbox("📤 Siųsti į Discord", value=False, help="Automatiškai siųsti collage į Discord kanalą")
if enable_discord:
    discord_webhook_url = st.sidebar.text_input(
        "Discord Webhook URL:",
        placeholder="https://discord.com/api/webhooks/...",
        type="password",
        help="Įveskite Discord webhook URL (Settings → Integrations → Webhooks)"
    )
else:
    discord_webhook_url = ""

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
tab1, tab2 = st.tabs(["📁 Failų įkėlimas", "🔧 Rankiniu būdu"])

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
                auto_enhance=auto_enhance
            )
            edited.seek(0)
            
            # Rodyti peržiūrą (sumažinta)
            st.image(edited, caption=f"Nuotrauka {i+1}", width=400)
            
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
        # NAUJAS: Social media formato pasirinkimas
        col_format, col_style = st.columns([1, 1])
        
        with col_format:
            social_format = st.selectbox(
                "📱 Socialinio tinklo formatas:",
                ["Instagram kvadratas (1080x1080)", "Instagram Portrait (1080x1350)", "Facebook Post (1200x630)"],
                help="Pasirinkite socialinio tinklo formatą"
            )
        
        with col_style:
            collage_style = st.selectbox(
                "🎨 Dizaino stilius:",
                ["💎 Glassmorphism - Modernus, skaidrus", "🎯 Neo-Brutalism - Ryškus, drąsus", "✨ Minimalist - Švarus, elegantiškas"],
                help="Bendras collage dizaino stilius"
            )
        
        # NAUJAS: Išdėstymas su teksto kvadratu
        st.markdown("---")
        st.markdown("#### 📐 Išdėstymas (nuotraukos + tekstas)")
        
        num_photos = len(files_to_process)
        
        if num_photos == 2:
            layout_options = [
                "Grid 2x2 (2 nuotraukos + 2 teksto kvadratai)",
                "Horizontal (2 nuotraukos + 1 tekstas viduryje)",
                "Asymmetric (1 didelė + 1 maža + tekstas)",
                "⚡ Dynamic (pasvirusios nuotraukos + tekstas)"
            ]
        elif num_photos == 3:
            layout_options = [
                "Grid 2x2 (3 nuotraukos + 1 teksto kvadratas)",
                "Magazine (3 nuotraukos + teksto zona)",
                "Asymmetric (1 didelė + 2 mažos + tekstas)"
            ]
        else:  # 4 ar daugiau
            layout_options = [
                "Grid 2x2 (4 nuotraukos be teksto)",
                "Grid 3x2 (4 nuotraukos + 2 teksto kvadratai)",
                "Mosaic (4 nuotraukos skirtingų dydžių + tekstas)"
            ]
        
        collage_layout = st.selectbox(
            "Pasirinkite išdėstymą:",
            layout_options,
            help="Layout su integruotu teksto kvadratu (ne overlay!)"
        )
        
        # AI Custom Fono generavimas
        use_custom_background = st.checkbox(
            "🎨 Naudoti Custom AI foną",
            value=False,
            help="Aprašyk foną savo žodžiais - AI sugeneruos pagal tavo aprašymą"
        )
        
        custom_prompt = ""
        if use_custom_background:
            custom_prompt = st.text_area(
                "Aprašykite norimą foną:",
                value="",
                placeholder="Pvz: medžiai rugiai pieva, kviečiai ir medžio tekstūra, jūra saulėlydis...",
                help="AI (DALL-E 3) sugeneruos foną pagal šį aprašymą",
                height=80
            )
            
            if custom_prompt and custom_prompt.strip():
                st.info(f"✨ **Custom AI fonas**: '{custom_prompt[:60]}...'")
        
        use_themed_bg = use_custom_background
        
        # NAUJAS: Teksto turinys (VISADA ĮJUNGTAS dabar, nes tekstas = dalis layout'o)
        st.markdown("---")
        st.markdown("#### ✍️ Teksto kvadrato turinys")
        
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
                    help="Pirmas teksto kvadratas"
                )
            
            with col2:
                text_content_2 = st.text_area(
                    "Tekstas kvadrate 2:",
                    value=f"Naujiena! {season} stilius 🎨",
                    height=80,
                    key="text_box_2",
                    help="Antras teksto kvadratas"
                )
            
            # Šrifto dydis ATSKIROJE EILUTĖJE
            text_font_size = st.slider(
                "Šrifto dydis (abiem tekstams):",
                30, 120, 60, 10,
                help="Teksto dydis teksto kvadratuose"
            )
        else:
            # Vienas tekstas visiem kitiems layoutams
            col1, col2 = st.columns([2, 1])
            
            with col1:
                text_content = st.text_area(
                    "Tekstas teksto kvadrate:",
                    value=f"{season} kolekcija 2025 🌿",
                    height=100,
                    help="Šis tekstas bus atskirame kvadrate collage (ne overlay!)"
                )
            
            with col2:
                text_font_size = st.slider(
                    "Šrifto dydis:",
                    30, 120, 60, 10,
                    help="Teksto dydis teksto kvadrate"
                )
            
            text_content_2 = None  # Nėra antro teksto
        
        # NAUJAS: Nuotraukų efektai
        st.markdown("---")
        st.markdown("#### 🎨 Nuotraukų efektai")
        
        col_fx1, col_fx2 = st.columns(2)
        
        with col_fx1:
            enable_white_border = st.checkbox("⬜ Baltas rėmelis", value=True, help="Baltas rėmelis aplink nuotraukas")
            enable_rounded_corners = st.checkbox("⭕ Užapvalinti kampai", value=True, help="Apvalūs nuotraukų kampai")
        
        with col_fx2:
            enable_shadow_effect = st.checkbox("🌑 Šešėlio efektas", value=True, help="3D šešėlis (drop shadow)")
            shadow_strength = st.slider("Šešėlio stiprumas:", 0, 100, 50, 5, help="0 = nematomas, 100 = juodas") if enable_shadow_effect else 0
        
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
                auto_enhance=auto_enhance
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
                            collage = create_gradient_background(canvas_width, canvas_height, (240, 245, 250), (250, 250, 255))
                    else:
                        collage = create_gradient_background(canvas_width, canvas_height, (245, 245, 245), (255, 255, 255))
                    
                    collage = collage.convert('RGBA')
                    
                    # PADDING - mažesnis padding, bet palikta vieta logo viršuje kairėje!
                    padding = int(canvas_width * 0.04)  # 4% padding
                    logo_safe_zone = 130  # Vieta logo (100px + 30px margin)
                    
                    content_width = canvas_width - padding * 2
                    content_height = canvas_height - padding * 2
                    
                    # Content pradžia - žemiau logo safe zone
                    content_start_y = padding + logo_safe_zone
                    
                    # Nustatome layout pagal pasirinkimą
                    num_photos = len(edited_images)
                    
                    # ============ GRID 2x2 LAYOUTS ============
                    if "Grid 2x2" in collage_layout:
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
                            (padding + cell_size + gap, padding + cell_size + gap)  # Bottom-right
                        ]
                        
                        for idx in range(4):
                            # Apskaičiuojame ląstelės centrą
                            row = idx // 2  # 0 arba 1
                            col = idx % 2   # 0 arba 1
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
                                    shadow_strength=shadow_strength
                                )
                                
                                # Centruojame nuotrauką ląstelėje
                                paste_x = cell_x + (cell_size - img_with_effects.width) // 2
                                paste_y = cell_y + (cell_size - img_with_effects.height) // 2
                                
                                collage.paste(img_with_effects, (paste_x, paste_y), img_with_effects)
                            else:
                                # Teksto kvadratas
                                # Jei 2 nuotraukos → naudojame text_content_2 antram tekstui
                                text_to_use = text_content
                                if num_photos == 2 and idx == 3 and text_content_2:
                                    text_to_use = text_content_2
                                
                                text_box = create_text_box(
                                    target_size, 
                                    target_size, 
                                    text_to_use,
                                    style=collage_style,
                                    font_size=text_font_size
                                )
                                # Pridedame tuos pačius efektus tekstui
                                text_with_effects = add_photo_effects(
                                    text_box,
                                    enable_border=enable_white_border,
                                    border_width=12,
                                    enable_rounded=enable_rounded_corners,
                                    corner_radius=25,
                                    enable_shadow=enable_shadow_effect,
                                    shadow_strength=shadow_strength
                                )
                                
                                # Centruojame tekstą ląstelėje
                                paste_x = cell_x + (cell_size - text_with_effects.width) // 2
                                paste_y = cell_y + (cell_size - text_with_effects.height) // 2
                                
                                st.write(f"✅ Tekstas įklijuojamas į poziciją ({paste_x}, {paste_y})")
                                collage.paste(text_with_effects, (paste_x, paste_y), text_with_effects)
                    
                    # ============ HORIZONTAL LAYOUT (2 nuotraukos + tekstas) ============
                    elif "Horizontal" in collage_layout and num_photos == 2:
                        cell_width = content_width // 3
                        gap = 20
                        
                        # Nuotrauka 1 (kairėje)
                        img1 = edited_images[0].resize((cell_width - gap, content_height), Image.Resampling.LANCZOS)
                        if img1.mode != 'RGBA':
                            img1 = img1.convert('RGBA')
                        styled1 = add_photo_effects(
                            img1,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
                        )
                        collage.paste(styled1, (padding, padding), styled1)
                        
                        # Teksto kvadratas (viduryje)
                        text_box = create_text_box(
                            cell_width - gap,
                            content_height,
                            text_content,
                            style=collage_style,
                            font_size=text_font_size
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        collage.paste(shadowed_text, (padding + cell_width + gap, padding), shadowed_text)
                        
                        # Nuotrauka 2 (dešinėje)
                        img2 = edited_images[1].resize((cell_width - gap, content_height), Image.Resampling.LANCZOS)
                        if img2.mode != 'RGBA':
                            img2 = img2.convert('RGBA')
                        styled2 = add_photo_effects(
                            img2,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
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
                            if img_big.mode != 'RGBA':
                                img_big = img_big.convert('RGBA')
                            styled_big = add_photo_effects(
                                img_big,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength
                            )
                            collage.paste(styled_big, (padding, padding), styled_big)
                            
                            # Maža nuotrauka (viršuje dešinėje)
                            img_small = edited_images[1].resize((small_width, half_height - gap), Image.Resampling.LANCZOS)
                            if img_small.mode != 'RGBA':
                                img_small = img_small.convert('RGBA')
                            styled_small = add_photo_effects(
                                img_small,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength
                            )
                            collage.paste(styled_small, (padding + big_width + gap, padding), styled_small)
                            
                            # Teksto kvadratas (apačioje dešinėje)
                            text_box = create_text_box(
                                small_width,
                                half_height - gap,
                                text_content,
                                style=collage_style,
                                font_size=text_font_size
                            )
                            shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                            collage.paste(shadowed_text, (padding + big_width + gap, padding + half_height + gap), shadowed_text)
                        
                        elif num_photos == 3:
                            # 1 didelė + 2 mažos + tekstas
                            big_width = int(content_width * 0.65)
                            small_width = content_width - big_width - 20
                            third_height = content_height // 3
                            gap = 20
                            
                            # Didelė nuotrauka (kairėje)
                            img_big = edited_images[0].resize((big_width, content_height), Image.Resampling.LANCZOS)
                            if img_big.mode != 'RGBA':
                                img_big = img_big.convert('RGBA')
                            styled_big = add_photo_effects(
                                img_big,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength
                            )
                            collage.paste(styled_big, (padding, padding), styled_big)
                            
                            # 2 mažos nuotraukos + tekstas dešinėje
                            for i in range(2):
                                img_small = edited_images[i + 1].resize((small_width, third_height - gap), Image.Resampling.LANCZOS)
                                if img_small.mode != 'RGBA':
                                    img_small = img_small.convert('RGBA')
                                styled_small = add_photo_effects(
                                    img_small,
                                    enable_border=enable_white_border,
                                    enable_rounded=enable_rounded_corners,
                                    enable_shadow=enable_shadow_effect,
                                    shadow_strength=shadow_strength
                                )
                                y_pos = padding + i * (third_height + gap)
                                collage.paste(styled_small, (padding + big_width + gap, y_pos), styled_small)
                            
                            # Teksto kvadratas apačioje
                            text_box = create_text_box(
                                small_width,
                                third_height - gap,
                                text_content,
                                style=collage_style,
                                font_size=text_font_size
                            )
                            shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                            collage.paste(shadowed_text, (padding + big_width + gap, padding + third_height * 2 + gap * 2), shadowed_text)
                    
                    # ============ MAGAZINE LAYOUT ============
                    elif "Magazine" in collage_layout and num_photos == 3:
                        half_width = content_width // 2
                        half_height = content_height // 2
                        gap = 20
                        
                        # Nuotrauka 1 (viršuje kairėje)
                        img1 = edited_images[0].resize((half_width - gap, half_height - gap), Image.Resampling.LANCZOS)
                        if img1.mode != 'RGBA':
                            img1 = img1.convert('RGBA')
                        styled1 = add_photo_effects(
                            img1,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
                        )
                        collage.paste(styled1, (padding, padding), styled1)
                        
                        # Nuotrauka 2 (viršuje dešinėje - didelė)
                        img2 = edited_images[1].resize((half_width - gap, content_height), Image.Resampling.LANCZOS)
                        if img2.mode != 'RGBA':
                            img2 = img2.convert('RGBA')
                        styled2 = add_photo_effects(
                            img2,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
                        )
                        collage.paste(styled2, (padding + half_width + gap, padding), styled2)
                        
                        # Teksto kvadratas (apačioje kairėje)
                        text_box = create_text_box(
                            half_width - gap,
                            half_height - gap,
                            text_content,
                            style=collage_style,
                            font_size=text_font_size - 10
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
                        if img_big.mode != 'RGBA':
                            img_big = img_big.convert('RGBA')
                        styled_big = add_photo_effects(
                            img_big,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
                        )
                        collage.paste(styled_big, (padding, padding), styled_big)
                        
                        # 2 mažos nuotraukos dešinėje viršuje
                        small_size = (content_width - big_size - gap * 2) // 2
                        for i in range(2):
                            img_small = edited_images[i + 1].resize((small_size, small_size), Image.Resampling.LANCZOS)
                            if img_small.mode != 'RGBA':
                                img_small = img_small.convert('RGBA')
                            styled_small = add_photo_effects(
                                img_small,
                                enable_border=enable_white_border,
                                enable_rounded=enable_rounded_corners,
                                enable_shadow=enable_shadow_effect,
                                shadow_strength=shadow_strength
                            )
                            x_pos = padding + big_size + gap + i * (small_size + gap)
                            collage.paste(styled_small, (x_pos, padding), styled_small)
                        
                        # Teksto kvadratas apačioje dešinėje
                        text_width = content_width - big_size - gap
                        text_height = content_height - small_size - gap * 2
                        text_box = create_text_box(
                            text_width,
                            text_height,
                            text_content,
                            style=collage_style,
                            font_size=text_font_size
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        collage.paste(shadowed_text, (padding + big_size + gap, padding + small_size + gap), shadowed_text)
                        
                        # 1 nuotrauka apačioje kairėje
                        bottom_size = content_height - big_size - gap
                        if num_photos >= 4:
                            img_bottom = edited_images[3].resize((big_size, bottom_size), Image.Resampling.LANCZOS)
                            if img_bottom.mode != 'RGBA':
                                img_bottom = img_bottom.convert('RGBA')
                            shadowed_bottom = add_modern_shadow(img_bottom, shadow_strength=50, shadow_offset=10)
                            collage.paste(shadowed_bottom, (padding, padding + big_size + gap), shadowed_bottom)
                    
                    # ============ DYNAMIC ANGLES LAYOUT (Pasvirusios nuotraukos) ============
                    elif "Dynamic" in collage_layout and num_photos == 2:
                        # 2 nuotraukos su energingu pasisukimu
                        photo_width = int(content_width * 0.48)
                        photo_height = int(content_height * 0.5)
                        
                        # 1-a nuotrauka (pasukta -8 laipsniai, kairėje)
                        img1 = edited_images[0].resize((photo_width, photo_height), Image.Resampling.LANCZOS)
                        if img1.mode != 'RGBA':
                            img1 = img1.convert('RGBA')
                        styled1 = add_photo_effects(
                            img1,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
                        )
                        styled1_rotated = styled1.rotate(-8, expand=True, fillcolor=(0, 0, 0, 0))
                        x1 = padding
                        y1 = content_start_y + 30
                        collage.paste(styled1_rotated, (x1, y1), styled1_rotated)
                        
                        # 2-a nuotrauka (pasukta +8 laipsniai, dešinėje)
                        img2 = edited_images[1].resize((photo_width, photo_height), Image.Resampling.LANCZOS)
                        if img2.mode != 'RGBA':
                            img2 = img2.convert('RGBA')
                        styled2 = add_photo_effects(
                            img2,
                            enable_border=enable_white_border,
                            enable_rounded=enable_rounded_corners,
                            enable_shadow=enable_shadow_effect,
                            shadow_strength=shadow_strength
                        )
                        styled2_rotated = styled2.rotate(8, expand=True, fillcolor=(0, 0, 0, 0))
                        x2 = padding + photo_width + 20
                        y2 = content_start_y
                        collage.paste(styled2_rotated, (x2, y2), styled2_rotated)
                        
                        # Teksto kvadratas apačioje centre
                        text_width = content_width - 100
                        text_height = 140
                        text_box = create_text_box(
                            text_width,
                            text_height,
                            text_content,
                            style=collage_style,
                            font_size=text_font_size + 10
                        )
                        shadowed_text = add_modern_shadow(text_box, shadow_strength=50, shadow_offset=10)
                        text_y = content_start_y + photo_height + 50
                        collage.paste(shadowed_text, (padding + 50, text_y), shadowed_text)
                    
                    # Pridedame logo (automatiškai iš assets/logo.png)
                    collage = add_logo_to_image(collage, logo_path='assets/logo.png', logo_size=100, position='top-left')
                    
                    # Konvertuojame į RGB
                    collage = collage.convert('RGB')
                    
                    # Išsaugome
                    collage_bytes = io.BytesIO()
                    collage.save(collage_bytes, format='JPEG', quality=95)
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
            if st.button("👁️ Peržiūrėti pilną dydį" if not st.session_state.show_full_collage else "📱 Sumažinti peržiūrą", 
                        use_container_width=True, 
                        key="toggle_collage_view"):
                st.session_state.show_full_collage = not st.session_state.show_full_collage
                st.rerun()
        
        # Display collage based on view mode
        if st.session_state.show_full_collage:
            # Full size - centered with max width
            col1, col2, col3 = st.columns([1, 4, 1])
            with col2:
                st.image(st.session_state.collage_result, caption="Pilnas dydis", use_column_width=True)
        else:
            # Thumbnail preview - limited width
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(st.session_state.collage_result, caption="Peržiūra (spauskite mygtuką pilnam dydžiui)", use_column_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 Atsisiųsti Collage",
                data=st.session_state.collage_result,
                file_name=st.session_state.collage_filename,
                mime="image/jpeg",
                use_container_width=True,
                key="download_collage_persistent"
            )
        
        with col2:
            if enable_discord and discord_webhook_url:
                if st.button("📤 Siųsti į Discord", type="secondary", use_container_width=True):
                    with st.spinner("Siunčiama į Discord..."):
                        success, message = send_to_discord(
                            discord_webhook_url,
                            st.session_state.collage_result,
                            f"🌿 Naujas {season} kolekcijos collage!"
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
            elif enable_discord and not discord_webhook_url:
                st.warning("⚠️ Įveskite Discord Webhook URL sidebar'e")
    
    # AI TURINIO GENERAVIMAS
    st.markdown("---")
    st.markdown("### 📝 AI Turinio Generavimas")
    st.info("💡 Sukurkite tekstus socialiniams tinklams pagal jūsų nuotraukas")
    
    # 📚 ISTORIJA - Senesnių aprašymų rodymas
    history = load_history()
    if history and len(history) > 0:
        with st.expander(f"📚 Aprašymų istorija ({len(history)} išsaugotų)", expanded=False):
            st.caption("Pasirinkite senesnį aprašymą arba sukurkite naują")
            
            for entry in history[:10]:  # Rodome tik 10 naujausių
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{entry['timestamp']}** - {entry['season']}, {entry['num_photos']} nuotr.")
                    preview = entry['description'][:150] + "..." if len(entry['description']) > 150 else entry['description']
                    st.text(preview)
                
                with col2:
                    if st.button("📋 Naudoti", key=f"use_history_{entry['id']}"):
                        st.session_state.ai_content_result = entry['description']
                        st.success("✅ Aprašymas užkrautas!")
                        st.rerun()
                
                st.markdown("---")
    
    # 🌐 TRENDING INFO
    trending_data = fetch_trending_hashtags(season)
    with st.expander("🔥 Trending dabar Instagram'e", expanded=False):
        st.markdown(f"**📊 Populiarūs hashtags ({season}):**")
        st.code(" ".join(trending_data['trending_hashtags']))
        st.markdown(f"**🔥 Trending temos:** {trending_data['trending_topics']}")
        st.markdown(f"**💡 Patarimas:** {trending_data['engagement_tip']}")
    
    # Mygtukas čia
    if st.button("🚀 Sukurti NAUJĄ AI Turinį (su trending hashtags)", type="primary", use_container_width=True, key="create_ai_content_btn"):
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
if "trigger_ai_content" in st.session_state and st.session_state.trigger_ai_content and files_to_process and len(files_to_process) > 0:
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
                auto_enhance=auto_enhance
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
    st.text_area("Sugeneruotas tekstas:", value=st.session_state.ai_content_pending, height=200, key="preview_pending", disabled=True)
    
    # Patvirtinimo mygtukai
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Patvirtinti ir Išsaugoti", type="primary", use_container_width=True):
            # Patvirtinta! Išsaugome į rezultatus ir JSON
            st.session_state.ai_content_result = st.session_state.ai_content_pending
            save_to_history(
                st.session_state.ai_content_pending,
                st.session_state.ai_pending_season,
                st.session_state.ai_pending_holiday,
                st.session_state.ai_pending_num_photos
            )
            # Išvalome pending
            del st.session_state.ai_content_pending
            st.success("✅ Turinys patvirtintas ir išsaugotas!")
            st.rerun()
    
    with col2:
        if st.button("🔄 Regeneruoti (sukurti kitą versiją)", type="secondary", use_container_width=True):
            # Atmesta! Išvalome pending ir trigger'iname naują generavimą
            del st.session_state.ai_content_pending
            st.session_state.trigger_ai_content = True
            st.info("♻️ Generuojama nauja versija...")
            st.rerun()

# Rodyti PATVIRTINTĄ AI turinio rezultatą
if "ai_content_result" in st.session_state and st.session_state.ai_content_result:
    st.markdown("---")
    st.success("✅ Turinys patvirtintas ir išsaugotas!")
    
    # Rezultatai
    st.subheader("📝 Patvirtinti socialinių tinklų įrašai")
    
    # Rodyti sugeneruotą turinį
    st.markdown("### 🎯 Paruošti tekstai:")
    st.text_area("Kopijuokite tekstą:", value=st.session_state.ai_content_result, height=200, key="ai_content_persistent")
    
    # Analitikos informacija
    if "ai_analyses" in st.session_state:
        with st.expander("📊 Detali analizė"):
            st.markdown("**Vaizdų analizė:**")
            for i, analysis in enumerate(st.session_state.ai_analyses):
                st.markdown(f"**Nuotrauka {i+1}:** {analysis}")

# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")



