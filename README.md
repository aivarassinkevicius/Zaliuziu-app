# 🌿 Žaliuzių ir Roletų Turinio Kūrėjas

Automatizuota AI aplikacija profesionalaus socialinių tinklų turinio kūrimui žaliuzių ir roletų verslui.

## ✨ Pagrindinės Funkcijos

### 📸 Nuotraukų Valdymas
- Įkelkite iki 4 nuotraukų (JPG, PNG)
- Automatinis vaizdų optimizavimas (šviesumas, kontrastas, sodrumas)
- Vandens ženklo pridėjimas
- Mobiliai optimizuota sąsaja

### 🎨 Collage Kūrimas
- **6 išdėstymo variantai**: Grid 2x2, Horizontal, Asymmetric, Magazine, Mosaic
- **3 dizaino stiliai**: Glassmorphism, Neo-Brutalism, Minimalist
- **Nuotraukų efektai**:
  - Balti rėmeliai (12px)
  - Užapvalinti kampai (25px radius)
  - 3D šešėlio efektas (drop shadow)
- **Integruoti teksto kvadratai** (ne overlay!)
- **3 socialinių tinklų formatai**:
  - Instagram kvadratas (1080x1080)
  - Instagram Portrait (1080x1350)
  - Facebook Post (1200x630)

### 🤖 AI Funkcionalumas

**1. GPT-4o-mini** - Turinio aprašymų generavimas
- Automatiškai analizuoja nuotraukas
- Sukuria aprašymus pagal metų laiką ir šventes
- Pritaikyta lietuviškoms šventėms

**2. DALL-E 3** - Fono generavimas
- AI generuojami sezoniniai fonai (Pavasaris, Vasara, Ruduo, Žiema)
- Švenčių tematikos (Kalėdos, Velykos, Valentino diena ir kt.)
- **Custom AI Prompt** - aprašyk foną savo žodžiais!
  - Pvz: "medžiai rugiai pieva kviečiai tekstūra"
  - Pvz: "jūra saulėlydis"

## 🚀 Kaip Pradėti

### Lokalus Paleidimas

```bash
# 1. Klonuoti repozitoriją
git clone https://github.com/aivarassinkevicius/Zaliuziu-app.git
cd Zaliuziu-app

# 2. Sukurti virtualią aplinką
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Įdiegti priklausomybes
pip install -r requirements.txt

# 4. Sukurti .env failą su API raktu
echo OPENAI_API_KEY=your-api-key-here > .env

# 5. Paleisti aplikaciją
streamlit run app.py
```

### Streamlit Cloud Deployment

1. Eiti į [share.streamlit.io](https://share.streamlit.io/)
2. Prisijungti su GitHub
3. Pasirinkti:
   - Repository: `aivarassinkevicius/Zaliuziu-app`
   - Branch: `dev-stable`
   - Main file: `app.py`
4. **Advanced Settings → Secrets**:
   ```toml
   OPENAI_API_KEY = "sk-proj-..."
   ```
5. Deploy!

## 📋 Reikalavimai

```txt
streamlit
openai
python-dotenv
Pillow==10.1.0
requests
```

## 🛠️ Technologijos

- **Frontend**: Streamlit (Python web framework)
- **AI Models**: 
  - OpenAI GPT-4o-mini (turinio aprašymai)
  - OpenAI DALL-E 3 (fono generavimas)
- **Image Processing**: PIL/Pillow
  - RGBA manipuliacija
  - ImageFilter (Gaussian Blur, Drop Shadow)
  - ImageDraw (teksto renderingas, formos)
  - ImageEnhance (šviesumas, kontrastas, sodrumas)
- **Version Control**: Git + GitHub

## 📱 Naudojimas

1. **Įkelti nuotraukas** (2-4 vnt)
2. **Pasirinkti nustatymus**:
   - Metų laikas (Pavasaris/Vasara/Ruduo/Žiema)
   - Šventė (pasirinktinai)
   - Custom AI fonas (pasirinktinai)
   - Vandens ženklas, spalvų optimizacija
3. **Sukurti Collage**:
   - Išdėstymas (Grid, Horizontal, Magazine...)
   - Dizaino stilius
   - Socialinio tinklo formatas
   - Teksto turinys
   - Nuotraukų efektai
4. **Atsisiųsti** rezultatą!

## 🎯 Versijos

- **v2.3** (current) - Simplified, no AI editing
- **dev-stable** branch - Stabili versija su naujausiais feature'ais

## 📊 Projekto Struktūra

```
Zaliuziu-app/
├── app.py              # Pagrindinis aplikacijos failas
├── requirements.txt    # Python priklausomybės
├── README.md          # Dokumentacija
├── .env               # API raktai (local)
├── .gitignore         # Git ignore taisyklės
└── venv/              # Virtual environment (local)
```

## 💰 AI Kainos (orientacinės)

- **GPT-4o-mini**: ~$0.15 už 1M input tokens, $0.60 už 1M output tokens
- **DALL-E 3** (1024x1024): ~$0.040 už vieną nuotrauką

## 🤝 Prisidėjimas

1. Fork projektas
2. Sukurti feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit pakeitimai (`git commit -m 'Add AmazingFeature'`)
4. Push į branch (`git push origin feature/AmazingFeature`)
5. Atidaryti Pull Request

## 📞 Kontaktai

**Repository**: [github.com/aivarassinkevicius/Zaliuziu-app](https://github.com/aivarassinkevicius/Zaliuziu-app)

---

Sukūrta su ❤️ žaliuzių ir roletų verslui | Powered by OpenAI GPT-4o-mini & DALL-E 3