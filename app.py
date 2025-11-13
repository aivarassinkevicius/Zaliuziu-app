import streamlit as st
from PIL import Image, ImageEnhance
import io, os
from openai import OpenAI
from dotenv import load_dotenv

# ---------- Nustatymai ----------
load_dotenv()

# Bandome gauti API raktą iš .env failo (vietinis) arba Streamlit secrets (cloud)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    # Jei vietiniai aplinkos kintamieji nėra, bandome Streamlit secrets
    api_key = st.secrets.get("openai", {}).get("api_key")

if not api_key:
    st.error("❌ OpenAI API raktas nerastas! Patikrinkite konfigūraciją.")
    st.stop()

client = OpenAI(api_key=api_key)

st.set_page_config(page_title="Žaliuzių turinio kūrėjas", page_icon="🌞", layout="wide")

st.title("🌿 Žaliuzių & Roletų turinio kūrėjas")
st.caption("Įkelk iki 4 nuotraukų ir gauk paruoštus įrašus socialiniams tinklams.")

# ---------- Pagalbinės funkcijos ----------
def auto_enhance(image: Image.Image):
    """Paprasta automatinė vaizdo korekcija"""
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.1)

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.15)

    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(1.1)

    return image

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

def generate_captions(analysis_text, season):
    """Sukuria 3 teksto variantus lietuviškai"""
    prompt = f"""
    Pagal šią analizę: {analysis_text}
    ir metų laiką: {season},
    sukurk 3 trumpus socialinių tinklų įrašų variantus (iki 250 simbolių) apie žaliuzes/roletus:
    1) marketinginis, 2) draugiškas, 3) su humoru. 
    Lietuviškai, gali pridėti 1–2 tinkamus hashtag'us.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

def image_to_bytes(image: Image.Image):
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()

# ---------- Streamlit UI ----------
uploaded_files = st.file_uploader(
    "Įkelk iki 4 nuotraukų (JPEG formatas):",
    type=["jpg", "jpeg"],
    accept_multiple_files=True
)

season = st.selectbox("Pasirink metų laiką:", ["Automatiškai", "Pavasaris", "Vasara", "Ruduo", "Žiema"])

if uploaded_files and st.button("🚀 Generuoti turinį"):
    for file in uploaded_files[:4]:
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📸 Originalas")
            image = Image.open(file).convert("RGB")
            st.image(image, use_column_width=True)

        with col2:
            st.subheader("🎨 Pakoreguota versija")
            enhanced = auto_enhance(image)
            st.image(enhanced, use_column_width=True)

            # atsisiuntimas
            img_bytes = image_to_bytes(enhanced)
            st.download_button(
                label="⬇️ Atsisiųsti pakoreguotą nuotrauką",
                data=img_bytes,
                file_name=f"enhanced_{file.name}",
                mime="image/jpeg"
            )

        # Vaizdo analizė ir teksto generavimas
        with st.spinner("Analizuoju nuotrauką ir kuriu tekstus..."):
            import base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            analysis = analyze_image(img_str)

            detected_season = season
            if season == "Automatiškai":
                # Bandome nustatyti sezoną iš analizės
                if any(w in analysis.lower() for w in ["žalias", "žydintis", "pavasar"]):
                    detected_season = "Pavasaris"
                elif any(w in analysis.lower() for w in ["karšt", "vasar", "saulėt"]):
                    detected_season = "Vasara"
                elif any(w in analysis.lower() for w in ["rud", "gelton", "lap"]):
                    detected_season = "Ruduo"
                elif any(w in analysis.lower() for w in ["snieg", "žiem", "šalt"]):
                    detected_season = "Žiema"
                else:
                    detected_season = "Pavasaris"  # default

            captions = generate_captions(analysis, detected_season)

        st.markdown("### ✍️ Siūlomi tekstai:")
        st.text_area("Sugeneruoti įrašai:", captions, height=180)
        st.success(f"✅ Aptiktas sezonas: {detected_season}")

st.divider()
st.caption("Sukurta naudojant Streamlit + OpenAI GPT-4o-mini")
