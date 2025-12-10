# Streamlit API Documentation

## Overview
Streamlit is an open-source Python library that makes it easy to create beautiful, custom web apps for machine learning and data science.

## Key Functions Used in This Project

### Page Configuration
```python
st.set_page_config(
    page_title="Title",
    page_icon="🌞",
    layout="wide"  # or "centered"
)
```

### Display Elements

#### Text Elements
- `st.title("Title")` - Main title (H1)
- `st.header("Header")` - Section header (H2)
- `st.subheader("Subheader")` - Subsection header (H3)
- `st.markdown("**Bold** text")` - Markdown formatting
- `st.caption("Small text")` - Small caption text
- `st.text("Plain text")` - Fixed-width text

#### Information Messages
- `st.success("✅ Success message")` - Green success box
- `st.info("💡 Info message")` - Blue info box
- `st.warning("⚠️ Warning message")` - Yellow warning box
- `st.error("❌ Error message")` - Red error box

#### Media Elements
- `st.image(image, caption="Caption", width=400)` - Display image
- `st.image(image, use_container_width=True)` - Responsive image

### Input Widgets

#### Sidebar
```python
st.sidebar.header("Header")
st.sidebar.selectbox("Label", ["Option 1", "Option 2"])
st.sidebar.checkbox("Label", value=True)
st.sidebar.slider("Label", min_value, max_value, default_value, step)
st.sidebar.text_input("Label", value="default")
```

#### Main Area
```python
st.selectbox("Label", options, index=0, help="Help text")
st.checkbox("Label", value=False, help="Help text")
st.slider("Label", min, max, default, step, help="Help text")
st.text_input("Label", value="", placeholder="...", type="default")
st.text_area("Label", value="", height=100)
st.radio("Label", ["Option 1", "Option 2"])
```

#### File Upload
```python
uploaded_files = st.file_uploader(
    "Label",
    type=["jpg", "png", "jpeg"],
    accept_multiple_files=True,
    help="Help text"
)
```

#### Buttons
```python
if st.button("Label", type="primary", use_container_width=True):
    # Action code here
    pass

st.download_button(
    label="📥 Download",
    data=file_bytes,
    file_name="filename.jpg",
    mime="image/jpeg",
    use_container_width=True
)
```

### Layout

#### Columns
```python
col1, col2 = st.columns(2)  # Equal width
col1, col2, col3 = st.columns([2, 1, 1])  # Custom ratios

with col1:
    st.write("Content in column 1")

with col2:
    st.write("Content in column 2")
```

#### Tabs
```python
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])

with tab1:
    st.write("Content in tab 1")

with tab2:
    st.write("Content in tab 2")
```

#### Expander
```python
with st.expander("Label", expanded=False):
    st.write("Hidden content")
```

#### Container
```python
container = st.container()
with container:
    st.write("Content in container")
```

### Progress & Status

```python
progress_bar = st.progress(0)
status_text = st.empty()

for i in range(100):
    progress_bar.progress(i / 100)
    status_text.text(f"Processing {i}%...")

progress_bar.empty()  # Remove progress bar
status_text.empty()  # Remove status text
```

#### Spinner
```python
with st.spinner("Loading..."):
    # Long-running code
    time.sleep(3)
```

### Session State

```python
# Initialize
if "key" not in st.session_state:
    st.session_state.key = "default_value"

# Access
value = st.session_state.key

# Update
st.session_state.key = "new_value"

# Delete
del st.session_state.key

# Rerun app
st.rerun()
```

### Caching

```python
@st.cache_data
def load_data():
    # Expensive computation
    return data

@st.cache_resource
def load_model():
    # Load ML model (singleton)
    return model
```

### Secrets Management

```python
# .streamlit/secrets.toml
# API_KEY = "sk-..."

# Access in code
api_key = st.secrets["API_KEY"]
```

### Best Practices

1. **Use session_state for persistence** across reruns
2. **Use columns for side-by-side layouts**
3. **Use expanders for optional content**
4. **Use spinners for long operations**
5. **Use cache_data for data loading**
6. **Use secrets for API keys**
7. **Always check if file is uploaded before processing**
8. **Use `key` parameter for duplicate widgets**

### Common Patterns

#### File Upload & Process
```python
uploaded_file = st.file_uploader("Upload", type=["jpg"])

if uploaded_file is not None:
    # Process file
    file.seek(0)  # Reset file pointer
    image = Image.open(file)
```

#### Button State Management
```python
if st.button("Process"):
    st.session_state.trigger = True

if st.session_state.get("trigger", False):
    # Process
    st.session_state.trigger = False
    st.rerun()
```

## Documentation Link
https://docs.streamlit.io/
