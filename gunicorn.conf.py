# gunicorn.conf.py
import os

# The number of worker processes to serve the application.
# Rule of thumb: (2 * CPU cores) + 1
# import os
workers = 2 * os.cpu_count() + 1

# The type of worker to use. Sync is the default, but you can change it to gevent for asynchronous workers.
worker_class = 'sync'  # Options: 'sync', 'gevent', 'eventlet', 'uvicorn.workers.UvicornWorker' (for ASGI apps)

# The maximum number of simultaneous clients that each worker can handle (for sync workers).
worker_connections = 1000

# The address Gunicorn will bind to (IP:port or a Unix socket path).
bind = '127.0.0.1:8000'  # Bind to localhost on port 8000

# The number of threads per worker. Useful for handling multiple requests per worker concurrently.
threads = 10

# Maximum number of requests a worker will process before restarting (helps avoid memory leaks).
max_requests = 1000
max_requests_jitter = 50  # Adds a random jitter to max_requests to avoid thundering herd effect.

# Preload the application code before the workers are forked (can improve memory usage).
preload_app = True

# Timeout for workers to complete a request (in seconds).
# If exceeded, the worker is killed and restarted.
timeout = 30
