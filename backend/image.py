
import os
import base64
import tempfile
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def get_image_media_type(image_path: str) -> str:
    """Get the media type for an image based on extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return media_types.get(ext, 'image/png')

def preprocess_image_for_text(image_path: str) -> Optional[str]:
    """
    Preprocess image to enhance text readability for vision models.
    Returns path to temporary processed image, or None if preprocessing unavailable.
    
    Techniques:
    - Increase contrast to make text stand out
    - Slight sharpening to crisp up text edges
    """
    if not PIL_AVAILABLE:
        return None
    
    try:
        img = Image.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Increase contrast - helps text stand out from photos
        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(1.3)  # 30% more contrast
        
        # Slight sharpening - crisps up text
        img = img.filter(ImageFilter.SHARPEN)
        
        # Save to temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)
        img.save(temp_path, 'PNG')
        
        return temp_path
    
    except Exception as e:
        print(f"  ⚠️ Image preprocessing failed: {e}")
        return None
