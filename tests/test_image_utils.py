import unittest
from PIL import Image
from lib.image_utils import add_marketing_overlay, load_font, create_social_template

class TestImageUtils(unittest.TestCase):
    def setUp(self):
        # Create a simple RGB image for testing
        self.img = Image.new('RGB', (100, 100), color='white')

    def test_add_marketing_overlay(self):
        result = add_marketing_overlay(self.img, "Test Overlay")
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, self.img.size)

    def test_load_font_default(self):
        font = load_font()
        self.assertIsNotNone(font)

    def test_create_social_template(self):
        result = create_social_template(self.img)
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, self.img.size)

if __name__ == "__main__":
    unittest.main()
