# PIL/Pillow Image Processing Documentation

## Overview
Pillow (PIL Fork) is the Python Imaging Library for opening, manipulating, and saving image files.

## Installation
```bash
pip install Pillow==10.1.0
```

## Import
```python
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter
```

## Core Modules Used

### Image - Core Image Class

#### Open Image
```python
# From file
img = Image.open("image.jpg")

# From bytes
img = Image.open(io.BytesIO(image_bytes))

# From uploaded file (Streamlit)
img = Image.open(uploaded_file)
```

#### Create New Image
```python
# RGB image
img = Image.new('RGB', (width, height), color=(255, 255, 255))

# RGBA image (with transparency)
img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
```

#### Image Properties
```python
width, height = img.size
mode = img.mode  # 'RGB', 'RGBA', 'L', etc.
format = img.format  # 'JPEG', 'PNG', etc.
```

#### Resize
```python
# Resize to exact size
new_img = img.resize((new_width, new_height), Image.LANCZOS)

# Resize maintaining aspect ratio
img.thumbnail((max_width, max_height), Image.LANCZOS)
```

#### Crop
```python
# Crop (left, top, right, bottom)
cropped = img.crop((100, 100, 400, 400))
```

#### Paste
```python
# Simple paste
canvas.paste(img, (x, y))

# Paste with mask (transparency)
canvas.paste(img, (x, y), img)  # img as mask if RGBA
```

#### Rotate
```python
# Rotate (expand=True to fit full image)
rotated = img.rotate(45, expand=True, fillcolor=(255, 255, 255))
```

#### Convert Mode
```python
# Convert to RGB (remove alpha)
rgb_img = img.convert('RGB')

# Convert to RGBA (add alpha)
rgba_img = img.convert('RGBA')
```

#### Save
```python
# Save to file
img.save("output.jpg", quality=95)

# Save to bytes
buffer = io.BytesIO()
img.save(buffer, format='JPEG', quality=95)
buffer.seek(0)
```

### ImageDraw - Drawing on Images

```python
draw = ImageDraw.Draw(img)
```

#### Rectangle
```python
# Filled rectangle
draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255, 128))

# Outlined rectangle
draw.rectangle([x1, y1, x2, y2], outline=(0, 0, 0), width=2)
```

#### Rounded Rectangle
```python
draw.rounded_rectangle([x1, y1, x2, y2], radius=25, fill=(255, 255, 255))
```

#### Text
```python
# Load font
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=60)

# Draw text
draw.text((x, y), "Text", fill=(0, 0, 0), font=font)

# Get text size (for centering)
bbox = draw.textbbox((0, 0), "Text", font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
```

#### Other Shapes
```python
# Line
draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0), width=5)

# Ellipse
draw.ellipse([x1, y1, x2, y2], fill=(255, 0, 0))

# Polygon
draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=(0, 255, 0))
```

### ImageFont - Font Handling

```python
# TrueType font
font = ImageFont.truetype("font.ttf", size=60)

# Default font
font = ImageFont.load_default()

# Common Windows fonts
fonts = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/calibri.ttf"
]
```

### ImageEnhance - Image Adjustments

#### Brightness
```python
enhancer = ImageEnhance.Brightness(img)
img = enhancer.enhance(1.2)  # 1.0 = original, >1.0 brighter, <1.0 darker
```

#### Contrast
```python
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.3)  # 1.0 = original, >1.0 more contrast
```

#### Color/Saturation
```python
enhancer = ImageEnhance.Color(img)
img = enhancer.enhance(1.2)  # 1.0 = original, 0.0 = grayscale, >1.0 more saturated
```

#### Sharpness
```python
enhancer = ImageEnhance.Sharpness(img)
img = enhancer.enhance(2.0)  # 1.0 = original, >1.0 sharper
```

### ImageFilter - Filters

