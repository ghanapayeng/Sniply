import os
from backend.app import create_app

# Gunicorn entrypoint
app = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    app.run()
