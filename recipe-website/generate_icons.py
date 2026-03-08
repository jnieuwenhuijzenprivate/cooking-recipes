"""Generate PWA icons for Jonah's Smullenboek."""
import math
from PIL import Image, ImageDraw


def _smooth_polygon(draw, points, fill, steps=60):
    """Draw a filled shape from control points using smooth interpolation."""
    # Simple closed cardinal spline for smoother outlines
    n = len(points)
    smooth = []
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        for t_step in range(steps):
            t = t_step / steps
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2 * p1[0]) +
                        (-p0[0] + p2[0]) * t +
                        (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                        (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) +
                        (-p0[1] + p2[1]) * t +
                        (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                        (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            smooth.append((x, y))
    draw.polygon(smooth, fill=fill)


def create_icon(size, output_path):
    """Create a smullen face with premium fork & knife in olive green."""
    ss = 4
    s = size * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Olive green rounded-rect background
    corner = s // 5
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=corner, fill="#6B7F3B")

    cx = s // 2
    cy = int(s * 0.50)

    # --- Happy smullen face ---
    face_r = int(s * 0.26)
    draw.ellipse([cx - face_r, cy - face_r, cx + face_r, cy + face_r], fill="#FFE0B2")

    # Blissful closed eyes
    eye_y = cy - int(face_r * 0.12)
    eye_spread = int(face_r * 0.40)
    eye_w = max(3, s // 45)
    eye_r = int(face_r * 0.20)
    draw.arc([cx - eye_spread - eye_r, eye_y - eye_r,
              cx - eye_spread + eye_r, eye_y + eye_r],
             start=200, end=340, fill="#3E2723", width=eye_w)
    draw.arc([cx + eye_spread - eye_r, eye_y - eye_r,
              cx + eye_spread + eye_r, eye_y + eye_r],
             start=200, end=340, fill="#3E2723", width=eye_w)

    # Rosy cheeks
    cheek_r = int(face_r * 0.14)
    cheek_y = cy + int(face_r * 0.12)
    cheek_spread = int(face_r * 0.52)
    draw.ellipse([cx - cheek_spread - cheek_r, cheek_y - cheek_r,
                  cx - cheek_spread + cheek_r, cheek_y + cheek_r], fill="#E8A087")
    draw.ellipse([cx + cheek_spread - cheek_r, cheek_y - cheek_r,
                  cx + cheek_spread + cheek_r, cheek_y + cheek_r], fill="#E8A087")

    # Open mouth (smullen!)
    mouth_w = int(face_r * 0.45)
    mouth_h = int(face_r * 0.32)
    mouth_y = cy + int(face_r * 0.30)
    draw.ellipse([cx - mouth_w, mouth_y - mouth_h // 3,
                  cx + mouth_w, mouth_y + mouth_h], fill="#C62828")
    tongue_w = int(mouth_w * 0.45)
    draw.ellipse([cx - tongue_w, mouth_y + int(mouth_h * 0.20),
                  cx + tongue_w, mouth_y + mouth_h], fill="#EF5350")

    # --- Premium utensils ---
    silver_fill = "#E8E8E8"
    silver_highlight = "#FFFFFF"
    silver_shadow = "#B0B0B0"
    utensil_top = int(s * 0.12)
    utensil_bot = int(s * 0.85)

    # ======= FORK (left side) — elegant dinner fork =======
    fx = cx - int(s * 0.35)
    fw = int(s * 0.018)

    # Dimensions
    tine_top = utensil_top
    tine_len = int(s * 0.15)
    tine_bottom = tine_top + tine_len
    neck_bottom = tine_bottom + int(s * 0.08)
    shoulder_bottom = neck_bottom + int(s * 0.04)

    # Draw handle first (behind everything)
    _smooth_polygon(draw, [
        (fx - fw * 0.5, neck_bottom),
        (fx - fw * 1.4, shoulder_bottom),
        (fx - fw * 1.1, utensil_bot - int(s * 0.04)),
        (fx - fw * 0.5, utensil_bot),
        (fx + fw * 0.5, utensil_bot),
        (fx + fw * 1.1, utensil_bot - int(s * 0.04)),
        (fx + fw * 1.4, shoulder_bottom),
        (fx + fw * 0.5, neck_bottom),
    ], fill=silver_fill, steps=40)

    # Handle highlight
    draw.line([(fx, shoulder_bottom + int(s * 0.02)), (fx, utensil_bot - int(s * 0.03))],
              fill=silver_highlight, width=max(1, int(fw * 0.4)))

    # Neck (narrow connecting piece, widens at tines)
    tine_spread = int(s * 0.035)  # total half-width at tine base
    draw.polygon([
        (fx - int(fw * 0.45), neck_bottom),
        (fx - tine_spread, tine_bottom),
        (fx + tine_spread, tine_bottom),
        (fx + int(fw * 0.45), neck_bottom),
    ], fill=silver_fill)
    # Neck highlight
    draw.line([(fx, tine_bottom + int(s * 0.01)), (fx, neck_bottom)],
              fill=silver_highlight, width=max(1, int(fw * 0.3)))

    # Four tines — elegant with rounded tips and gaps between them
    n_tines = 4
    total_tine_width = tine_spread * 2
    gap_w = max(2, int(s * 0.005))
    single_tine_w = (total_tine_width - (n_tines - 1) * gap_w) // n_tines

    for i in range(n_tines):
        t_left = fx - tine_spread + i * (single_tine_w + gap_w)
        t_right = t_left + single_tine_w
        t_cx = (t_left + t_right) / 2
        # Rounded-rect tine
        draw.rounded_rectangle(
            [int(t_left), tine_top, int(t_right), tine_bottom + int(s * 0.005)],
            radius=max(2, single_tine_w // 2), fill=silver_fill)
        # Highlight per tine
        draw.line([(int(t_cx), tine_top + max(2, single_tine_w)),
                   (int(t_cx), tine_bottom - int(s * 0.005))],
                  fill=silver_highlight, width=max(1, single_tine_w // 4))

    # ======= KNIFE (right side) — elegant chef's knife, edge facing left =======
    kx = cx + int(s * 0.35)
    kw = int(s * 0.018)

    blade_bottom = utensil_top + int(s * 0.38)

    # Blade (spine = right/straight side, edge = left/curved side facing inward)
    belly = int(s * 0.022)
    blade_pts = [
        (kx + kw * 0.3, utensil_top),                                   # tip (top)
        (kx + kw * 0.8, utensil_top + int(s * 0.02)),                   # spine side near tip
        (kx + kw * 1.0, blade_bottom),                                  # spine at bolster
        (kx + kw * 1.3, blade_bottom),                                  # bolster right
        (kx - kw * 1.3, blade_bottom),                                  # bolster left
        (kx - kw * 1.0 - belly * 0.3, blade_bottom - int(s * 0.02)),   # edge near bolster
        (kx - kw * 1.2 - belly, blade_bottom - int(s * 0.12)),         # edge belly
        (kx - kw * 0.8 - belly * 0.6, blade_bottom - int(s * 0.24)),   # edge curving up
        (kx - kw * 0.2, utensil_top + int(s * 0.02)),                   # edge near tip
    ]
    _smooth_polygon(draw, blade_pts, fill=silver_fill, steps=30)

    # Blade highlight
    hl_x = kx + int(kw * 0.3)
    draw.line([(hl_x, utensil_top + int(s * 0.04)), (hl_x, blade_bottom - int(s * 0.02))],
              fill=silver_highlight, width=max(1, int(kw * 0.5)))

    # Bolster
    bolster_h = int(s * 0.012)
    draw.rounded_rectangle(
        [kx - int(kw * 1.4), blade_bottom - bolster_h,
         kx + int(kw * 1.4), blade_bottom + bolster_h],
        radius=bolster_h // 2, fill=silver_shadow)

    # Handle
    _smooth_polygon(draw, [
        (kx - kw * 1.1, blade_bottom + bolster_h),
        (kx - kw * 1.3, blade_bottom + int(s * 0.06)),
        (kx - kw * 1.0, utensil_bot - int(s * 0.02)),
        (kx - kw * 0.5, utensil_bot),
        (kx + kw * 0.5, utensil_bot),
        (kx + kw * 1.0, utensil_bot - int(s * 0.02)),
        (kx + kw * 1.3, blade_bottom + int(s * 0.06)),
        (kx + kw * 1.1, blade_bottom + bolster_h),
    ], fill="#5a5a5a", steps=40)

    # Handle highlight
    draw.line([(kx, blade_bottom + int(s * 0.03)), (kx, utensil_bot - int(s * 0.03))],
              fill="#787878", width=max(1, int(kw * 0.4)))

    # Downsample with antialiasing
    img = img.resize((size, size), Image.LANCZOS)
    img.save(output_path, quality=95)
    print(f"Created {output_path}")

if __name__ == "__main__":
    import os
    icons_dir = os.path.join(os.path.dirname(__file__), "static", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    create_icon(192, os.path.join(icons_dir, "icon-192.png"))
    create_icon(512, os.path.join(icons_dir, "icon-512.png"))
    print("Done!")
