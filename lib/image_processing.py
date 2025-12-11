"""
Professional Image Processing Pipeline
Auto-crop, perspective correction, and enhancement for window blinds photos
"""

import cv2
import numpy as np
from PIL import Image
import io


def pil_to_cv2(pil_image):
    """Convert PIL Image to OpenCV format"""
    # Convert PIL to RGB numpy array
    img_array = np.array(pil_image.convert('RGB'))
    # Convert RGB to BGR for OpenCV
    return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_image):
    """Convert OpenCV image to PIL format"""
    # Convert BGR to RGB
    rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_image)


def smart_auto_crop(cv2_image, margin_percent=0.03):
    """
    Detect blinds area and crop out walls/background
    Uses multiple methods: edge detection + color clustering
    
    Args:
        cv2_image: OpenCV image (BGR)
        margin_percent: Safety margin around detected area (0.03 = 3%)
    
    Returns:
        Cropped OpenCV image
    """
    h, w = cv2_image.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
    
    # Apply stronger blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # MUCH stronger edge detection for better contour detection
    edges = cv2.Canny(blurred, 30, 100)
    
    # Dilate edges to connect nearby features (blinds slats)
    kernel = np.ones((5, 5), np.uint8)
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return cv2_image
    
    # Find the largest contour (likely the blinds)
    largest_contour = max(contours, key=cv2.contourArea)
    contour_area = cv2.contourArea(largest_contour)
    
    # Only crop if contour is significant (covers at least 40% of image)
    if contour_area < (h * w * 0.4):
        return cv2_image
    
    # Get bounding rectangle
    x, y, w_rect, h_rect = cv2.boundingRect(largest_contour)
    
    # Add smaller margin for tighter crop
    margin_w = int(w * margin_percent)
    margin_h = int(h * margin_percent)
    
    # Calculate crop coordinates with margins
    x1 = max(0, x - margin_w)
    y1 = max(0, y - margin_h)
    x2 = min(w, x + w_rect + margin_w)
    y2 = min(h, y + h_rect + margin_h)
    
    # Crop
    cropped = cv2_image[y1:y2, x1:x2]
    
    # Safety check - if crop is too small, return original
    if cropped.shape[0] < h * 0.5 or cropped.shape[1] < w * 0.5:
        return cv2_image
    
    return cropped


def perspective_correction(cv2_image):
    """
    Detect vertical lines and straighten image
    
    Args:
        cv2_image: OpenCV image (BGR)
    
    Returns:
        Corrected OpenCV image
    """
    h, w = cv2_image.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Hough Line Transform to detect lines
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    
    if lines is None or len(lines) < 2:
        # Not enough lines detected - return original
        return cv2_image
    
    # Calculate angles of vertical lines
    angles = []
    for line in lines:
        rho, theta = line[0]
        # Filter for near-vertical lines (±30 degrees from vertical)
        angle_deg = np.degrees(theta) - 90
        if -30 < angle_deg < 30:
            angles.append(angle_deg)
    
    if not angles:
        return cv2_image
    
    # Calculate median angle (more robust than mean)
    median_angle = np.median(angles)
    
    # Only correct if angle is significant (> 1 degree)
    if abs(median_angle) < 1.0:
        return cv2_image
    
    # Rotate image
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    
    # Calculate new bounding box
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]
    
    # Apply rotation
    rotated = cv2.warpAffine(cv2_image, rotation_matrix, (new_w, new_h), 
                             flags=cv2.INTER_LINEAR, 
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(255, 255, 255))
    
    return rotated


