# URL Shortener — Flask + MongoDB

Matches the infographic: long URL in → hash generator → redirect → click
analytics → database store, plus custom aliases, expiration, password
protection, and QR codes.

## What's hand-rolled vs. what's a library

- **Short-code generation** (`shortener.py`): built from scratch — our own
  base62 alphabet, our own encoder/decoder, our own counter-salting so
  codes aren't sequential/guessable. No `shortuuid`, `hashids`, or
  `pyshorteners`.
- **Web framework** (Flask) and **DB driver** (`pymongo`) are used as
  infrastructure, the same way you'd use them for any backend — the point
  was to not offload the *shortening logic itself* to a library.
- **QR codes**: uses the `qrcode` package. Drawing QR matrices by hand is
  a separate (large) problem from URL shortening, so this one's a
  deliberate exception — say the word if you'd rather that be hand-rolled
  too or dropped entirely.

## Setup

1. Install MongoDB locally (or point at a remote instance / MongoDB Atlas
   free tier) and make sure it's running on `localhost:27017`, or set:
   ```
   export MONGO_URI="mongodb://<host>:<port>"
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run it:
   ```
   python app.py
   ```
   Visit `http://localhost:5000`.

## API

- `POST /api/shorten` — body: `{long_url, custom_alias?, expires_in_days?, password?}`
- `GET /<code>` — redirects to the long URL (records a click; prompts for
  password if set; shows an expired page if past `expires_at`)
- `GET /api/analytics/<code>` — click count + recent click history
- `GET /api/qr/<code>` — PNG QR code for the short link
- `DELETE /api/links/<code>` — remove a link

## Data model (MongoDB)

- `links`: `{code, long_url, created_at, expires_at, password_hash, click_count}`
- `clicks`: `{code, timestamp, ip, referrer}` — one doc per click, for analytics
- `counters`: `{_id: "link_id", seq}` — Mongo has no native auto-increment,
  so this collection provides one for the short-code generator

## Notes

- Password hashing here is salted SHA-256 for simplicity — swap in
  `bcrypt`/`argon2` before using this for anything real.
- Not tested end-to-end in this environment (no MongoDB server available
  here), but the shortening/encoding logic was tested in isolation and
  all files compile cleanly. Test it against your own Mongo instance
  before relying on it.
