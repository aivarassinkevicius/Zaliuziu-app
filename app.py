import streamlit as st
import io, os, base64, random
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageFilter, ImageOps

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
            {"role": "system", "content": """Tu esi langų uždangalų ir žaliuzių produktų atpažinimo specialistas. 
Tavo užduotis - TIKSLIAI identifikuoti produkto tipą lietuviškai."""},
            {"role": "user", "content": [
                {"type": "text", "text": """Išanalizuok šią nuotrauką ir BŪTINAI nurodyk:

1. **PRODUKTO TIPAS** (pasirink vieną iš šių):
   - Roletai (tekstiliniai, rule-up blinds)
   - Roletai Diena-Naktis (zebra blinds, dual blinds)
   - Horizontalios žaliuzės (horizontal blinds, venetian blinds)
   - Vertikalios žaliuzės (vertical blinds)
   - Plisuotos žaliuzės (pleated blinds)
   - Romanetės (roman shades)
   - Lamelės (panel blinds, vertical panel track)
   - Užuolaidos
   - Kita (nurodyk kas)

2. **SPALVA IR MEDŽIAGA**: kokios spalvos, ar matinė, skaidri, tamsinanti

3. **APLINKA**: koks kambarys, apšvietimas, interjero stilius

4. **DETALĖS**: kas dar įdomaus - langas, vaizdas, dekoro elementai

BŪTINAI pradėk nuo produkto tipo, pvz: "Matosi ROLETAI DIENA-NAKTIS..." arba "Nuotraukoje - VERTIKALIOS ŽALIUZĖS..." """},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_bytes}}
            ]}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

