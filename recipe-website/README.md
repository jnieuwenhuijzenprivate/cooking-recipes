# Jonah's Smullenboek 🍳

A mobile-first personal recipe website built with Flask + SQLite + Tailwind CSS.

## Features

- **Mobile-first design** — Optimized for phones with a bottom navigation bar, large touch targets, and responsive layout
- **Quick recipe upload** — Add recipes from your phone with photo capture directly from camera
- **Image support** — Photos are auto-rotated (EXIF) and resized for fast loading
- **Search & filter** — Find recipes by name or filter by category
- **PWA support** — Add to home screen on your phone for an app-like experience
- **Ingredient checklist** — Check off ingredients while cooking
- **Optional PIN protection** — Lock editing behind a simple PIN
- **API endpoint** — Quick-add recipes via API (useful for Shortcuts/automation)

## Quick Start

```bash
cd recipe-website
python3 -m pip install -r requirements.txt
python3 app.py
```

Open http://localhost:5000 on your phone (same Wi-Fi network) or browser.

## Add to Home Screen (iOS / Android)

1. Open the site in Safari (iOS) or Chrome (Android)
2. Tap **Share** → **Add to Home Screen**
3. The app will work in standalone mode like a native app

## PIN Protection

To protect recipe editing, set a PIN in your `.env` file:

```
APP_PIN=1234
```

## API Quick-Add

You can add recipes via API (useful for Siri Shortcuts, etc.):

```bash
curl -X POST http://localhost:5000/api/recipes \
  -H "Content-Type: application/json" \
  -d '{"title": "Quick Pasta", "ingredients": "pasta\nsauce", "steps": "cook\neat"}'
```

If PIN is set, add: `-H "Authorization: Bearer 1234"`

## Deployment

For public access, deploy to a cloud service like:
- **Railway** / **Render** — easiest, free tier available
- **PythonAnywhere** — free Python hosting
- **VPS with nginx** — more control

For production, set a proper `SECRET_KEY` in `.env`.
