import streamlit as st
import io, os, base64
from openai import OpenAI
from dotenv import load_dotenv

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
st.info("📱 **Telefone:** Pasirinkite 'Fotografuoti' arba 'Pasirinkti iš galerijos'")

# CSS stilių pridejimas
st.markdown("""
<style>
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
# Failų įkėlimas su spalvotos rėmelio
uploaded_files = st.file_uploader(
    "Įkelkite nuotraukas (JPG/PNG, maks 4 failai)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="main_file_uploader"
)

# Išsaugojame failus session_state (mobiliems telefonams)
if uploaded_files:
    st.session_state.uploaded_files = uploaded_files
elif "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

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