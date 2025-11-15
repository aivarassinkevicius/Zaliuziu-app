import streamlit as st
import io, os, base64
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import replicate
import requests

# Bandome importuoti camera input (jei neveiks, praleidžia)
try:
    from streamlit_camera_input_live import camera_input_live
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ---------- Nustatymai ----------
load_dotenv()

# Version: 2.2 - AI Image Editing with Replicate
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

# Replicate API raktas
replicate_key = os.getenv("REPLICATE_API_TOKEN")
if not replicate_key:
    try:
        replicate_key = st.secrets.get("REPLICATE_API_TOKEN")
    except:
        pass

client = OpenAI(api_key=api_key)

st.set_page_config(
    page_title="Žaliuzių turinio kūrėjas", 
    page_icon="🌞", 
    layout="wide"
)

st.title("🌿 Žaliuzių & Roletų turinio kūrėjas")
st.caption("Įkelk iki 4 nuotraukų ir gauk paruoštus įrašus socialiniams tinklams.")

# ---------- Pagalbinės funkcijos ----------

def add_marketing_overlay(image_file, add_watermark=False, add_border=False, brightness=1.0, contrast=1.0, saturation=1.0, watermark_text="", watermark_size=80):
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
            # TIESIAI: slider reikšmė = px dydis (bet ne mažiau kaip 20)
            font_size = max(20, int(watermark_size))
            
            # Bandome įkelti geresnį fontą
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("arialbd.ttf", font_size)  # Bold Arial
                    except:
                        # Jei nepavyko, naudojame default
                        font = ImageFont.load_default()
            
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

def edit_image_with_ai(image_file, mask_file, prompt):
    """Redaguoja nuotrauką naudojant OpenAI DALL-E su mask'u - TIKRAS objektų šalinimas"""
    try:
        # Konvertuojame nuotrauką
        image_file.seek(0)
        img = Image.open(image_file)
        
        # Konvertuojame į RGBA (reikia DALL-E)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # DALL-E reikalauja 1024x1024 arba mažiau
        max_size = 1024
        original_size = (img.width, img.height)
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Išsaugome kaip PNG
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        img_bytes.name = 'image.png'
        
        # Paruošiame mask'ą
        mask_file.seek(0)
        mask = Image.open(mask_file)
        
        # Resize mask į tą patį dydį kaip image
        if mask.size != img.size:
            mask = mask.resize(img.size, Image.Resampling.LANCZOS)
        
        # Konvertuojame mask į juoda-baltą (baltos vietos bus keičiamos)
        if mask.mode != 'RGBA':
            mask = mask.convert('RGBA')
        
        # Išsaugome mask
        mask_bytes = io.BytesIO()
        mask.save(mask_bytes, format='PNG')
        mask_bytes.seek(0)
        mask_bytes.name = 'mask.png'
        
        # Naudojame OpenAI DALL-E Edit su mask'u
        response = client.images.edit(
            image=img_bytes,
            mask=mask_bytes,
            prompt=f"Fill the masked area naturally matching the surrounding. {prompt}. Professional photo editing, realistic, high quality, seamless blend.",
            n=1,
            size="1024x1024"
        )
        
        # Gauname rezultatą
        image_url = response.data[0].url
        
        # Atsisiunčiame
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            edited_image = io.BytesIO(img_response.content)
            return edited_image, "✅ Nuotrauka sėkmingai redaguota su DALL-E!"
        else:
            return None, f"❌ Nepavyko atsisiųsti: {img_response.status_code}"
            
    except Exception as e:
        return None, f"❌ Klaida: {str(e)}"

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
    watermark_size = st.sidebar.slider("📏 Vandens ženklo dydis (px)", 20, 500, 120, 10, help="Šrifto dydis pikseliais. 120px = vidutinis, 200px = didelis")
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