def generate_captions(analysis_text, season, holiday):
    """Sukuria 3 teksto variantus lietuviškai pagal tikslią produkto analizę"""
    holiday_context = f" ir šventę: {holiday}" if holiday != "Nėra" else ""
    prompt = f"""
Pagal šią TIKSLIĄ produkto analizę:
{analysis_text}

Metų laikas: {season}{holiday_context}

Sukurk 3 įvairius socialinių tinklų įrašų variantus (iki 250 simbolių kiekvienas) apie šį KONKRETŲ produktą:

1) **MARKETINGINIS**: Profesionalus, pabrėžk produkto naudą ir savybes. Naudok TIKSLŲ produkto pavadinimą iš analizės.

2) **DRAUGIŠKAS**: Šiltas, artimas, kaip kalbėtum su kaimynu. Paaiškink kaip šis produktas pagerina gyvenimą.

3) **SU HUMORU**: Linksmas, kreatyvus, bet vis tiek informatyvus apie produktą.

SVARBU:
- Naudok TIKSLŲ produkto pavadinimą (pvz. "Roletai Diena-Naktis", ne tiesiog "roletai")
- Pridėk 1-2 tinkamus #hashtag'us
- Jei yra spalvų/medžiagos info - panaudok
{f"- Įtraukk šventės {holiday} tematiką natūraliai" if holiday != "Nėra" else ""}

Atskirk variantus su "---"
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=800
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
            
            # Redaguojame nuotrauką
            edited = add_marketing_overlay(
                file,
                add_watermark=add_watermark,
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
    
    # === AI TURINIO GENERAVIMAS ===
    st.markdown("---")
    st.markdown("### 🤖 AI Turinio Generavimas")
    st.caption("Sukurkite automatinį aprašymą pagal nuotraukas")
    
    if st.button("🚀 Generuoti AI Turinį", type="primary", use_container_width=True):
        with st.spinner("🤖 AI analizuoja nuotraukas ir kuria tekstą..."):
            try:
                all_analyses = []
                
                # Analizuojame kiekvieną nuotrauką
                for i, file in enumerate(files_to_process):
                    file.seek(0)
                    image_b64 = image_to_base64(file)
                    analysis = analyze_image(image_b64)
                    all_analyses.append(analysis)
                
                # Sujungiame analizes
                combined_analysis = " ".join(all_analyses)
                
                # Generuojame tekstą
                captions = generate_captions(combined_analysis, season, holiday)
                
                # Išsaugome į session state
                st.session_state['ai_captions'] = captions
                st.session_state['ai_analyses'] = all_analyses
                
                st.success("✅ AI turinys sukurtas!")
                
            except Exception as e:
                st.error(f"❌ Klaida: {str(e)}")
    
    # Rodyti AI turinį jei sukurtas
    if 'ai_captions' in st.session_state and st.session_state['ai_captions']:
        st.markdown("### 📝 Sugeneruotas tekstas:")
        st.text_area("AI Tekstas:", value=st.session_state['ai_captions'], height=200, key="ai_text_display")
        
        with st.expander("📊 Nuotraukų analizė"):
            for i, analysis in enumerate(st.session_state['ai_analyses']):
                st.markdown(f"**Nuotrauka {i+1}:** {analysis}")
        
        # === GALUTINIO POSTO GENERAVIMAS ===
        st.markdown("---")
        st.markdown("### 🎨 Gatavo Instagram Posto Generatorius")
        st.info("📱 Sukurkite gatavą 1080x1080 Instagram postą su nuotrauka ir tekstu!")
        
        # Pasirinkimai
        col1, col2 = st.columns(2)
        with col1:
            which_image = st.selectbox(
                "🖼️ Nuotrauka:",
                [f"Nuotrauka {i+1}" for i in range(len(files_to_process))],
                help="Pasirinkite kurią nuotrauką naudoti fone"
            )
        
        with col2:
            # Padalijame AI tekstą į variantus
            text_variants = st.session_state['ai_captions'].split("---")
            text_options = ["Visas tekstas"] + [f"Variantas {i+1}" for i in range(len(text_variants))]
            which_text = st.selectbox(
                "📝 Tekstas:",
                text_options,
                help="Pasirinkite kurį teksto variantą naudoti"
            )
        
        col3, col4, col5 = st.columns(3)
        with col3:
            text_position = st.selectbox(
                "📍 Teksto pozicija:",
                ["Apačia", "Viršus", "Centras", "Kairė apačia", "Dešinė apačia"],
                help="Kur bus tekstas ant nuotraukos"
            )
        
        with col4:
            text_size = st.slider("📏 Teksto dydis:", 20, 80, 40, 5)
        
        with col5:
            text_bg_opacity = st.slider("🔳 Fono tamsa:", 0, 255, 150, 10, help="0=permatomas, 255=juodas")
        
        if st.button("✨ SUKURTI GATAVĄ POSTĄ", type="primary", use_container_width=True):
            with st.spinner("🎨 Kuriamas gatavs Instagram postas..."):
                try:
                    # Pasirenkame nuotrauką
                    img_index = int(which_image.split()[1]) - 1
                    selected_file = files_to_process[img_index]
                    selected_file.seek(0)
                    
                    # Redaguojame nuotrauką
                    edited = add_marketing_overlay(
                        selected_file,
                        add_watermark=False,  # Vandens ženklą pridėsime atskirai
                        add_border=False,
                        brightness=brightness,
                        contrast=contrast,
                        saturation=saturation,
                        watermark_text="",
                        watermark_size=watermark_size
                    )
                    edited.seek(0)
                    base_image = Image.open(edited)
                    
                    # Resize į Instagram formatą
                    canvas_size = 1080
                    base_image = base_image.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
                    
                    # Sukuriame canvas
                    canvas = Image.new('RGB', (canvas_size, canvas_size))
                    canvas.paste(base_image, (0, 0))
                    
                    # Pasiruošiame tekstą
                    if which_text == "Visas tekstas":
                        final_text = st.session_state['ai_captions']
                    else:
                        variant_index = int(which_text.split()[1]) - 1
                        final_text = text_variants[variant_index].strip() if variant_index < len(text_variants) else st.session_state['ai_captions']
                    
                    # Išvalome teksto formatavimą
                    import re
                    final_text = re.sub(r'VARIANTAS\s+\d+\s*[-:]*\s*', '', final_text, flags=re.IGNORECASE)
                    final_text = re.sub(r'^\d+[\.\)]\s*', '', final_text, flags=re.MULTILINE)
                    final_text = re.sub(r'(MARKETINGINIS|DRAUGIŠKAS|DRAUGI[ŠS]KAS|SU HUMORU)\s*[💼🏡😄🎭]*\s*[-:]*\s*', '', final_text, flags=re.IGNORECASE)
                    final_text = final_text.strip()
                    
                    # Pridedame tekstą ant nuotraukos
                    canvas = canvas.convert('RGBA')
                    text_layer = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(text_layer)
                    
                    # Įkeliame šriftą
                    font = None
                    font_paths = [
                        "C:/Windows/Fonts/arialbd.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        "/System/Library/Fonts/Helvetica.ttc"
                    ]
                    for path in font_paths:
                        try:
                            font = ImageFont.truetype(path, text_size)
                            break
                        except:
                            continue
                    
                    if not font:
                        font = ImageFont.load_default()
                    
                    # Word wrap
                    margin = 60
                    max_width = canvas_size - (margin * 2)
                    
                    words = final_text.split()
                    lines = []
                    current_line = []
                    
                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        bbox = draw.textbbox((0, 0), test_line, font=font)
                        if bbox[2] - bbox[0] <= max_width:
                            current_line.append(word)
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [word]
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    # Skaičiuojame teksto bloko dydį
                    line_height = text_size + 10
                    total_height = len(lines) * line_height + margin
                    
                    # Nustatome poziciją
                    if "Apačia" in text_position or "apačia" in text_position.lower():
                        text_y = canvas_size - total_height - margin
                    elif "Viršus" in text_position or "viršus" in text_position.lower():
                        text_y = margin
                    else:  # Centras
                        text_y = (canvas_size - total_height) // 2
                    
                    # Pridedame pusskaidrų foną tekstui
                    bg_overlay = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
                    bg_draw = ImageDraw.Draw(bg_overlay)
                    bg_draw.rectangle(
                        [(margin // 2, text_y - 20), (canvas_size - margin // 2, text_y + total_height + 20)],
                        fill=(0, 0, 0, text_bg_opacity)
                    )
                    canvas = Image.alpha_composite(canvas, bg_overlay)
                    
                    # Piešiame tekstą
                    draw = ImageDraw.Draw(canvas)
                    current_y = text_y
                    
                    for line in lines:
                        # Centruojame tekstą
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                        text_x = (canvas_size - line_width) // 2
                        
                        # Šešėlis
                        draw.text((text_x + 2, current_y + 2), line, fill=(0, 0, 0), font=font)
                        # Tekstas
                        draw.text((text_x, current_y), line, fill=(255, 255, 255), font=font)
                        
                        current_y += line_height
                    
                    # Pridedame vandens ženklą jei reikia
                    if add_watermark and watermark_text:
                        wm_font = None
                        for path in font_paths:
                            try:
                                wm_font = ImageFont.truetype(path, watermark_size // 3)
                                break
                            except:
                                continue
                        
                        if wm_font:
                            wm_bbox = draw.textbbox((0, 0), watermark_text, font=wm_font)
                            wm_width = wm_bbox[2] - wm_bbox[0]
                            wm_x = canvas_size - wm_width - 30
                            wm_y = canvas_size - 60
                            
                            draw.text((wm_x + 2, wm_y + 2), watermark_text, fill=(0, 0, 0, 180), font=wm_font)
                            draw.text((wm_x, wm_y), watermark_text, fill=(255, 255, 255), font=wm_font)
                    
                    # Konvertuojame į RGB
                    canvas = canvas.convert('RGB')
                    
                    # Išsaugome
                    final_bytes = io.BytesIO()
                    canvas.save(final_bytes, format='JPEG', quality=95)
                    final_bytes.seek(0)
                    
                    st.session_state['final_post'] = final_bytes.getvalue()
                    st.success("✅ Gatavs Instagram postas sukurtas!")
                    
                except Exception as e:
                    st.error(f"❌ Klaida: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        
        # Rodyti gatavą postą
        if 'final_post' in st.session_state:
            st.markdown("---")
            st.markdown("### 🎉 JŪSŲ GATAVS INSTAGRAM POSTAS")
            st.image(st.session_state['final_post'], caption="Gatavs postas - Instagram 1080x1080", use_container_width=True)
            
            st.download_button(
                label="📥 ATSISIŲSTI GATAVĄ POSTĄ",
                data=st.session_state['final_post'],
                file_name=f"instagram_post_{season}_{holiday}.jpg",
                mime="image/jpeg",
                use_container_width=True,
                type="primary"
            )
            
            st.success("🎯 Dabar tiesiog įkelkite šį failą į Instagram/Facebook!")
    
    # SOCIAL MEDIA ŠABLONAS (SENASIS - su koliažu)
    st.markdown("---")
    st.markdown("### 📱 Social Media Šablonas")
    st.caption("Panaudokite sukurtą koliažą ant teminio fono paveikslėlio")
    
    # Automatiškai nustatome temą
    if holiday != "Nėra":
        auto_theme = f"🎉 Šventinė: {holiday}"
    else:
        auto_theme = f"🍂 Sezoninė: {season}"
    
    st.info(f"✨ Automatinė tema: **{auto_theme}** (pagal jūsų nustatymus kairėje)")
    
    # Tikriname ar yra sukurtas koliažas
    if 'created_collage' in st.session_state and st.session_state['created_collage'] is not None:
        
        st.success("✅ Koliažas rastas! Dabar galite jį uždėti ant tematinio fono.")
        
        # Fono stilius
        bg_style = st.selectbox(
            "🎨 Fono stilius:",
            ["Automatinis (pagal sezoną)", "Gamta", "Ofisas", "Interjeras", "Abstraktus", "Minimalus"],
            help="Pasirinkite fono tematiką"
        )
        
        if st.button("✨ Sukurti Social Media Šabloną su Koliažu", type="primary", use_container_width=True):
            with st.spinner("🎨 Kuriamas social media šablonas su koliažu..."):
                try:
                    # Naudojame jau sukurtą koliažą iš session_state
                    collage_image = st.session_state['created_collage']
                    
                    # === FONO GENERAVIMAS SU VIZUALIAIS ELEMENTAIS ===
                    canvas_width = 1080  # Instagram standartinis
                    canvas_height = 1080
                    if bg_style == "Automatinis (pagal sezoną)" or bg_style == "Gamta":
                        if holiday != "Nėra":
                            # Šventiniai fonai su objektais
                            if "Kalėdos" in holiday:
                                bg_colors = [(25, 60, 40), (40, 80, 60), (20, 50, 35)]
                                objects_type = "christmas"  # Eglutės, snaigės
                            elif "Velykos" in holiday:
                                bg_colors = [(255, 250, 235), (250, 245, 225), (245, 240, 220)]
                                objects_type = "easter"  # Gėlės, kiaušiniai
                            elif "Valentino" in holiday:
                                bg_colors = [(255, 235, 240), (250, 220, 230), (245, 210, 220)]
                                objects_type = "hearts"  # Širdys
                            elif "Naujieji" in holiday:
                                bg_colors = [(25, 25, 45), (35, 35, 60), (20, 20, 40)]
                                objects_type = "fireworks"  # Fejerverkai (žvaigždės)
                            else:
                                bg_colors = [(240, 240, 245), (235, 235, 240), (230, 230, 235)]
                                objects_type = "abstract"
                        else:
                            # Sezoniniai fonai su objektais
                            if season == "Pavasaris":
                                bg_colors = [(230, 245, 220), (220, 240, 210), (210, 235, 200)]
                                objects_type = "spring"  # Gėlės, lapai
                            elif season == "Vasara":
                                bg_colors = [(255, 245, 200), (250, 240, 190), (245, 235, 180)]
                                objects_type = "summer"  # Saulės, bangos
                            elif season == "Ruduo":
                                bg_colors = [(240, 220, 190), (235, 210, 180), (230, 200, 170)]
                                objects_type = "autumn"  # Lapai
                            else:  # Žiema
                                bg_colors = [(230, 240, 250), (220, 235, 245), (210, 230, 240)]
                                objects_type = "winter"  # Snaigės
                    
                    elif bg_style == "Ofisas":
                        bg_colors = [(245, 245, 245), (235, 235, 240), (225, 230, 235)]
                        objects_type = "office"  # Geometrinės formos
                    
                    elif bg_style == "Interjeras":
                        bg_colors = [(250, 245, 240), (245, 240, 235), (240, 235, 230)]
                        objects_type = "interior"  # Augalų siluetai
                    
                    elif bg_style == "Abstraktus":
                        bg_colors = [(240, 230, 250), (230, 240, 255), (250, 240, 230)]
                        objects_type = "abstract"  # Abstrakčios formos
                    
                    else:  # Minimalus
                        bg_colors = [(255, 255, 255), (250, 250, 250), (245, 245, 245)]
                        objects_type = "minimal"  # Taškai
                    
                    # Sukuriame gradientinį foną
                    background = Image.new('RGB', (canvas_width, canvas_height))
                    draw = ImageDraw.Draw(background)
                    
                    # Gradientas
                    for y in range(canvas_height):
                        ratio = y / canvas_height
                        if ratio < 0.5:
                            local_ratio = ratio * 2
                            r = int(bg_colors[0][0] + (bg_colors[1][0] - bg_colors[0][0]) * local_ratio)
                            g = int(bg_colors[0][1] + (bg_colors[1][1] - bg_colors[0][1]) * local_ratio)
                            b = int(bg_colors[0][2] + (bg_colors[1][2] - bg_colors[0][2]) * local_ratio)
                        else:
                            local_ratio = (ratio - 0.5) * 2
                            r = int(bg_colors[1][0] + (bg_colors[2][0] - bg_colors[1][0]) * local_ratio)
                            g = int(bg_colors[1][1] + (bg_colors[2][1] - bg_colors[1][1]) * local_ratio)
                            b = int(bg_colors[1][2] + (bg_colors[2][2] - bg_colors[1][2]) * local_ratio)
                        draw.line([(0, y), (canvas_width, y)], fill=(r, g, b))
                    
                    # === GENERUOJAME VIZUALINIUS OBJEKTUS ===
                    background = background.convert('RGBA')
                    objects_layer = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                    obj_draw = ImageDraw.Draw(objects_layer)
                    
                    # Funkcija generuoti objektus pagal tipą
                    def draw_decorative_objects(draw_obj, obj_type, colors, width, height):
                        """Piešia dekoratyvinius objektus fone"""
                        
                        if obj_type == "christmas":
                            # Eglutės ir snaigės (RYŠKESNI)
                            for _ in range(15):
                                x = random.randint(0, width - 200)
                                y = random.randint(0, height - 250)
                                # Eglutė (trikampis)
                                size = random.randint(120, 200)
                                points = [(x + size//2, y), (x, y + size), (x + size, y + size)]
                                draw_obj.polygon(points, fill=(40, 90, 60, 150))
                            
                            # Snaigės
                            for _ in range(40):
                                x = random.randint(0, width)
                                y = random.randint(0, height)
                                size = random.randint(40, 100)
                                # 6-kampė snaigė (supaprastinta)
                                draw_obj.ellipse([x, y, x+size, y+size], fill=(255, 255, 255, 120))
                                draw_obj.line([(x, y+size//2), (x+size, y+size//2)], fill=(255, 255, 255, 180), width=4)
                                draw_obj.line([(x+size//2, y), (x+size//2, y+size)], fill=(255, 255, 255, 180), width=4)
                        
                        elif obj_type == "easter":
                            # Gėlės (paprastos) RYŠKESNĖS
                            for _ in range(25):
                                x = random.randint(0, width - 150)
                                y = random.randint(0, height - 150)
                                size = random.randint(60, 120)
                                # Gėlės žiedlapiai (5 apskritimai)
                                petal_color = random.choice([(255, 200, 220, 150), (255, 240, 200, 150), (200, 220, 255, 150)])
                                for angle in range(0, 360, 72):  # 5 žiedlapiai
                                    import math
                                    px = x + size//2 + int(size * 0.4 * math.cos(math.radians(angle)))
                                    py = y + size//2 + int(size * 0.4 * math.sin(math.radians(angle)))
                                    draw_obj.ellipse([px, py, px+size//2, py+size//2], fill=petal_color)
                                # Centras
                                draw_obj.ellipse([x+size//3, y+size//3, x+2*size//3, y+2*size//3], fill=(255, 220, 100, 180))
                        
                        elif obj_type == "hearts":
                            # Širdys (supaprastintos apskritimai) RYŠKESNĖS
                            for _ in range(20):
                                x = random.randint(0, width - 120)
                                y = random.randint(0, height - 120)
                                size = random.randint(60, 130)
                                draw_obj.ellipse([x, y, x+size, y+size], fill=(255, 150, 180, 140))
                        
                        elif obj_type == "spring":
                            # Gėlių žiedlapiai ir lapai RYŠKESNI
                            for _ in range(35):
                                x = random.randint(0, width - 120)
                                y = random.randint(0, height - 150)
                                size = random.randint(50, 100)
                                # Lapai (elipsės)
                                draw_obj.ellipse([x, y, x+size, y+size*2], fill=(120, 200, 120, 140))
                        
                        elif obj_type == "summer":
                            # Saulės spinduliai ir bangos RYŠKESNI
                            for _ in range(25):
                                x = random.randint(0, width - 150)
                                y = random.randint(0, height - 150)
                                size = random.randint(70, 150)
                                # Saulė (apskritimas)
                                draw_obj.ellipse([x, y, x+size, y+size], fill=(255, 200, 50, 130))
                                # Spinduliai
                                for angle in range(0, 360, 45):
                                    import math
                                    x2 = x + size//2 + int(size * math.cos(math.radians(angle)))
                                    y2 = y + size//2 + int(size * math.sin(math.radians(angle)))
                                    draw_obj.line([(x+size//2, y+size//2), (x2, y2)], fill=(255, 220, 100, 120), width=6)
                        
                        elif obj_type == "autumn":
                            # Lapai (įvairių formų) RYŠKESNI
                            for _ in range(45):
                                x = random.randint(0, width - 100)
                                y = random.randint(0, height - 100)
                                size = random.randint(60, 120)
                                rotation = random.randint(0, 360)
                                leaf_color = random.choice([(200, 100, 50, 150), (220, 150, 50, 150), (180, 80, 40, 150)])
                                # Lapas (elipsė pasukta)
                                draw_obj.ellipse([x, y, x+size, y+size//2], fill=leaf_color)
                        
                        elif obj_type == "winter":
                            # Snaigės RYŠKESNĖS
                            for _ in range(50):
                                x = random.randint(0, width)
                                y = random.randint(0, height)
                                size = random.randint(30, 80)
                                # Snaigė (žvaigždė)
                                draw_obj.ellipse([x, y, x+size, y+size], fill=(200, 220, 255, 130))
                                # Kryžius
                                draw_obj.line([(x, y+size//2), (x+size, y+size//2)], fill=(255, 255, 255, 170), width=3)
                                draw_obj.line([(x+size//2, y), (x+size//2, y+size)], fill=(255, 255, 255, 170), width=3)
                        
                        elif obj_type == "office":
                            # Geometrinės formos (kvadratai, stačiakampiai) RYŠKESNĖS
                            for _ in range(25):
                                x = random.randint(0, width - 200)
                                y = random.randint(0, height - 200)
                                w = random.randint(80, 180)
                                h = random.randint(80, 180)
                                shape_color = random.choice([(200, 200, 210, 120), (180, 180, 200, 120)])
                                draw_obj.rectangle([x, y, x+w, y+h], fill=shape_color)
                        
                        elif obj_type == "interior":
                            # Augalų siluetai (paprasti) RYŠKESNI
                            for _ in range(15):
                                x = random.randint(0, width - 150)
                                y = random.randint(height//2, height - 200)
                                height_plant = random.randint(120, 250)
                                # Vazonas
                                draw_obj.rectangle([x, y+height_plant-40, x+80, y+height_plant], fill=(180, 160, 140, 140))
                                # Stiebas
                                draw_obj.rectangle([x+32, y, x+48, y+height_plant-40], fill=(100, 150, 100, 140))
                                # Lapai
                                for i in range(6):
                                    ly = y + i * height_plant // 7
                                    draw_obj.ellipse([x+10, ly, x+40, ly+40], fill=(120, 180, 120, 150))
                                    draw_obj.ellipse([x+40, ly, x+70, ly+40], fill=(120, 180, 120, 150))
                        
                        elif obj_type == "abstract":
                            # Abstrakčios formos (apskritimai, bangos) RYŠKESNĖS
                            for _ in range(35):
                                x = random.randint(0, width - 150)
                                y = random.randint(0, height - 150)
                                size = random.randint(70, 180)
                                shape_type = random.choice(['circle', 'wave'])
                                color = random.choice([(200, 180, 220, 120), (180, 200, 240, 120), (240, 200, 180, 120)])
                                
                                if shape_type == 'circle':
                                    draw_obj.ellipse([x, y, x+size, y+size], fill=color)
                                else:
                                    # Banga (keli apskritimai)
                                    for i in range(4):
                                        draw_obj.ellipse([x+i*40, y, x+i*40+50, y+50], fill=color)
                        
                        elif obj_type == "fireworks":
                            # Fejerverkai (žvaigždės) RYŠKESNI
                            for _ in range(20):
                                x = random.randint(100, width - 100)
                                y = random.randint(100, height - 100)
                                size = random.randint(80, 150)
                                star_color = random.choice([(255, 215, 0, 150), (255, 100, 150, 150), (100, 200, 255, 150)])
                                # Žvaigždė (8 spinduliai)
                                import math
                                for angle in range(0, 360, 45):
                                    x2 = x + int(size * math.cos(math.radians(angle)))
                                    y2 = y + int(size * math.sin(math.radians(angle)))
                                    draw_obj.line([(x, y), (x2, y2)], fill=star_color, width=7)
                                draw_obj.ellipse([x-20, y-20, x+20, y+20], fill=star_color)
                        
                        else:  # minimal
                            # Subtilūs taškai (bet DAUGIAU)
                            for _ in range(100):
                                x = random.randint(0, width)
                                y = random.randint(0, height)
                                size = random.randint(5, 15)
                                draw_obj.ellipse([x, y, x+size, y+size], fill=(200, 200, 200, 80))
                    
                    # Generuojame objektus
                    import math  # Reikalingas kai kuriems objektams
                    draw_decorative_objects(obj_draw, objects_type, bg_colors, canvas_width, canvas_height)
                    
                    # Sujungiame foną su objektais
                    background = Image.alpha_composite(background, objects_layer)
                    background = background.convert('RGB')
                    
                    # === KOLIAŽO UŽDĖJIMAS ANT FONO ===
                    # Naudojame jau sukurtą koliažą (mažesnis, kad matytųsi fonas)
                    collage_max_width = int(canvas_width * 0.50)  # 50% ekrano
                    collage_max_height = int(canvas_height * 0.50)
                    
                    # Resize koliažo išlaikant proportions
                    collage_w, collage_h = collage_image.size
                    aspect_ratio = collage_w / collage_h
                    
                    if collage_w > collage_max_width or collage_h > collage_max_height:
                        if aspect_ratio > 1:  # Platesnis
                            new_w = collage_max_width
                            new_h = int(new_w / aspect_ratio)
                        else:  # Aukštesnis
                            new_h = collage_max_height
                            new_w = int(new_h * aspect_ratio)
                        collage_resized = collage_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    else:
                        collage_resized = collage_image
                    
                    # Pridedame baltą rėmelį
                    border_width = 15
                    collage_with_border = ImageOps.expand(collage_resized, border=border_width, fill='white')
                    
                    # Pridedame šešėlį
                    shadow_offset = 20
                    shadow_blur = 30
                    collage_w, collage_h = collage_with_border.size
                    
                    shadow = Image.new('RGBA', (collage_w + shadow_offset * 2, collage_h + shadow_offset * 2), (0, 0, 0, 0))
                    shadow_draw = ImageDraw.Draw(shadow)
                    shadow_draw.rectangle([shadow_offset, shadow_offset, collage_w + shadow_offset, collage_h + shadow_offset], fill=(0, 0, 0, 100))
                    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
                    
                    # Centruojame koliažą
                    collage_x = (canvas_width - collage_w) // 2
                    collage_y = (canvas_height - collage_h) // 2
                    
                    # Paste šešėlį
                    background = background.convert('RGBA')
                    background.paste(shadow, (collage_x - shadow_offset, collage_y - shadow_offset), shadow)
                    background = background.convert('RGB')
                    
                    # Paste koliažą
                    background.paste(collage_with_border, (collage_x, collage_y))
                    
                    # === DEKORACIJOS ===
                    # Pridedame subtilias dekoracijas kampuose (emoji arba shapes)
                    if holiday != "Nėra":
                        if "Kalėdos" in holiday:
                            decorations = ["❄️", "🎄", "⭐"]
                        elif "Velykos" in holiday:
                            decorations = ["🌸", "🐰", "🥚"]
                        elif "Valentino" in holiday:
                            decorations = ["❤️", "💕", "🌹"]
                        elif "Naujieji" in holiday:
                            decorations = ["✨", "🎆", "🎉"]
                        else:
                            decorations = ["✨", "🎈"]
                    else:
                        if season == "Pavasaris":
                            decorations = ["🌸", "🦋", "🌱"]
                        elif season == "Vasara":
                            decorations = ["☀️", "🌻", "🍋"]
                        elif season == "Ruduo":
                            decorations = ["🍂", "🍁", "🎃"]
                        else:
                            decorations = ["❄️", "⛄", "☃️"]
                    
                    # Dedame dekoracijas kampuose (subtiliai)
                    try:
                        emoji_font = None
                        emoji_paths = [
                            "C:/Windows/Fonts/seguiemj.ttf",
                            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                            "/System/Library/Fonts/Apple Color Emoji.ttc"
                        ]
                        
                        for path in emoji_paths:
                            try:
                                emoji_font = ImageFont.truetype(path, 40)
                                break
                            except:
                                continue
                        
                        if emoji_font:
                            background = background.convert('RGBA')
                            emoji_layer = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                            emoji_draw = ImageDraw.Draw(emoji_layer)
                            
                            # Kampų dekoracijos (8 vnt)
                            positions = [
                                (30, 30), (canvas_width - 70, 30),  # Top corners
                                (30, canvas_height - 70), (canvas_width - 70, canvas_height - 70),  # Bottom corners
                                (30, canvas_height // 2 - 20), (canvas_width - 70, canvas_height // 2 - 20),  # Middle sides
                                (canvas_width // 2 - 20, 30), (canvas_width // 2 - 20, canvas_height - 70)  # Middle top/bottom
                            ]
                            
                            for pos in positions:
                                emoji = random.choice(decorations)
                                emoji_draw.text(pos, emoji, font=emoji_font, embedded_color=True)
                            
                            background = Image.alpha_composite(background, emoji_layer)
                            background = background.convert('RGB')
                    except:
                        pass
                    
                    # Išsaugome
                    template_bytes = io.BytesIO()
                    background.save(template_bytes, format='JPEG', quality=95)
                    template_bytes.seek(0)
                    
                    st.success("✅ Social Media šablonas sukurtas!")
                    st.image(template_bytes, caption="Jūsų Social Media įrašas", use_container_width=True)
                    
                    template_bytes.seek(0)
                    st.download_button(
                        label="📥 Atsisiųsti šabloną",
                        data=template_bytes.getvalue(),
                        file_name=f"social_media_{season}_{holiday}.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Klaida kuriant šabloną: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    else:
        st.warning("⚠️ Pirmiausia sukurkite koliažą apačioje ⬇️, tada galėsite jį naudoti šablone!")
    
    # COLLAGE KŪRIMAS (ORIGINALUS)
    st.markdown("---")
    st.markdown("### 🖼️ Collage Kūrėjas")
    
    # Automatiškai nustatome temą pagal sezoną/šventę
    if holiday != "Nėra":
        auto_theme = f"🎉 Šventinė: {holiday}"
    else:
        auto_theme = f"🍂 Sezoninė: {season}"
    
    st.info(f"✨ Automatinė tema: **{auto_theme}** (pagal jūsų nustatymus kairėje)")
    
    if len(files_to_process) >= 2:
        collage_layout = st.selectbox(
            "📐 Išdėstymas:",
            ["2x2 Grid (4 nuotraukos)", "1x2 Horizontal (2 nuotraukos)", "2x1 Vertical (2 nuotraukos)", "1x3 Horizontal (3 nuotraukos)"],
            help="Pasirinkite kaip išdėstyti nuotraukas"
        )
        
        if st.button("🎨 Sukurti Collage", type="primary", use_container_width=True):
            with st.spinner("🖼️ Kuriamas tematinis collage..."):
                try:
                    # Paruošiame redaguotas nuotraukas
                    edited_images = []
                    for file in files_to_process:
                        file.seek(0)
                        edited = add_marketing_overlay(
                            file,
                            add_watermark=add_watermark,
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
                    
                    # Apkarpome jei per daug
                    edited_images = edited_images[:needed]
                    
                    # Jei per mažai - dubliuojame
                    while len(edited_images) < needed:
                        edited_images.append(edited_images[-1])
                    
                    # Nustatome collage dydį
                    img_width = 800
                    img_height = 600
                    
                    # Resize'iname visas nuotraukas
                    resized = []
                    for img in edited_images:
                        img_resized = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
                        resized.append(img_resized)
                    
                    # AUTOMATIŠKAI nustatome fono spalvą ir dekoracijų tipą pagal sezoną/šventę
                    decorations = []
                    
                    if holiday != "Nėra":
                        # ŠVENTINĖS TEMOS
                        if "Kalėdos" in holiday:
                            bg_color = (20, 50, 30)  # Tamsiai žalia
                            decorations = ["❄️", "🎄", "⭐", "🎅", "🎁"]
                            decoration_color = (255, 255, 255)
                        elif "Velykos" in holiday:
                            bg_color = (255, 250, 230)  # Šviesi pastelinė
                            decorations = ["🐰", "🥚", "🌷", "🌸", "🦋"]
                            decoration_color = (150, 100, 200)
                        elif "Valentino" in holiday:
                            bg_color = (255, 240, 245)  # Švelniai rožinė
                            decorations = ["❤️", "💕", "🌹", "💐"]
                            decoration_color = (200, 50, 100)
                        elif "Naujieji" in holiday:
                            bg_color = (30, 30, 50)  # Tamsiai mėlyna
                            decorations = ["🎆", "🎊", "🥂", "✨", "🎉"]
                            decoration_color = (255, 215, 0)
                        else:
                            bg_color = (250, 245, 250)
                            decorations = ["🎉", "✨", "🎈"]
                            decoration_color = (200, 150, 200)
                    else:
                        # SEZONINĖS TEMOS
                        if season == "Pavasaris":
                            bg_color = (245, 255, 245)  # Šviesiai žalia
                            decorations = ["🌸", "🌷", "🌼", "🦋", "🌱"]
                            decoration_color = (100, 180, 100)
                        elif season == "Vasara":
                            bg_color = (255, 250, 220)  # Šilta geltona
                            decorations = ["☀️", "🌻", "🌺", "🦜", "🍋"]
                            decoration_color = (255, 180, 50)
                        elif season == "Ruduo":
                            bg_color = (255, 240, 220)  # Švelni oranžinė
                            decorations = ["🍂", "🍁", "🎃", "🌾", "🦊"]
                            decoration_color = (180, 100, 50)
                        else:  # Žiema
                            bg_color = (240, 245, 255)  # Šaltas mėlynas
                            decorations = ["❄️", "⛄", "🎿", "☃️", "🌨️"]
                            decoration_color = (100, 150, 200)
                    
                    # Sukuriame collage
                    gap = 20
                    canvas_width = cols * img_width + (cols + 1) * gap
                    canvas_height = rows * img_height + (rows + 1) * gap
                    
                    collage = Image.new('RGB', (canvas_width, canvas_height), bg_color)
                    draw = ImageDraw.Draw(collage)
                    
                    # Dedame nuotraukas
                    idx = 0
                    for row in range(rows):
                        for col in range(cols):
                            if idx < len(resized):
                                x = gap + col * (img_width + gap)
                                y = gap + row * (img_height + gap)
                                collage.paste(resized[idx], (x, y))
                                idx += 1
                    
                    # PRIDEDAME DEKORACIJAS (emoji) po nuotraukomis
                    if decorations:
                        try:
                            # Bandome įkelti emoji palaikantį šriftą
                            emoji_font = None
                            emoji_paths = [
                                "C:/Windows/Fonts/seguiemj.ttf",  # Windows Emoji
                                "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",  # Linux
                                "/System/Library/Fonts/Apple Color Emoji.ttc"  # Mac
                            ]
                            
                            for path in emoji_paths:
                                try:
                                    emoji_font = ImageFont.truetype(path, 60)
                                    break
                                except:
                                    continue
                            
                            if emoji_font:
                                # Atsitiktinai išdėstome dekoracijas kampuose ir tarpuose
                                for _ in range(15):  # 15 dekoracijų
                                    emoji = random.choice(decorations)
                                    x = random.randint(10, canvas_width - 70)
                                    y = random.randint(10, canvas_height - 70)
                                    draw.text((x, y), emoji, font=emoji_font, embedded_color=True)
                        except:
                            pass  # Jei nepavyko - praleidžiame dekoracijas
                    
                    # Išsaugome
                    collage_bytes = io.BytesIO()
                    collage.save(collage_bytes, format='JPEG', quality=95)
                    collage_bytes.seek(0)
                    
                    # IŠSAUGOME Į SESSION STATE (kad galėtume naudoti Social Media šablone)
                    st.session_state['created_collage'] = collage  # PIL Image objektas
                    st.session_state['collage_layout'] = f"{rows}x{cols}"
                    
                    st.success("✅ Collage sukurtas! Dabar galite jį naudoti Social Media šablone ⬆️")
                    st.image(collage_bytes, caption="Jūsų Collage", use_container_width=True)
                    
                    collage_bytes.seek(0)
                    st.download_button(
                        label="📥 Atsisiųsti Collage",
                        data=collage_bytes.getvalue(),
                        file_name=f"collage_{season}_{holiday}.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Klaida kuriant collage: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    else:
        st.warning("⚠️ Collage reikia bent 2 nuotraukų!")
    
    # Mygtukas išvalyti failus
    st.markdown("---")
    if st.button("🗑️ Išvalyti visus failus", type="secondary", use_container_width=True):
        st.session_state.uploaded_files = []
        st.rerun()
    
    if len(files_to_process) > 4:
        st.warning("⚠️ Per daug failų! Pasirinkite iki 4 nuotraukų.")
        files_to_process = files_to_process[:4]
        st.session_state.uploaded_files = files_to_process

# Apdorojimas tik jei yra failų ir paspaustas mygtukas
if create_content and files_to_process and len(files_to_process) > 0:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_analyses = []
    
    # Rodyti nuotraukas apdorojimo metu
    st.subheader(f"📸 Apdorojamos nuotraukos ({len(files_to_process)})")
    cols = st.columns(min(len(files_to_process), 4))
    for i, file in enumerate(files_to_process):
        with cols[i]:
            st.image(file, caption=f"Nuotrauka {i+1}", use_container_width=True)
            
    for i, file in enumerate(files_to_process):
        status_text.text(f"🔍 Analizuojama nuotrauka {i+1}/{len(files_to_process)}...")
        progress_bar.progress((i + 1) / (len(files_to_process) + 1))
        
        try:
            # Konvertuojame į base64
            image_b64 = image_to_base64(file)
            
            # Analizuojame
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
            
            st.success("✅ Turinys sėkmingai sukurtas!")
            
            # Rezultatai
            st.subheader("📝 Socialinių tinklų įrašai")
            
            # Rodyti sugeneruotą turinį
            st.markdown("### 🎯 Paruošti tekstai:")
            st.text_area("Kopijuokite tekstą:", value=captions, height=200)
            
            # Analitikos informacija
            with st.expander("📊 Detali analizė"):
                st.markdown("**Vaizdų analizė:**")
                for i, analysis in enumerate(all_analyses):
                    st.markdown(f"**Nuotrauka {i+1}:** {analysis}")
            
        except Exception as e:
            st.error(f"❌ Klaida generuojant turinį: {e}")
    
    progress_bar.empty()
    status_text.empty()

elif create_content and (not files_to_process or len(files_to_process) == 0):
    st.warning("⚠️ Prašome pirmiausia įkelti bent vieną nuotrauką!")

# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")