```python
# Gaussian Blur
img = img.filter(ImageFilter.GaussianBlur(radius=5))

# Sharpen
img = img.filter(ImageFilter.SHARPEN)

# Unsharp Mask (professional sharpening)
img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

# Edge Enhance
img = img.filter(ImageFilter.EDGE_ENHANCE)

# Smooth
img = img.filter(ImageFilter.SMOOTH)
```

### ImageOps - Image Operations

#### Expand (Add Border)
```python
# Add white border
img = ImageOps.expand(img, border=10, fill='white')
```

#### Fit (Crop to Aspect Ratio)
```python
# Fit image to exact size (crop center)
img = ImageOps.fit(img, (width, height), Image.LANCZOS)
```

#### Grayscale
```python
gray_img = ImageOps.grayscale(img)
```

#### Flip
```python
flipped = ImageOps.flip(img)  # Vertical flip
mirrored = ImageOps.mirror(img)  # Horizontal flip
```

## Advanced Techniques

### Alpha Compositing (Transparency)
```python
# Blend two RGBA images
result = Image.alpha_composite(background, foreground)
```

### White Background Removal
```python
img = img.convert('RGBA')
datas = img.getdata()

new_data = []
for item in datas:
    # Change white pixels to transparent
    if item[0] > 200 and item[1] > 200 and item[2] > 200:
        new_data.append((255, 255, 255, 0))
    else:
        new_data.append(item)

img.putdata(new_data)
```

### Drop Shadow Effect
```python
# Create shadow layer
shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
shadow_draw = ImageDraw.Draw(shadow)

# Draw shadow (offset)
shadow_draw.rectangle([x+5, y+5, x+w+5, y+h+5], fill=(0, 0, 0, 100))

# Blur shadow
shadow = shadow.filter(ImageFilter.GaussianBlur(10))

# Composite: canvas + shadow + image
canvas.paste(shadow, (0, 0), shadow)
canvas.paste(img, (x, y), img)
```

### Rounded Corners
```python
def add_corners(img, radius):
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, img.width, img.height], radius=radius, fill=255)
    
    output = ImageOps.fit(img, img.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    return output
```

### Professional Auto Enhancement
```python
import numpy as np

# Convert to numpy array
img_array = np.array(img)

# Histogram optimization (auto levels)
for channel in range(3):
    channel_data = img_array[:, :, channel]
    p2, p98 = np.percentile(channel_data, (2, 98))
    stretched = np.clip((channel_data - p2) * 255.0 / (p98 - p2), 0, 255)
    img_array[:, :, channel] = stretched.astype(np.uint8)

# Convert back to PIL
img = Image.fromarray(img_array)

# Smart sharpening
img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

# Enhance contrast
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.25)

# Boost saturation
enhancer = ImageEnhance.Color(img)
img = enhancer.enhance(1.20)
```

## Best Practices

1. **Always use RGBA for transparency**
   - Use 4th channel (alpha) for transparency
   - Convert RGB to RGBA before compositing

2. **Use LANCZOS for quality resizing**
   - `Image.LANCZOS` for best quality
   - `Image.BICUBIC` for good quality + speed

3. **Seek to 0 before reading uploaded files**
   ```python
   uploaded_file.seek(0)
   img = Image.open(uploaded_file)
   ```

4. **Use BytesIO for in-memory operations**
   ```python
   buffer = io.BytesIO()
   img.save(buffer, format='JPEG')
   buffer.seek(0)
   ```

5. **Close images when done (memory)**
   ```python
   img.close()
   ```

## Common Patterns

### Load → Process → Save
```python
img = Image.open("input.jpg")
img = img.resize((800, 600), Image.LANCZOS)
img = img.filter(ImageFilter.SHARPEN)
img.save("output.jpg", quality=95)
```

### Canvas → Paste Multiple Images
```python
canvas = Image.new('RGB', (1080, 1080), 'white')
canvas.paste(img1, (0, 0))
canvas.paste(img2, (540, 0))
canvas.paste(img3, (0, 540))
canvas.paste(img4, (540, 540))
```

## Documentation Link
https://pillow.readthedocs.io/
