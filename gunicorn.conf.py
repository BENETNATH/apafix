"""Gunicorn configuration for production."""
import multiprocessing
import os

# Server socket
bind = os.environ.get("APAFIX_BIND", "0.0.0.0:8000")

# Worker processes
workers = int(os.environ.get("APAFIX_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
timeout = 120

# Logging
accesslog = os.environ.get("APAFIX_ACCESS_LOG", "/var/log/apafix/access.log")
errorlog = os.environ.get("APAFIX_ERROR_LOG", "/var/log/apafix/error.log")
loglevel = os.environ.get("APAFIX_LOG_LEVEL", "info")

# Process naming
proc_name = "apafix"

# PID file
pidfile = os.environ.get("APAFIX_PIDFILE", "/var/run/apafix/apafix.pid")

# Security
limit_request_line = 8190
limit_request_fields = 200
limit_request_field_size = 0  # No limit (XML forms can be large)
