import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from backend.app import create_app

# Gunicorn entrypoint
app = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    app.run()

