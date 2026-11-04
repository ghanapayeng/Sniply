"""
URL Shortener — Flask + MongoDB.

Short-code generation is hand-rolled in shortener.py (base62 over our
own counter). QR generation uses the `qrcode` package because drawing
QR matrices by hand is out of scope — but the actual shortening logic
never touches a third-party shortening library.
"""

import hashlib
import io
import re
from datetime import datetime, timedelta, timezone

import qrcode
from flask import Flask, request, jsonify, redirect, render_template, send_file, abort

import db
import shortener

app = Flask(__name__)

URL_REGEX = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}"
    r"(?::\d+)?(?:/[^\s]*)?$"
)


def is_valid_url(url: str) -> bool:
    return bool(URL_REGEX.match(url))


def hash_password(password: str) -> str:
    # Simple salted sha256 — fine for a portfolio project; would use
    # bcrypt/argon2 in a real production system.
    salt = "url-shortener-salt"
    return hashlib.sha256((salt + password).encode()).hexdigest()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def api_shorten():
    data = request.get_json(force=True)
    long_url = (data.get("long_url") or "").strip()
    custom_alias = (data.get("custom_alias") or "").strip()
    expires_in_days = data.get("expires_in_days")
    password = data.get("password")

    if not long_url or not is_valid_url(long_url):
        return jsonify({"error": "Please provide a valid http(s) URL"}), 400

    expires_at = None
    if expires_in_days:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=float(expires_in_days))
        except (TypeError, ValueError):
            return jsonify({"error": "expires_in_days must be a number"}), 400

    password_hash = hash_password(password) if password else None

    if custom_alias:
        if not shortener.is_valid_custom_alias(custom_alias):
            return jsonify({"error": "Alias must be 3-20 chars: letters, digits, - or _"}), 400
        if not db.save_link(custom_alias, long_url, expires_at, password_hash):
            return jsonify({"error": "That alias is already taken"}), 409
        code = custom_alias
    else:
        # Retry loop guards against the rare base62 collision.
        for _ in range(5):
            counter = db.get_next_counter()
            code = shortener.generate_code_from_counter(counter)
            if db.save_link(code, long_url, expires_at, password_hash):
                break
        else:
            return jsonify({"error": "Could not generate a unique code, try again"}), 500

    return jsonify({
        "code": code,
        "short_url": request.host_url + code,
        "long_url": long_url,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "password_protected": password_hash is not None,
    }), 201


@app.route("/<code>")
def go(code):
    link = db.get_link(code)
    if not link:
        abort(404)

    if link.get("expires_at") and datetime.now(timezone.utc) > link["expires_at"].replace(tzinfo=timezone.utc):
        return render_template("expired.html"), 410

    if link.get("password_hash"):
        supplied = request.args.get("password")
        if not supplied or hash_password(supplied) != link["password_hash"]:
            return render_template("password.html", code=code), 401

    db.record_click(code, ip=request.remote_addr, referrer=request.referrer)
    return redirect(link["long_url"], code=302)


@app.route("/api/analytics/<code>")
def api_analytics(code):
    link = db.get_link(code)
    if not link:
        return jsonify({"error": "Not found"}), 404

    history = db.get_click_history(code)
    return jsonify({
        "code": code,
        "long_url": link["long_url"],
        "click_count": link["click_count"],
        "created_at": link["created_at"].isoformat(),
        "recent_clicks": [
            {"timestamp": c["timestamp"].isoformat(), "referrer": c["referrer"]}
            for c in history
        ],
    })


@app.route("/api/qr/<code>")
def api_qr(code):
    link = db.get_link(code)
    if not link:
        abort(404)

    short_url = request.host_url + code
    img = qrcode.make(short_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/links/<code>", methods=["DELETE"])
def api_delete(code):
    if db.delete_link(code):
        return jsonify({"deleted": True})
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    db.init_indexes()
    app.run(debug=True, port=5000)
