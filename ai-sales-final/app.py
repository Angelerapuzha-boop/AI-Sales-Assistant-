"""
AI Sales Assistant — Flask 3.1
Render: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
Local:  python app.py
"""
import logging
import os

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sales")

# ── Absolute paths so gunicorn finds templates no matter what cwd is ──────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMPL_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static") if os.path.isdir(os.path.join(BASE_DIR, "static")) else None

from flask import Flask, render_template, jsonify

app = Flask(__name__,
            template_folder=TMPL_DIR,
            static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "ai-sales-secret-key-32chars-2024!")

# ── Register API blueprint ────────────────────────────────────────────────────
from routes_api import api as api_bp
app.register_blueprint(api_bp)

# ── Initialise DB at import time (works for gunicorn multi-worker) ────────────
try:
    from database import init_db
    init_db()
    logger.info("✅ Database ready")
except Exception as _e:
    logger.error(f"DB init failed: {_e}")

# ── Start scheduler ───────────────────────────────────────────────────────────
try:
    from scheduler import start as _sched_start
    _sched_start()
    logger.info("✅ Scheduler started")
except Exception as _e:
    logger.warning(f"Scheduler skipped: {_e}")

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/<path:subpath>")
def catch_all(subpath):
    # Pass /api/* through to the blueprint; serve index for everything else
    return render_template("index.html")

@app.get("/health")
def health():
    from database import q
    try:
        cos = len(q("SELECT id FROM companies"))
        db_ok = True
    except Exception:
        cos, db_ok = 0, False
    return jsonify({
        "status":   "healthy" if db_ok else "degraded",
        "database": db_ok,
        "companies": cos,
        "groq":     bool(os.environ.get("GROQ_API_KEY")),
        "twilio":   bool(os.environ.get("TWILIO_ACCOUNT_SID")),
        "bland":    bool(os.environ.get("BLAND_API_KEY")),
        "gmail":    bool(os.environ.get("GMAIL_SENDER_EMAIL")),
    })

# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    # SPA: always return index so front-end router handles it
    try:
        return render_template("index.html"), 200
    except Exception:
        return "<h1>AI Sales Assistant</h1><p>Loading...</p>", 200

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"ok": False, "error": "Method not allowed"}), 405

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500: {e}")
    return jsonify({"ok": False, "error": "Internal server error — check logs"}), 500

# ── Local dev entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 http://localhost:{port}")
    logger.info("   Login: admin@salesai.com / Admin@123456")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
