import os
import multiprocessing

# Gunicorn production configuration for Sniply on Render Web Service

port = os.getenv("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Workers: Render free tier has 0.1 to 0.5 CPU, standard has 1-2 CPUs.
# Using 2-4 workers provides concurrency without memory exhaustion.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "sync"
worker_connections = 1000
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# Process naming
proc_name = "sniply-backend"

# Graceful restarts & memory management
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30