# Mygtukas visada matomas
create_content = st.button("🚀 Sukurti turinį", type="primary", use_container_width=True)

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
    
    # AI Chat asistento skyrius - REALUS REDAGAVIMAS SU MASK
    st.markdown("---")
    st.markdown("### 🎨 AI Objektų Šalinimas (su piešimu)")
    st.info("✏️ **Nupiešk ant nuotraukos** kur norite ištrinti objektą, tada AI užpildys tuščią vietą!")
    
    # Inicializuojame
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'ai_edited_images' not in st.session_state:
        st.session_state.ai_edited_images = []
    
    # Pasirinkti kurią nuotrauką redaguoti
    photo_to_edit = st.selectbox(
        "📸 Pasirinkite nuotrauką:",
        options=range(len(files_to_process)),
        format_func=lambda x: f"Nuotrauka {x+1}"
    )
    
    # Parodyti nuotrauką ir leisti piešti
    if len(files_to_process) > 0:
        from streamlit_drawable_canvas import st_canvas
        import numpy as np
        
        selected_file = files_to_process[photo_to_edit]
        selected_file.seek(0)
        img = Image.open(selected_file)
        
        # Konvertuojame į RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize jei per didelė
        display_width = 600
        if img.width > display_width:
            ratio = display_width / img.width
            display_height = int(img.height * ratio)
            img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        else:
            display_width = img.width
            display_height = img.height
        
        st.markdown("**✏️ Nupiešk RAUDONAI kur norite ištrinti:**")
        
        # Canvas piešimui - konvertuojame į numpy array
        img_array = np.array(img)
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.5)",
            stroke_width=20,
            stroke_color="#FF0000",
            background_image=Image.fromarray(img_array),
            update_streamlit=True,
            height=display_height,
            width=display_width,
            drawing_mode="freedraw",
            key=f"canvas_{photo_to_edit}",
        )
        
        # Instrukcijos
        col1, col2 = st.columns(2)
        with col1:
            st.info("🖌️ Piešk raudonai per objektą kurį norite ištrinti")
        with col2:
            st.success("✅ Tada spausti 'Redaguoti su AI'")
        
        # Aprašymas ką AI turėtų padaryti
        user_prompt = st.text_input(
            "💬 Kaip užpildyti tuščią vietą? (angliškai)",
            value="remove object and fill naturally",
            help="Pvz: 'wooden floor', 'white wall', 'natural background'"
        )
        
        edit_button = st.button("✨ Redaguoti su AI", type="primary", use_container_width=True)
        
        if edit_button and canvas_result.image_data is not None:
            with st.spinner("🎨 DALL-E šalina objektą... (10-20 sek)"):
                try:
                    # Gauname mask iš canvas
                    mask_data = canvas_result.image_data
                    
                    # Konvertuojame mask į PIL Image
                    mask_img = Image.fromarray(mask_data.astype('uint8'), 'RGBA')
                    
                    # Sukuriame juoda-baltą mask (baltos vietos - kur trinti)
                    mask_gray = mask_img.convert('L')
                    
                    # Išsaugome mask į BytesIO
                    mask_bytes = io.BytesIO()
                    mask_gray.save(mask_bytes, format='PNG')
                    mask_bytes.seek(0)
                    
                    # Redaguojame su AI
                    edited_img, message = edit_image_with_ai(selected_file, mask_bytes, user_prompt)
                    
                    if edited_img:
                        st.success(message)
                        
                        # Parodome rezultatą
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**🖼️ Originali:**")
                            selected_file.seek(0)
                            st.image(selected_file, use_container_width=True)
                        
                        with col2:
                            st.markdown("**✨ AI redaguota:**")
                            edited_img.seek(0)
                            st.image(edited_img, use_container_width=True)
                        
                        # Download
                        edited_img.seek(0)
                        st.download_button(
                            label="📥 Atsisiųsti",
                            data=edited_img.getvalue(),
                            file_name=f"edited_{photo_to_edit + 1}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                        
                        st.info("💰 Kaina: ~$0.04")
                        
                    else:
                        st.error(message)
                        
                except Exception as e:
                    st.error(f"❌ Klaida: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        
        elif edit_button:
            st.warning("⚠️ Pirmiausia nupiešk ant nuotraukos kur norite ištrinti!")
    
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