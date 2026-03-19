import sqlite3

from flask import Flask, g, redirect, render_template, request, url_for

app = Flask(__name__)
DATABASE = "memos.db"


def get_db():
    """Get database connection for current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()


with app.app_context():
    init_db()


@app.route("/")
def index():
    """Display all memos."""
    db = get_db()
    memos = db.execute("SELECT * FROM memos ORDER BY created_at DESC").fetchall()
    return render_template("index.html", memos=memos)


@app.route("/add", methods=["POST"])
def add_memo():
    """Add a new memo."""
    content = request.form.get("content", "").strip()
    if content:
        db = get_db()
        db.execute("INSERT INTO memos (content) VALUES (?)", (content,))
        db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:memo_id>", methods=["POST"])
def delete_memo(memo_id):
    """Delete a memo by ID."""
    db = get_db()
    db.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
