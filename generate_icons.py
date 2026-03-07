"""Generate simple PWA icons for the recipe website."""
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, output_path):
    """Create a simple recipe book icon."""
    img = Image.new("RGB", (size, size), "#f97316")
    draw = ImageDraw.Draw(img)

    # Draw a simple pot/bowl shape
    center = size // 2
    radius = int(size * 0.3)

    # Bowl
    draw.ellipse(
        [center - radius, center - int(radius * 0.3),
         center + radius, center + int(radius * 0.9)],
        fill="#ffffff"
    )

    # Steam lines
    line_w = max(2, size // 50)
    for dx in [-radius // 2, 0, radius // 2]:
        x = center + dx
        y_start = center - int(radius * 0.5)
        y_end = center - int(radius * 1.0)
        draw.line([(x, y_start), (x - 3, y_end)], fill="#ffffff", width=line_w)

    img.save(output_path, quality=90)
    print(f"Created {output_path}")

if __name__ == "__main__":
    import os
    icons_dir = os.path.join(os.path.dirname(__file__), "static", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    create_icon(192, os.path.join(icons_dir, "icon-192.png"))
    create_icon(512, os.path.join(icons_dir, "icon-512.png"))
    print("Done!")
