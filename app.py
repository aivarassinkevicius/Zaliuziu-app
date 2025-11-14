import streamlit as st
import io, os, base64
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# Bandome importuoti camera input (jei neveiks, praleidžia)
try:
    from streamlit_camera_input_live import camera_input_live
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ---------- Nustatymai ----------
load_dotenv()

# Version: 2.1 - Mobile session state fix
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

def compress_image(image_file, max_size_mb=1, max_dimension=1920):
    """
    Sumažina nuotrauką iki nurodyto dydžio ir rezoliucijos.
    Tai išsprendžia mobilių įkėlimo problemas ir sutaupo API kaštus.
    """
    try:
        # Atidarome nuotrauką
        img = Image.open(image_file)
        
        # Konvertuojame į RGB jei reikia (pvz. PNG su alpha kanalu)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Sumažiname rezoliuciją jei per didelė
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # Išsaugome į bytes su progressyviu mažinimu kokybės
        output = io.BytesIO()
        quality = 95
        
        while quality > 20:
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            
            size_mb = output.tell() / (1024 * 1024)
            if size_mb <= max_size_mb:
                break
            quality -= 5
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Klaida mažinant nuotrauką: {e}")
        # Jei nepavyko sumažinti, grąžiname originalą
        image_file.seek(0)
        return image_file

def analyze_image(image_bytes):
    """Naudoja GPT-4o-mini vaizdo analizei"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu esi vaizdų analizės specialistas, apibūdink nuotraukas lietuviškai."},
            {"role": "user", "content": [
                {"type": "text", "text": "Aprašyk, kas matosi šioje nuotraukoje. Pastebėk aplinką, apšvietimą, spalvas, ar matosi langai ar žaliuzės, koks įspūdis susidaro."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_bytes}}
            ]}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_captions(analysis_text, season, holiday):
    """Sukuria 3 teksto variantus lietuviškai"""
    holiday_context = f" ir šventę: {holiday}" if holiday != "Nėra" else ""
    prompt = f"""
    Pagal šią analizę: {analysis_text}
    ir metų laiką: {season}{holiday_context},
    sukurk 3 trumpus socialinių tinklų įrašų variantus (iki 250 simbolių) apie žaliuzes/roletus:
    1) marketinginis, 2) draugiškas, 3) su humoru. 
    Lietuviškai, gali pridėti 1–2 tinkamus hashtag'us.
    {f"Įtraukk šventės {holiday} tematiką, jei tinkama." if holiday != "Nėra" else ""}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

def image_to_base64(image_file):
    """Konvertuoja įkeltą failą į base64 su automatine kompresija"""
    # Pirmiausia sumažiname nuotrauką
    compressed = compress_image(image_file, max_size_mb=1, max_dimension=1920)
    return base64.b64encode(compressed.getvalue()).decode()

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
st.sidebar.markdown("💡 **Patarimas:** Įkelkite ryškias, kokybiškas nuotraukas su žaliuzėmis ar roletais.")

# Failų įkėlimas
st.markdown("### 📷 Nuotraukų įkėlimas")
st.info("📱 **Telefone:** Pasirinkite 'Fotografuoti' arba 'Pasirinkti iš galerijos'")

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
st.info("💡 **Patarimas**: Nuotraukos automatiškai sumažinamos iki 1 MB - tai pagreitina įkėlimą ir sutaupo API kaštus!")

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
                    # Informuojame apie kompresiją jei failas didelis
                    if file_size_mb > 2:
                        st.info("🗜️ Didelė nuotrauka - bus automatiškai sumažinta")
                    
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
    # Žalias langelis - sėkmingai įkelta
    st.markdown("""
    <div style="border: 2px solid #28a745; background-color: #d4edda; 
                border-radius: 10px; padding: 15px; margin: 10px 0;">
    </div>
    """, unsafe_allow_html=True)
    
    st.success(f"✅ Įkelta {len(files_to_process)} nuotraukų!")
    
    # Mygtukas išvalyti failus
    if st.button("🗑️ Išvalyti failus", type="secondary"):
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