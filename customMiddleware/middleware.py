# myapp/middleware.py
import time
import logging
from django.utils.timezone import now

class RequestLogMiddleware:
    """
    Middleware that logs each request's processing time,
    client IP address, and User-Agent string to a file.
    """

    def __init__(self, get_response):
        """
        One-time configuration and initialization.
        """
        self.get_response = get_response

        # Set up a file logger for request logs
        self.logger = logging.getLogger('request_logger')
        self.logger.setLevel(logging.INFO)

        # Create a file handler that writes to 'logs/requests.log'
        file_handler = logging.FileHandler('logs/requests.log')
        file_handler.setLevel(logging.INFO)

        # Define a simple log format
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def __call__(self, request):
        """
        Called for each request. This method does the actual logging.
        """
        # Skip logging for static and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Record the start time (in seconds since epoch)
        start_time = time.time()

        # Process the request and get the response from the next middleware/view
        response = self.get_response(request)

        # Calculate elapsed time
        elapsed_ms = (time.time() - start_time) * 1000

        # Extract client IP (handles proxy headers if used)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')

        # Extract User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Build the log message
        log_message = (
            f"IP: {ip} | "
            f"User-Agent: {user_agent} | "
            f"Method: {request.method} | "
            f"Path: {request.get_full_path()} | "
            f"Status: {response.status_code} | "
            f"Time: {elapsed_ms:.2f}ms"
        )

        # Write to the log file
        self.logger.info(log_message)

        # Return the response unchanged
        return response