#!/usr/bin/env python3
"""
InstaGen - School Instagram Content Generator
Takes photos, resizes for Instagram, generates captions with local AI.

Usage:
  instagen -i ~/Desktop/photos -e "Sports Day 2026"
  
Output:
  post/      - 1080x1080 square posts
  portrait/  - 1080x1350 portrait posts  
  reel/      - 1080x1920 reel covers
  story/     - 1080x1920 stories
  captions.txt - All captions ready to copy
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import shutil

# Configuration
SCHOOL_NAME = "Bodhana Learning Tree"
DEFAULT_FONT_SIZE = 60
CAPTION_MODEL = "gemma4:e4b-q4"  # Your local model

# Instagram specs
SIZES = {
    "post": (1080, 1080),      # Square
    "portrait": (1080, 1350),   # Portrait post
    "reel": (1080, 1920),       # Reel/Story
    "story": (1080, 1920),      # Story
}

def ensure_font():
    """Find a usable font on macOS."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    # Fallback - PIL default
    return None

def generate_caption(event_name, image_description=""):
    """Generate Instagram caption using local Gemma 4 via Ollama."""
    
    prompt = f"""Write a short, engaging Instagram caption for a school called "{SCHOOL_NAME}".
Event: {event_name}
{image_description}

Requirements:
- Max 2 sentences
- Warm, welcoming tone
- Include 3-5 relevant hashtags at the end
- No emojis
- Output ONLY the caption, nothing else

Caption:"""
    
    try:
        result = subprocess.run(
            ["ollama", "run", CAPTION_MODEL, prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        caption = result.stdout.strip()
        
        # Clean up Gemma 4 thinking/output junk
        # Remove common markers
        for marker in ["<thinking>", "</thinking>", "**Option", "Suggested Hashtags", 
                       "Here's a thinking process", "1.  **Analyze", "**Final Output**",
                       "***", "---"]:
            if marker in caption:
                # Take only text before marker or after closing tags
                if marker == "<thinking>":
                    parts = caption.split("</thinking>")
                    if len(parts) > 1:
                        caption = parts[-1].strip()
                elif marker.startswith("**"):
                    caption = caption.split(marker)[0].strip()
                else:
                    caption = caption.split(marker)[0].strip()
        
        # Remove any remaining markdown formatting
        caption = caption.replace("**", "").replace("*", "")
        
        # Extract just the caption text (look for "Caption:" prefix)
        if "Caption:" in caption:
            caption = caption.split("Caption:")[-1].strip()
        
        # Clean up hashtags - ensure they're at the end
        lines = [l.strip() for l in caption.split("\n") if l.strip()]
        if lines:
            caption = " ".join(lines)
        
        # If still empty or too short, fallback
        if len(caption) < 20:
            caption = f"{event_name} at {SCHOOL_NAME}! Join us for a day of learning and fun. #SchoolLife #Education #BodhanaLearningTree"
        
        return caption
    except Exception as e:
        print(f"⚠️  Caption generation failed: {e}")
        return f"{event_name} at {SCHOOL_NAME}! Join us for a day of learning and fun. #SchoolLife #Education #BodhanaLearningTree"

def add_text_overlay(image, text, position="bottom", font_size=DEFAULT_FONT_SIZE):
    """Add semi-transparent text bar with school name or caption."""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    # Try to load font
    font_path = ensure_font()
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Create semi-transparent overlay
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Text wrapping
    words = text.split()
    lines = []
    current_line = []
    max_width = width - 80
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = overlay_draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    if not lines:
        lines = [text]
    
    # Calculate text block height
    line_height = font_size + 10
    total_height = len(lines) * line_height + 40
    
    # Position
    if position == "bottom":
        y_start = height - total_height - 20
    elif position == "top":
        y_start = 20
    else:  # center
        y_start = (height - total_height) // 2
    
    # Draw background bar
    overlay_draw.rectangle(
        [(20, y_start - 10), (width - 20, y_start + total_height)],
        fill=(0, 0, 0, 180)
    )
    
    # Draw text
    y = y_start
    for line in lines:
        bbox = overlay_draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        overlay_draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height
    
    # Composite
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')

def process_image(input_path, output_dir, event_name, sizes_to_create):
    """Process a single image into multiple formats."""
    
    filename = Path(input_path).stem
    results = {}
    
    try:
        img = Image.open(input_path)
    except Exception as e:
        print(f"❌ Cannot open {input_path}: {e}")
        return results
    
    # Generate caption once per image
    caption = generate_caption(event_name, f"Photo showing {filename}")
    
    for size_name, (target_w, target_h) in sizes_to_create.items():
        # Create output directory
        size_dir = os.path.join(output_dir, size_name)
        os.makedirs(size_dir, exist_ok=True)
        
        # Resize with crop/fill
        img_copy = img.copy()
        img_w, img_h = img_copy.size
        
        # Calculate crop to maintain aspect ratio
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h
        
        if img_ratio > target_ratio:
            # Image is wider, crop width
            new_w = int(img_h * target_ratio)
            left = (img_w - new_w) // 2
            img_copy = img_copy.crop((left, 0, left + new_w, img_h))
        else:
            # Image is taller, crop height
            new_h = int(img_w / target_ratio)
            top = (img_h - new_h) // 2
            img_copy = img_copy.crop((0, top, img_w, top + new_h))
        
        # Resize to target
        img_copy = img_copy.resize((target_w, target_h), Image.LANCZOS)
        
        # Add overlays based on format
        if size_name == "post":
            img_copy = add_text_overlay(img_copy, SCHOOL_NAME, "bottom", 50)
        elif size_name == "reel":
            img_copy = add_text_overlay(img_copy, event_name, "top", 70)
            img_copy = add_text_overlay(img_copy, SCHOOL_NAME, "bottom", 50)
        elif size_name == "story":
            img_copy = add_text_overlay(img_copy, event_name, "top", 60)
            img_copy = add_text_overlay(img_copy, "Tap for more →", "bottom", 40)
        
        # Save
        output_path = os.path.join(size_dir, f"{filename}_{size_name}.jpg")
        img_copy.save(output_path, "JPEG", quality=95)
        
        results[size_name] = {
            "path": output_path,
            "caption": caption
        }
    
    return results

def create_content_package(input_dir, output_dir, event_name):
    """Process all images and create organized output."""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return False
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Supported formats
    extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}
    images = [f for f in input_path.iterdir() if f.suffix.lower() in extensions]
    
    if not images:
        print(f"❌ No images found in {input_dir}")
        return False
    
    print(f"🎓 Processing {len(images)} photos for: {event_name}")
    print(f"🏫 School: {SCHOOL_NAME}")
    print()
    
    # Determine which sizes to create
    sizes = {
        "post": SIZES["post"],
        "portrait": SIZES["portrait"],
        "reel": SIZES["reel"],
        "story": SIZES["story"],
    }
    
    all_results = {}
    captions_file = []
    
    for i, img_path in enumerate(sorted(images), 1):
        print(f"  [{i}/{len(images)}] Processing {img_path.name}...")
        
        results = process_image(str(img_path), str(output_path), event_name, sizes)
        all_results[img_path.stem] = results
        
        # Collect captions
        if results:
            first_size = list(results.keys())[0]
            caption = results[first_size]["caption"]
            captions_file.append(f"📸 {img_path.stem}\n{caption}\n")
    
    # Save captions
    captions_path = output_path / "captions.txt"
    with open(captions_path, "w") as f:
        f.write(f"🎓 {SCHOOL_NAME}\n")
        f.write(f"📅 Event: {event_name}\n")
        f.write(f"📊 Total photos: {len(images)}\n")
        f.write("=" * 50 + "\n\n")
        f.write("\n".join(captions_file))
    
    # Create summary
    summary = {
        "school": SCHOOL_NAME,
        "event": event_name,
        "total_photos": len(images),
        "output_folder": str(output_path),
        "sizes_created": list(sizes.keys()),
    }
    
    summary_path = output_path / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    print()
    print("✅ Done!")
    print(f"📁 Output: {output_path}")
    print(f"📄 Captions: {captions_path}")
    print()
    print("Folder structure:")
    for size_name in sizes.keys():
        size_dir = output_path / size_name
        count = len(list(size_dir.glob("*.jpg"))) if size_dir.exists() else 0
        print(f"  📂 {size_name}/ - {count} files")
    print()
    print("💡 Next steps:")
    print("  1. Review photos in output folders")
    print("  2. Pick best ones for Instagram")
    print("  3. Use captions.txt for copy-paste")
    print("  4. For better designs, run through Canva/Nano Banana")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="InstaGen - School Instagram Content Generator")
    parser.add_argument("--input", "-i", required=True, help="Input folder with photos")
    parser.add_argument("--output", "-o", default="~/Desktop/instagen_output", help="Output folder (default: ~/Desktop/instagen_output)")
    parser.add_argument("--event", "-e", required=True, help="Event name (e.g., 'Sports Day 2026')")
    parser.add_argument("--sizes", "-s", default="all", help="Sizes: all, post, reel, story")
    
    args = parser.parse_args()
    
    # Expand paths
    input_dir = os.path.expanduser(args.input)
    output_dir = os.path.expanduser(args.output)
    
    # Check dependencies
    try:
        from PIL import Image
    except ImportError:
        print("❌ Pillow not installed. Run: pip3 install Pillow")
        sys.exit(1)
    
    # Check Ollama
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
    except:
        print("❌ Ollama not found. Is it installed?")
        sys.exit(1)
    
    create_content_package(input_dir, output_dir, args.event)

if __name__ == "__main__":
    main()
