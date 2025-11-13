import streamlit as st
import io, os, base64
from openai import OpenAI
from dotenv import load_dotenv

# ---------- Nustatymai ----------
load_dotenv()

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
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state inicializavimas mobiliems
if 'files_uploaded' not in st.session_state:
    st.session_state.files_uploaded = []
if 'files_processed' not in st.session_state:
    st.session_state.files_processed = False
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

st.title("🌿 Žaliuzių & Roletų turinio kūrėjas")
st.caption("Įkelk iki 4 nuotraukų ir gauk paruoštus įrašus socialiniams tinklams.")

# ---------- Pagalbinės funkcijos ----------
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
    """Konvertuoja įkeltą failą į base64"""
    return base64.b64encode(image_file.getvalue()).decode()

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
st.info("📱 **Telefone:** Pasirinkite 'Fotografuoti' arba 'Pasirinkti iš galerijos'. Maksimalus failo dydis: 18MB")

# Rodyti anksčiau įkeltas nuotraukas
if st.session_state.files_uploaded:
    st.success(f"✅ Anksčiau įkelta {len(st.session_state.files_uploaded)} nuotraukų")
    if st.button("🗑️ Išvalyti visas nuotraukas"):
        st.session_state.files_uploaded = []
        st.session_state.files_processed = False
        st.session_state.last_result = None
        st.rerun()

uploaded_files = st.file_uploader(
    "Įkelkite nuotraukas (JPG/PNG, maks 4 failai)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Palaikomi formatai: JPG, JPEG, PNG. Maksimalus dydis: 18MB per failą",
    key="file_uploader"
)

# Naudoti failus iš session state arba naujai įkeltus
files_to_process = st.session_state.files_uploaded if st.session_state.files_uploaded else []

# Jei įkelti nauji failai, atnaujinti session state
if uploaded_files:
    st.session_state.files_uploaded = []
    for file in uploaded_files:
        file_data = {
            'name': file.name,
            'size': len(file.getvalue()),
            'content': file.getvalue()
        }
        st.session_state.files_uploaded.append(file_data)
    files_to_process = st.session_state.files_uploaded

if files_to_process:
    st.success(f"✅ Paruošta {len(files_to_process)} nuotraukų!")
    
    with st.spinner("🔄 Tikrinami failai..."):
        # Tikrinti failų dydį
        valid_files = []
        for file_data in files_to_process:
            file_size = file_data['size'] / (1024 * 1024)  # MB
            if file_size > 18:
                st.error(f"❌ Failas '{file_data['name']}' per didelis ({file_size:.1f}MB). Maksimalus dydis: 18MB")
            else:
                valid_files.append(file_data)
                st.success(f"✅ {file_data['name']} - OK ({file_size:.1f}MB)")
    
    if not valid_files:
        st.error("❌ Nėra tinkamų failų. Patikrinkite failų dydį ir formatą.")
    else:
        st.subheader(f"📸 Paruoštos nuotraukos ({len(valid_files)})")
        
        # Rodyti nuotraukas iš session state
        cols = st.columns(min(len(valid_files), 4))
        for i, file_data in enumerate(valid_files):
            with cols[i]:
                st.image(file_data['content'], caption=f"Nuotrauka {i+1}", use_container_width=True)
    
        # Apdorojimo mygtukas
        if st.button("🚀 Sukurti turinį", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_analyses = []
            
            for i, file_data in enumerate(valid_files):
                status_text.text(f"🔍 Analizuojama nuotrauka {i+1}/{len(valid_files)}...")
                progress_bar.progress((i + 1) / (len(valid_files) + 1))
                
                try:
                    # Konvertuojame į base64
                    image_b64 = base64.b64encode(file_data['content']).decode()
                    
                    # Analizuojame
                    analysis = analyze_image(image_b64)
                    all_analyses.append(analysis)
                    
                except Exception as e:
                    st.error(f"❌ Klaida apdorojant nuotrauką {i+1}: {str(e)}")
                    st.error("💡 Patarimas: Pabandykite su mažesniu failu arba kitu formatu")
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

else:
    st.info("👆 Įkelkite nuotraukas, kad pradėtumėte!")

# Footer
st.markdown("---")
st.markdown("🌿 *Sukūrta žaliuzių ir roletų verslui* | Powered by OpenAI")