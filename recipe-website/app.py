import os
import sqlite3
import uuid
import secrets
import threading
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, send_from_directory, g, session
)
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "recipes.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic"}
MAX_IMAGE_SIZE = 800  # max width/height in pixels

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            servings TEXT,
            prep_time TEXT,
            cook_time TEXT,
            category TEXT,
            image_filename TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            text TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            text TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        );
    """)
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Auth – simple PIN / password protection (optional)
# ---------------------------------------------------------------------------

APP_PIN = os.environ.get("APP_PIN")  # Set to enable PIN protection


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if APP_PIN and not session.get("authenticated"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if not APP_PIN:
        return redirect(url_for("index"))
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("pin", ""), APP_PIN):
            session["authenticated"] = True
            next_url = request.args.get("next", url_for("index"))
            return redirect(next_url)
        flash("Incorrect PIN", "error")
    return render_template("login.html")


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file):
    """Save and resize an uploaded image, return the filename."""
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None

    # Always save as JPEG for smaller file size
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    img = Image.open(file.stream)
    # Auto-rotate based on EXIF
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img)
    # Resize if too large
    img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.LANCZOS)
    # Convert to RGB for JPEG
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    img.save(filepath, format="JPEG", quality=70, optimize=True)
    return filename


def delete_image(filename):
    if filename:
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Breakfast", "Lunch", "Dinner", "Appetizer", "Snack",
    "Dessert", "Soup", "Salad", "Baking", "Drinks", "Other"
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = "SELECT * FROM recipes"
    params = []
    conditions = []

    if search:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if category:
        conditions.append("category = ?")
        params.append(category)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    recipes = db.execute(query, params).fetchall()

    # Get tags for each recipe
    recipes_with_tags = []
    for r in recipes:
        tags = db.execute(
            "SELECT name FROM tags WHERE recipe_id = ?", (r["id"],)
        ).fetchall()
        recipes_with_tags.append({**dict(r), "tags": [t["name"] for t in tags]})

    return render_template(
        "index.html",
        recipes=recipes_with_tags,
        search=search,
        category=category,
        categories=CATEGORIES,
    )


@app.route("/recipe/<recipe_id>")
def recipe_detail(recipe_id):
    db = get_db()
    recipe = db.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if not recipe:
        flash("Recipe not found", "error")
        return redirect(url_for("index"))

    ingredients = db.execute(
        "SELECT text FROM ingredients WHERE recipe_id = ? ORDER BY sort_order",
        (recipe_id,),
    ).fetchall()
    steps = db.execute(
        "SELECT text FROM steps WHERE recipe_id = ? ORDER BY sort_order",
        (recipe_id,),
    ).fetchall()
    tags = db.execute(
        "SELECT name FROM tags WHERE recipe_id = ?", (recipe_id,)
    ).fetchall()

    return render_template(
        "detail.html",
        recipe=dict(recipe),
        ingredients=[i["text"] for i in ingredients],
        steps=[s["text"] for s in steps],
        tags=[t["name"] for t in tags],
    )


@app.route("/recipe/new", methods=["GET", "POST"])
@login_required
def recipe_new():
    if request.method == "POST":
        return _save_recipe(None)
    return render_template("form.html", recipe=None, categories=CATEGORIES)


@app.route("/recipe/<recipe_id>/edit", methods=["GET", "POST"])
@login_required
def recipe_edit(recipe_id):
    db = get_db()
    recipe = db.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if not recipe:
        flash("Recipe not found", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        return _save_recipe(recipe_id)

    ingredients = db.execute(
        "SELECT text FROM ingredients WHERE recipe_id = ? ORDER BY sort_order",
        (recipe_id,),
    ).fetchall()
    steps = db.execute(
        "SELECT text FROM steps WHERE recipe_id = ? ORDER BY sort_order",
        (recipe_id,),
    ).fetchall()
    tags = db.execute(
        "SELECT name FROM tags WHERE recipe_id = ?", (recipe_id,)
    ).fetchall()

    recipe_data = dict(recipe)
    recipe_data["ingredients"] = [i["text"] for i in ingredients]
    recipe_data["steps"] = [s["text"] for s in steps]
    recipe_data["tags"] = [t["name"] for t in tags]

    return render_template("form.html", recipe=recipe_data, categories=CATEGORIES)


def _save_recipe(recipe_id):
    db = get_db()
    now = datetime.utcnow().isoformat()

    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required", "error")
        return redirect(request.url)

    description = request.form.get("description", "").strip()
    servings = request.form.get("servings", "").strip()
    prep_time = request.form.get("prep_time", "").strip()
    cook_time = request.form.get("cook_time", "").strip()
    category = request.form.get("category", "").strip()
    ingredients_raw = request.form.get("ingredients", "").strip()
    steps_raw = request.form.get("steps", "").strip()
    tags_raw = request.form.get("tags", "").strip()

    # Handle image
    image_filename = None
    file = request.files.get("image")
    if file and file.filename:
        image_filename = save_image(file)

    if recipe_id:
        # Update
        old = db.execute("SELECT image_filename FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        if image_filename and old and old["image_filename"]:
            delete_image(old["image_filename"])
        if not image_filename and old:
            image_filename = old["image_filename"]

        # Check if user wants to remove image
        if request.form.get("remove_image") == "1":
            if old and old["image_filename"]:
                delete_image(old["image_filename"])
            image_filename = None

        db.execute("""
            UPDATE recipes SET title=?, description=?, servings=?, prep_time=?,
            cook_time=?, category=?, image_filename=?, updated_at=?
            WHERE id=?
        """, (title, description, servings, prep_time, cook_time, category,
              image_filename, now, recipe_id))
    else:
        # Insert
        recipe_id = uuid.uuid4().hex
        db.execute("""
            INSERT INTO recipes (id, title, description, servings, prep_time,
            cook_time, category, image_filename, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (recipe_id, title, description, servings, prep_time, cook_time,
              category, image_filename, now, now))

    # Replace ingredients
    db.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    for i, line in enumerate(ingredients_raw.splitlines()):
        line = line.strip()
        if line:
            db.execute(
                "INSERT INTO ingredients (recipe_id, sort_order, text) VALUES (?, ?, ?)",
                (recipe_id, i, line),
            )

    # Replace steps
    db.execute("DELETE FROM steps WHERE recipe_id = ?", (recipe_id,))
    for i, line in enumerate(steps_raw.splitlines()):
        line = line.strip()
        if line:
            db.execute(
                "INSERT INTO steps (recipe_id, sort_order, text) VALUES (?, ?, ?)",
                (recipe_id, i, line),
            )

    # Replace tags
    db.execute("DELETE FROM tags WHERE recipe_id = ?", (recipe_id,))
    for tag in tags_raw.split(","):
        tag = tag.strip()
        if tag:
            db.execute(
                "INSERT INTO tags (recipe_id, name) VALUES (?, ?)",
                (recipe_id, tag),
            )

    db.commit()
    flash("Recipe saved!", "success")
    trigger_backup()
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.route("/recipe/<recipe_id>/delete", methods=["POST"])
@login_required
def recipe_delete(recipe_id):
    db = get_db()
    recipe = db.execute("SELECT image_filename FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if recipe:
        delete_image(recipe["image_filename"])
        db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        db.commit()
        flash("Recipe deleted", "success")
        trigger_backup()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Auto-backup to GitHub (runs in background thread)
# ---------------------------------------------------------------------------

def run_backup():
    """Export recipes and push to GitHub in a background thread."""
    try:
        from backup_recipes import export_recipes, git_commit_and_push
        export_recipes()
        git_commit_and_push()
    except Exception as e:
        app.logger.warning(f"Auto-backup failed: {e}")

def trigger_backup():
    """Fire-and-forget backup so it doesn't slow down the request."""
    threading.Thread(target=run_backup, daemon=True).start()


# ---------------------------------------------------------------------------
# API endpoint for quick-add (useful for mobile shortcuts / Siri / etc.)
# ---------------------------------------------------------------------------

@app.route("/api/recipes", methods=["POST"])
def api_add_recipe():
    """Quick-add API: accepts JSON or form data."""
    if APP_PIN:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not secrets.compare_digest(auth[7:], APP_PIN):
            return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    db = get_db()
    now = datetime.utcnow().isoformat()
    recipe_id = uuid.uuid4().hex

    db.execute("""
        INSERT INTO recipes (id, title, description, servings, prep_time,
        cook_time, category, image_filename, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
    """, (
        recipe_id,
        title,
        (data.get("description") or "").strip(),
        (data.get("servings") or "").strip(),
        (data.get("prep_time") or "").strip(),
        (data.get("cook_time") or "").strip(),
        (data.get("category") or "").strip(),
        now, now,
    ))

    for i, line in enumerate((data.get("ingredients") or "").splitlines()):
        line = line.strip()
        if line:
            db.execute(
                "INSERT INTO ingredients (recipe_id, sort_order, text) VALUES (?, ?, ?)",
                (recipe_id, i, line),
            )

    for i, line in enumerate((data.get("steps") or "").splitlines()):
        line = line.strip()
        if line:
            db.execute(
                "INSERT INTO steps (recipe_id, sort_order, text) VALUES (?, ?, ?)",
                (recipe_id, i, line),
            )

    db.commit()
    return jsonify({"id": recipe_id, "url": url_for("recipe_detail", recipe_id=recipe_id)}), 201


# ---------------------------------------------------------------------------
# PWA service worker & manifest
# ---------------------------------------------------------------------------

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "My Recipe Book",
        "short_name": "Recipes",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#f97316",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


@app.route("/sw.js")
def service_worker():
    return send_from_directory("static/js", "sw.js", mimetype="application/javascript")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
