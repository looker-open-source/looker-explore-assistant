# Gunicorn configuration for Looker Explore Assistant REST API
# Optimized for Cloud Run deployment

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 8080)}"
backlog = 2048

# Worker processes
# For Cloud Run, use 1 worker to match single-container model
# Use threads for concurrency instead of multiple processes
workers = 1
worker_class = "sync"  # Can be upgraded to "gevent" or "uvicorn.workers.UvicornWorker" for async
worker_connections = 1000
threads = 8  # Handle concurrent requests with threads

# Worker lifecycle
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 300  # 5 minutes for long AI operations
keepalive = 2
graceful_timeout = 30

# Logging
accesslog = "-"  # Log to stdout for Cloud Run
errorlog = "-"   # Log to stderr for Cloud Run
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "looker-explore-assistant"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
worker_tmp_dir = "/dev/shm"  # Use memory for temporary files

# Environment-specific overrides
if os.environ.get("FLASK_ENV") == "development":
    # Development settings
    workers = 1
    threads = 4
    timeout = 120
    reload = True
    loglevel = "debug"
elif os.environ.get("CLOUD_RUN_SERVICE"):
    # Cloud Run specific optimizations
    workers = 1
    threads = int(os.environ.get("GUNICORN_THREADS", "8"))
    timeout = int(os.environ.get("GUNICORN_TIMEOUT", "300"))
    preload_app = True
    
    # Enable memory optimizations for Cloud Run
    max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
    max_requests_jitter = 50

# Startup/shutdown hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Looker Explore Assistant REST API")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Looker Explore Assistant REST API")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Looker Explore Assistant REST API ready to serve requests")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Shutting down Looker Explore Assistant REST API")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received INT/QUIT signal")

# Health check configuration
# Cloud Run will hit the /health endpoint for health checks