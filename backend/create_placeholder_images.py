#!/usr/bin/env python3
"""
Create placeholder images for the e-commerce products
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Create the images directory if it doesn't exist
os.makedirs('/Users/elloukelie/workspace/github.com/elloukelie/final_ecom/backend/static/images', exist_ok=True)

# Define product images to create
products = [
    ('macbook-pro.jpg', 'MacBook Pro 16"', '#1d1d1f'),
    ('dell-xps-13.jpg', 'Dell XPS 13', '#0066cc'),
    ('logitech-mx-master.jpg', 'MX Master 3S', '#00b8d4'),
    ('mechanical-keyboard.jpg', 'RGB Keyboard', '#ff6b35'),
    ('iphone-15-pro.jpg', 'iPhone 15 Pro', '#1d1d1f'),
    ('samsung-s24-ultra.jpg', 'Galaxy S24 Ultra', '#5f2c82'),
    ('sony-headphones.jpg', 'Sony WH-1000XM5', '#000000'),
    ('ipad-air.jpg', 'iPad Air', '#1d1d1f'),
    ('asus-monitor.jpg', 'ASUS ROG Monitor', '#ff0040'),
    ('razer-mouse.jpg', 'Razer DeathAdder', '#00ff00')
]

def create_placeholder_image(filename, product_name, bg_color):
    # Create a 400x400 image
    img = Image.new('RGB', (400, 400), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic font if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw product name
    text_bbox = draw.textbbox((0, 0), product_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Center the text
    x = (400 - text_width) // 2
    y = (400 - text_height) // 2
    
    # Draw white text
    draw.text((x, y), product_name, fill='white', font=font)
    
    # Draw "PLACEHOLDER" at the bottom
    placeholder_text = "PLACEHOLDER IMAGE"
    placeholder_bbox = draw.textbbox((0, 0), placeholder_text, font=small_font)
    placeholder_width = placeholder_bbox[2] - placeholder_bbox[0]
    px = (400 - placeholder_width) // 2
    py = 350
    draw.text((px, py), placeholder_text, fill='white', font=small_font)
    
    # Save the image
    filepath = f'/Users/elloukelie/workspace/github.com/elloukelie/final_ecom/backend/static/images/{filename}'
    img.save(filepath, 'JPEG', quality=85)
    print(f"Created: {filepath}")

# Create all placeholder images
for filename, product_name, bg_color in products:
    create_placeholder_image(filename, product_name, bg_color)

print("All placeholder images created successfully!")
