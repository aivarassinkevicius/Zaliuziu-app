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


def smart_auto_crop(cv2_image, margin_percent=0.05):
    """
    Detect blinds area and crop out walls/background
    
    Args:
        cv2_image: OpenCV image (BGR)
        margin_percent: Safety margin around detected area (0.05 = 5%)
    
    Returns:
        Cropped OpenCV image
    """
    h, w = cv2_image.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        # No contours found - return original
        return cv2_image
    
    # Find the largest contour (likely the blinds)
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get bounding rectangle
    x, y, w_rect, h_rect = cv2.boundingRect(largest_contour)
    
    # Add margin
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
    if cropped.shape[0] < h * 0.3 or cropped.shape[1] < w * 0.3:
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
    Remove yellow/blue tint and normalize colors
    
    Args:
        cv2_image: OpenCV image (BGR)
    
    Returns:
        Color-corrected OpenCV image
    """
    # Simple gray world assumption
    result = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2LAB)
    avg_a = np.average(result[:, :, 1])
    avg_b = np.average(result[:, :, 2])
    
    result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
    
    result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
    
    return result


def enhance_clarity(cv2_image, strength=0.15):
    """
    Increase texture and detail clarity
    
    Args:
        cv2_image: OpenCV image (BGR)
        strength: Enhancement strength (0.0 to 1.0)
    
    Returns:
        Enhanced OpenCV image
    """
    # Convert to float
    img_float = cv2_image.astype(np.float32) / 255.0
    
    # Apply bilateral filter for edge-preserving smoothing
    smooth = cv2.bilateralFilter(cv2_image, 9, 75, 75).astype(np.float32) / 255.0
    
    # Calculate detail layer
    detail = img_float - smooth
    
    # Enhance detail
    enhanced = img_float + detail * strength
    
    # Clip and convert back
    enhanced = np.clip(enhanced * 255, 0, 255).astype(np.uint8)
    
    return enhanced


def process_blinds_photo(pil_image, enable_auto_crop=True, enable_perspective=True, 
                         enable_white_balance=True, enable_clarity=True):
    """
    Main processing pipeline for window blinds photos
    
    Args:
        pil_image: PIL Image
        enable_auto_crop: Enable smart auto-cropping
        enable_perspective: Enable perspective correction
        enable_white_balance: Enable white balance correction
        enable_clarity: Enable clarity enhancement
    
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
            cv2_img = enhance_clarity(cv2_img, strength=0.15)
        except Exception as e:
            print(f"Clarity enhancement failed: {e}")
    
    # Convert back to PIL
    return cv2_to_pil(cv2_img)
