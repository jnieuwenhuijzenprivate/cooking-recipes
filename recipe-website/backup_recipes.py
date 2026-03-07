"""
Backup script: exports all recipes as JSON files and commits to GitHub.
Run manually or schedule as a daily task on PythonAnywhere.

Usage:
    python3 backup_recipes.py
"""
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "recipes.db")
BACKUP_DIR = os.path.join(BASE_DIR, "recipe_backups")


def export_recipes():
    """Export all recipes to individual JSON files in recipe_backups/."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    recipes = db.execute("SELECT * FROM recipes ORDER BY created_at").fetchall()

    # Clean out old backup files (to handle deleted recipes)
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(BACKUP_DIR, f))

    for recipe in recipes:
        recipe_data = dict(recipe)

        ingredients = db.execute(
            "SELECT text FROM ingredients WHERE recipe_id = ? ORDER BY sort_order",
            (recipe_data["id"],),
        ).fetchall()
        recipe_data["ingredients"] = [i["text"] for i in ingredients]

        steps = db.execute(
            "SELECT text FROM steps WHERE recipe_id = ? ORDER BY sort_order",
            (recipe_data["id"],),
        ).fetchall()
        recipe_data["steps"] = [s["text"] for s in steps]

        tags = db.execute(
            "SELECT name FROM tags WHERE recipe_id = ?",
            (recipe_data["id"],),
        ).fetchall()
        recipe_data["tags"] = [t["name"] for t in tags]

        # Use a safe filename based on title
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "" for c in recipe_data["title"]
        ).strip()[:60]
        filename = f"{safe_title}_{recipe_data['id'][:8]}.json"

        filepath = os.path.join(BACKUP_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(recipe_data, f, indent=2, ensure_ascii=False)

    db.close()
    return len(recipes)


def git_commit_and_push():
    """Stage backup files, uploaded images, and push to GitHub."""
    # Find the git repo root (may be a parent of BASE_DIR)
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=BASE_DIR,
    )
    repo_root = result.stdout.strip() if result.returncode == 0 else BASE_DIR
    os.chdir(repo_root)

    # Stage the backup JSON files and uploaded images (paths relative to repo root)
    subprocess.run(["git", "add", "--all", "recipe-website/recipe_backups/"], check=False)
    subprocess.run(["git", "add", "--all", "recipe-website/static/uploads/"], check=False)

    # Check if there are changes to commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
    )

    if result.returncode != 0:
        # There are staged changes
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        subprocess.run(
            ["git", "commit", "-m", f"Auto-backup recipes: {timestamp}"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        return True
    return False


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        print("No database found, nothing to back up.")
        sys.exit(0)

    count = export_recipes()
    print(f"Exported {count} recipes to {BACKUP_DIR}/")

    pushed = git_commit_and_push()
    if pushed:
        print("Changes committed and pushed to GitHub.")
    else:
        print("No changes to commit.")
