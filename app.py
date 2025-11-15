import streamlit as st
import io, os, base64
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter

# Bandome importuoti camera input (jei neveiks, praleidžia)
try:
    from streamlit_camera_input_live import camera_input_live
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

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
    
    # Sezoninis ir šventinis kontekstas
    seasonal_tips = {
        "Pavasaris": "Šviesios spalvos, gaivumas, atsinaujinimas, pavasario šviesumas",
        "Vasara": "Apsauga nuo karščio, šviesus interjeras, vasaros saulė, energijos taupymas",
        "Ruduo": "Jaukumas, šilti tonai, rudeniškas komfortas, namų atmosfera",
        "Žiema": "Šilumos išsaugojimas, jaukumas, žiemos šviesa, energijos efektyvumas"
    }
    
    holiday_context = ""
    if holiday != "Nėra":
        holiday_context = f"\n🎉 ŠVENTĖ: {holiday} - PRIVALOMA įtraukti šventinę tematiką į VISUS 3 tekstus!"
    
    season_tip = seasonal_tips.get(season, "")
    
    prompt = f"""Tu esi PROFESIONALUS turinio kūrėjas žaliuzių ir roletų verslui.

📊 DETALI PRODUKTŲ ANALIZĖ:
{analysis_text}

🌍 KONTEKSTAS:
- Metų laikas: {season} ({season_tip})
{holiday_context}

🎯 UŽDUOTIS: Sukurk 3 SKIRTINGUS socialinių tinklų įrašų variantus (iki 280 simbolių kiekvienas):

---
**1) MARKETINGINIS** 💼
- Profesionalus, verslo tonas
- Pabrėžk KONKREČIŲ produktų PRIVALUMUS ir funkcijas
- Jei yra KELI produktai - paminėk VISUS pagal svarbą
- Naudok TIKSLIUS pavadinimus iš analizės (pvz: "Plisuotos žaliuzės", "Medinės venetian", "Roletai Diena-Naktis")
- Susieti su {season} sezonu ir jo specifika
{f"- BŪTINAI įtraukti {holiday} tematiką (dovanų idėjos, šventinis dekoras, spec. pasiūlymai)" if holiday != "Nėra" else ""}
- 2-3 tinkamus hashtag'us (#Žaliuzės, #{season}, etc.)

---
**2) DRAUGIŠKAS** 🏡
- Šiltas, artimas tonas - lyg kalbėtum su kaimynu
- Paaiškink kaip šie produktai pagerina kasdienį gyvenimą
- Paminėk KONKREČIUS produktus iš nuotraukų
- Praktinės naudos ({season} kontekste)
{f"- Natūraliai susieti su {holiday} - šeimos jaukumas, švenčių nuotaika" if holiday != "Nėra" else ""}
- 1-2 hashtag'us

---
**3) SU HUMORU** 😄
- Linksmas, įsimintinas, bet INFORMATYVUS
- Išlaikyk produktų tipus ir pavadinimus
- Žaismingas požiūris į {season} sezoną
{f"- {holiday} tematika su humoru (bet profesionaliai!)" if holiday != "Nėra" else ""}
- 2-3 hashtag'us su emoji

---

‼️ KRITIŠKAI SVARBU:
1. Jei analizėje minimi KELI SKIRTINGI produktai (pvz. "plisuotos žaliuzės", "medinės žaliuzės", "roletai") - PRIVALOMA paminėti VISUS
2. Naudok TIKSLIUS pavadinimus iš analizės (ne bendrinius)
3. {season} sezonas turi būti AIŠKIAI matomas KIEKVIENAME tekste
{f"4. {holiday} šventė PRIVALOMA KIEKVIENAME variante!" if holiday != "Nėra" else ""}
5. Kiekvienas variantas turi būti UNIKALUS ir SKIRTINGO stiliaus

Atskirk variantus su "---"
Rašyk LIETUVIŠKAI, natūraliai, profesionaliai.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu esi ekspertas kuriantis įtraukiantį turinį langų dekoravimo verslui Lietuvoje. Esi kūrybiškas, tikslus ir atsižvelgi į produktų specifiką bei sezonines tendencijas."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.85,
        max_tokens=1200
    )
    return response.choices[0].message.content.strip()

def image_to_base64(image_file):
    """Konvertuoja įkeltą failą į base64 be kompresijos"""
    image_file.seek(0)
    return base64.b64encode(image_file.read()).decode()

# ---------- Pagrindinis UI ----------
st.sidebar.header("⚙️ Nustatymai")

season = st.sidebar.selectbox(
    "🌤️ Metų laikas",
    ["Pavasaris", "Vasara", "Ruduo", "Žiema"],
    index=1
)

holiday = st.sidebar.selectbox(
    "🎉 Lietuviškos šventės (pasirinktinai)",
    ["Nėra", "Naujieji metai", "Šv. Valentino diena", "Vasario 16-oji", "Kovo 11-oji", 
     "Velykos", "Gegužės 1-oji (Darbo diena)", "Motinos diena", "Tėvo diena", 
     "Joninės", "Liepos 6-oji (Karaliaus Mindaugo diena)", "Žolinė", "Rugsėjo 1-oji", 
     "Šv. Kalėdos", "Kūčios"],
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
    st.session_state.trigger_ai_content = False  # Reset trigger
    progress_bar = st.progress(0)
    status_text = st.empty()
    
# Apdorojimas tik jei yra failų ir trigger'is aktyvuotas
if "trigger_ai_content" in st.session_state and st.session_state.trigger_ai_content and files_to_process and len(files_to_process) > 0:
    st.session_state.trigger_ai_content = False  # Reset trigger
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

elif create_content and (not files_to_process or len(files_to_process) == 0):
    st.warning("⚠️ Prašome pirmiausia įkelti bent vieną nuotrauką!")

# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")