def white_balance_correction(cv2_image):
    """
    SUBTLE white balance - removes only strong yellow/blue tints
    
    Args:
        cv2_image: OpenCV image (BGR)
    
    Returns:
        Color-corrected OpenCV image (SUBTLE correction)
    """
    # MUCH gentler gray world assumption - only 30% correction
    result = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2LAB).astype(np.float32)
    avg_a = np.average(result[:, :, 1])
    avg_b = np.average(result[:, :, 2])
    
    # Only correct if tint is STRONG (deviation > 5 from neutral 128)
    if abs(avg_a - 128) < 5 and abs(avg_b - 128) < 5:
        return cv2_image  # No correction needed
    
    # Apply only 30% of correction (was 110% before!)
    result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 0.3)
    result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 0.3)
    
    result = np.clip(result, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
    
    return result


def enhance_clarity(cv2_image, strength=0.5):
    """
    STRONG clarity boost - sharpens blinds texture
    
    Args:
        cv2_image: OpenCV image (BGR)
        strength: Enhancement strength (0.5 = moderate sharpening)
    
    Returns:
        Enhanced OpenCV image with sharper details
    """
    # Convert to float
    img_float = cv2_image.astype(np.float32)
    
    # Apply Gaussian blur to get smooth base
    smooth = cv2.GaussianBlur(cv2_image, (0, 0), 3).astype(np.float32)
    
    # Calculate detail layer (high-pass filter)
    detail = img_float - smooth
    
    # Enhance detail with MUCH stronger strength
    enhanced = img_float + detail * strength
    
    # Clip and convert back
    enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
    
    return enhanced


def normalize_aspect_ratio(cv2_image, target_ratio="4:3", fill_color=(255, 255, 255)):
    """
    Normalize image to specific aspect ratio by smart cropping or padding
    
    Args:
        cv2_image: OpenCV image (BGR)
        target_ratio: Target aspect ratio ("4:3", "16:9", "1:1", "3:4")
        fill_color: Padding color if needed (default white)
    
    Returns:
        Image with normalized aspect ratio
    """
    h, w = cv2_image.shape[:2]
    current_ratio = w / h
    
    # Parse target ratio
    ratio_map = {
        "4:3": 4/3,      # 1.333 - horizontal
        "3:4": 3/4,      # 0.75 - vertical
        "16:9": 16/9,    # 1.778 - wide horizontal
        "9:16": 9/16,    # 0.5625 - vertical video
        "1:1": 1.0,      # square
    }
    
    target_ratio_value = ratio_map.get(target_ratio, 4/3)
    
    # If already close to target (within 5%), return original
    if abs(current_ratio - target_ratio_value) / target_ratio_value < 0.05:
        return cv2_image
    
    if current_ratio > target_ratio_value:
        # Image is too wide - crop width or pad height
        # Prefer cropping to maintain quality
        new_width = int(h * target_ratio_value)
        
        if new_width > w * 0.7:  # If crop is gentle (< 30% loss)
            # Crop width (center crop)
            x_start = (w - new_width) // 2
            cropped = cv2_image[:, x_start:x_start + new_width]
            return cropped
        else:
            # Crop is too aggressive - pad height instead
            new_height = int(w / target_ratio_value)
            pad_total = new_height - h
            pad_top = pad_total // 2
            pad_bottom = pad_total - pad_top
            
            padded = cv2.copyMakeBorder(cv2_image, pad_top, pad_bottom, 0, 0,
                                        cv2.BORDER_CONSTANT, value=fill_color)
            return padded
    else:
        # Image is too tall - crop height or pad width
        new_height = int(w / target_ratio_value)
        
        if new_height > h * 0.7:  # If crop is gentle
            # Crop height (center crop)
            y_start = (h - new_height) // 2
            cropped = cv2_image[y_start:y_start + new_height, :]
            return cropped
        else:
            # Crop is too aggressive - pad width instead
            new_width = int(h * target_ratio_value)
            pad_total = new_width - w
            pad_left = pad_total // 2
            pad_right = pad_total - pad_left
            
            padded = cv2.copyMakeBorder(cv2_image, 0, 0, pad_left, pad_right,
                                        cv2.BORDER_CONSTANT, value=fill_color)
            return padded


def process_blinds_photo(pil_image, enable_auto_crop=True, enable_perspective=True, 
                         enable_white_balance=True, enable_clarity=True, 
                         enable_aspect_ratio=False, target_aspect_ratio="4:3"):
    """
    Main processing pipeline for window blinds photos
    
    Args:
        pil_image: PIL Image
        enable_auto_crop: Enable smart auto-cropping
        enable_perspective: Enable perspective correction
        enable_white_balance: Enable white balance correction
        enable_clarity: Enable clarity enhancement
        enable_aspect_ratio: Enable aspect ratio normalization
        target_aspect_ratio: Target ratio ("4:3", "16:9", "1:1", "3:4")
    
    Returns:
        Processed PIL Image
    """
    # Convert to OpenCV
    cv2_img = pil_to_cv2(pil_image)
    
    # 1. Auto-crop (detect blinds and crop walls)
    if enable_auto_crop:
        try:
            cv2_img = smart_auto_crop(cv2_img)
        except Exception as e:
            print(f"Auto-crop failed: {e}")
    
    # 2. Perspective correction (straighten vertical lines)
    if enable_perspective:
        try:
            cv2_img = perspective_correction(cv2_img)
        except Exception as e:
            print(f"Perspective correction failed: {e}")
    
    # 3. White balance correction (remove tint)
    if enable_white_balance:
        try:
            cv2_img = white_balance_correction(cv2_img)
        except Exception as e:
            print(f"White balance failed: {e}")
    
    # 4. Clarity enhancement (increase detail)
    if enable_clarity:
        try:
            cv2_img = enhance_clarity(cv2_img, strength=0.5)
        except Exception as e:
            print(f"Clarity enhancement failed: {e}")
    
    # 5. Aspect ratio normalization (make all photos same ratio)
    if enable_aspect_ratio:
        try:
            cv2_img = normalize_aspect_ratio(cv2_img, target_ratio=target_aspect_ratio)
        except Exception as e:
            print(f"Aspect ratio normalization failed: {e}")
    
    # Convert back to PIL
    return cv2_to_pil(cv2_img)
