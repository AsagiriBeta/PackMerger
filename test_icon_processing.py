#!/usr/bin/env python3
"""
Test script for custom icon processing
"""
from PIL import Image
from pathlib import Path
import io

def test_icon_processing():
    """Test that we can create and process a sample icon"""
    # Create a test image (red square)
    test_img = Image.new('RGB', (256, 256), color='red')

    # Save to bytes
    img_bytes = io.BytesIO()
    test_img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Open and process like the app does
    img = Image.open(img_bytes)

    # Convert to RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Crop to square (already square in this case)
    width, height = img.size
    if width != height:
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        img = img.crop((left, top, left + size, top + size))

    # Resize to 128x128
    img = img.resize((128, 128), Image.Resampling.LANCZOS)

    # Check final size
    assert img.size == (128, 128), f"Expected (128, 128), got {img.size}"
    assert img.mode == 'RGBA', f"Expected RGBA mode, got {img.mode}"

    print("✅ Icon processing test passed!")
    print(f"   - Final size: {img.size}")
    print(f"   - Final mode: {img.mode}")

if __name__ == '__main__':
    test_icon_processing()

