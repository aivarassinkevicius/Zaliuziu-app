# Konsoliduoti importai
import streamlit as st
import io
import os
import random
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter

from until.export import resize_for_social
from until.layout import draw_text_auto
from until.templates import apply_template
from lib.image_utils import add_marketing_overlay, create_social_template, load_font


CAMERA_AVAILABLE = False

# AI išdėstymo generavimo funkcija

def ai_generate_layout(num_images, texts):
    """
    Naudoja OpenAI API, kad sugeneruotų nuotraukų ir tekstų išdėstymo parametrus.
    """
    prompt = (
        f"Sugenerok social media koliažo išdėstymo parametrus {num_images} nuotraukoms ir {len(texts)} tekstams. "
        "Atsakyk JSON formatu: nuotraukos: [{{x, y, w, h, rotation}}], tekstai: [{{x, y, size, font, color}}]. "
        "Stilius modernus, estetiškas, VISI elementai turi būti išdėstyti vizualiai BALANSUOTAI ir CENTRUOTI, kad nuotraukos ir tekstai nebūtų tik kairiame viršutiniame kampe. Naudok pilną drobės plotą, išdėstyk nuotraukas ir tekstus tvarkingai, kad atrodytų gražiai ir profesionaliai."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    import json
    try:
        layout = json.loads(response.choices[0].message.content)
    except Exception:
        # Fallback: estetiškas centrinis išdėstymas su padding ir automatinėmis spalvomis
        canvas_w, canvas_h = 1080, 1080
        padding = 80
        gap = 40
        img_size = int((canvas_w - 2*padding - (num_images-1)*gap) / max(num_images,1))
        layout = {"nuotraukos": [], "tekstai": []}
        # Išdėstome nuotraukas centre su tarpais
        for i in range(num_images):
            x = padding + i*(img_size + gap)
            y = int(canvas_h*0.22)
            layout["nuotraukos"].append({
                "x": x,
                "y": y,
                "w": img_size,
                "h": img_size,
                "rotation": random.randint(-5,5)
            })
        # Tekstus dedame po nuotraukomis, centre, su didesniu tarpu
        for i in range(len(texts)):
            # OpenAI API key check and fallback
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
            layout["tekstai"].append({
                "x": int(canvas_w * (0.25 + 0.5*i)),
                "y": int(canvas_h*0.22 + img_size + 60),
                "size": 54 if i == 0 else 40,
                "font": "DejaVuSans-Bold.ttf",
                "color": "#222222" if i == 0 else "#444444"
            })
    return layout

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
                if not client:
                    st.warning("🔒 OpenAI API raktas nerastas. Naudojamas automatinis išdėstymas.")
                    return {"nuotraukos": [], "tekstai": []}

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
            if not client:
                st.warning("🔒 OpenAI API raktas nerastas. Naudojamas automatinis produktų atpažinimas.")
                return "Nuotraukoje matosi žaliuzės arba roletai. Spalva: balta arba pilka. Kambarys: svetainė arba miegamasis."
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
            if not client:
                st.warning("🔒 OpenAI API raktas nerastas. Naudojami automatiniai tekstai.")
                return f"Pavasario gaivumas su mūsų žaliuzėmis! Šviesios spalvos, atsinaujinimas, nauji sprendimai. --- Jaukumas namuose su roletais. --- Linksmas tekstas apie žaliuzes ir sezoną."
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

# ========== MODERNUS SOCIAL TEMPLATE ========== #
from until.export import resize_for_social
from until.layout import draw_text_auto
from until.templates import apply_template

st.markdown("---")
st.header("🆕 Modernus Social Media Šablonas su AI išdėstymu")

uploaded_imgs = st.file_uploader("Įkelk nuotraukas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
input_text = st.text_input("Tekstas ant nuotraukos", "Žaliuzių akcija!")
extra_text = st.text_input("Papildomas tekstas (mažesnis)", "Akcija tik šią savaitę!")
social_format = st.selectbox("Formatas:", ["Instagram Square", "Instagram Story", "Facebook Post", "Pinterest Vertical"])
theme = st.selectbox("Tema:", ["Modern Dark", "Modern Blue", "Modern Red", "Modern Green", "Modern Gradient", "Winter", "Pastel"])
export_format = st.selectbox("Eksportuoti kaip:", ["PNG", "JPEG"], key="export_format_modern_ai")
font_path = st.text_input("Šrifto failas (pvz. Roboto-Bold.ttf)", "Roboto-Bold.ttf")

if uploaded_imgs:
    texts = [input_text]
    if extra_text:
        texts.append(extra_text)
    layout = ai_generate_layout(len(uploaded_imgs), texts)
    # Canvas pagal social formatą
    size_map = {"Instagram Square": (1080,1080), "Instagram Story": (1080,1920), "Facebook Post": (1200,628), "Pinterest Vertical": (1000,1500)}
    canvas_size = size_map.get(social_format, (1080,1080))
    canvas = Image.new("RGBA", canvas_size, (30,30,30,255))
    # Sudedam nuotraukas pagal AI
    for i, img_file in enumerate(uploaded_imgs):
        img = Image.open(img_file).convert("RGBA")
        params = layout["nuotraukos"][i]
        img = img.resize((params["w"], params["h"]), Image.LANCZOS)
        img = img.rotate(params["rotation"], expand=True)
        canvas.alpha_composite(img, (params["x"], params["y"]))
    # Uždedam teminį overlay
    palette = [(120,180,255), (255,255,255)]
    canvas = apply_template(canvas.convert("RGB"), palette, theme).convert("RGBA")
    # Sudedam tekstus pagal AI
    draw = ImageDraw.Draw(canvas)
    for i, txt in enumerate(texts):
        tparams = layout["tekstai"][i]
        try:
            font = ImageFont.truetype(get_font_path(), tparams["size"])
        except Exception:
            import os
            if os.name == "nt":  # Windows
                font_path = "C:/Windows/Fonts/arial.ttf"
            else:
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font = ImageFont.truetype(get_font_path(), tparams["size"])
        draw.text((tparams["x"], tparams["y"]), txt, font=font, fill=tparams["color"])
    st.image(canvas.convert("RGB"), caption="Modernus AI šablonas", use_container_width=True)
    buf = io.BytesIO()
    if export_format == "PNG":
        canvas.convert("RGB").save(buf, format="PNG")
    else:
        canvas.convert("RGB").save(buf, format="JPEG")
    st.download_button("Atsisiųsti šabloną", buf.getvalue(), file_name=f"modern_ai_template.{export_format.lower()}", mime=f"image/{export_format.lower()}")

# ---------- Pagrindinis UI ----------


add_watermark = False  # Numatytasis, kad nebūtų klaidos
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


# --- Helper: Clear all session keys ---
def clear_all():
    for key in ["uploaded_files", "manual_files", "camera_photos", "ai_content_result", "collage_result", "template_result", "collage_filename", "template_filename", "ai_analyses", "last_ai_settings", "trigger_ai_content", "trigger_ai_regenerate"]:
        if key in st.session_state:
            del st.session_state[key]

# --- Normalize uploaded files to BytesIO ---
def normalize_files(file_list):
    normalized = []
    for f in file_list:
        if hasattr(f, "read"):
            f.seek(0)
            data = f.read()
            bio = io.BytesIO(data)
            bio.name = getattr(f, "name", None)
            normalized.append(bio)
        elif isinstance(f, bytes):
            bio = io.BytesIO(f)
            normalized.append(bio)
        else:
            normalized.append(f)
    return normalized

# Mobilus failų valdymas
if uploaded_files:
    # Normalize all files to BytesIO for downstream processing
    normalized_files = normalize_files(uploaded_files)
    # Limit to 4 files
    if len(normalized_files) > 4:
        st.warning("⚠️ Per daug nuotraukų! Bus naudojamos tik pirmosios 4.")
        normalized_files = normalized_files[:4]
    st.session_state["uploaded_files"] = normalized_files
    st.success(f"🎉 **Iš viso pasirinkta: {len(normalized_files)} nuotraukų!**")
    # Rodyti preview
    cols = st.columns(len(normalized_files))
    for i, file in enumerate(normalized_files):
        with cols[i]:
            st.image(file, caption=f"#{i+1}", width=150)
elif "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

# Globalus išvalymo mygtukas
if st.session_state["uploaded_files"]:
    if st.button("🗑️ Išvalyti VISAS nuotraukas", type="secondary", key="clear_all"):
        clear_all()
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
                        
                        canvas_width = cols * img_size + (cols +  1) * gap
                       
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