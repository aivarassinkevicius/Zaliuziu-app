import io
import pytest
from PIL import Image
from lib.image_utils import add_marketing_overlay, create_social_template
from app import ai_generate_layout

def mock_image_bytes():
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def test_add_marketing_overlay_watermark():
    img_bytes = mock_image_bytes()
    result = add_marketing_overlay(
        img_bytes,
        add_watermark=True,
        add_border=False,
        brightness=1.0,
        contrast=1.0,
        saturation=1.0,
        watermark_text="TEST",
        watermark_size=24
    )
    assert isinstance(result, io.BytesIO)
    result.seek(0)
    data = result.read()
    assert len(data) > 0

def test_create_social_template_png():
    img_bytes = mock_image_bytes()
    img = Image.open(img_bytes)
    result = create_social_template(
        images=[img],
        text="Test",
        layout="1",
        text_position="bottom",
        font_size=32,
        background_color="#FFFFFF",
        style="Classic",
        font_family="Arial Bold",
        text_color="#000000",
        bg_opacity=180
    )
    assert isinstance(result, io.BytesIO)
    result.seek(0)
    data = result.read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header
    assert len(data) > 1000

def test_ai_generate_layout_dict():
    layout = ai_generate_layout(2, ["A", "B"])
    assert isinstance(layout, dict)
    assert "nuotraukos" in layout
    assert "tekstai" in layout
    assert isinstance(layout["nuotraukos"], list)
    assert isinstance(layout["tekstai"], list)
