'''
Docstring for research_and_analyst.logger.custom_logger
--  Tracking the execution of project
'''

import os
import logging
from datetime import datetime
import structlog

class CustomLogger:
    def __init__(self, log_dir="logs"):
        # Ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Timestamped log file (for persistence)
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        self.log_file_path = os.path.join(self.logs_dir, log_file)

    def get_logger(self, name=__file__):
        logger_name = os.path.basename(name)

        # Configure logging for console + file (both JSON)
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s"))  # Raw JSON lines

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",  # Structlog will handle JSON rendering
            handlers=[console_handler, file_handler]
        )

        # Configure structlog for JSON structured logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
                structlog.processors.add_log_level,
                structlog.processors.EventRenamer(to="event"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        return structlog.get_logger(logger_name)

if __name__ == "__main__":
    logger = CustomLogger().get_logger(__file__) # __file__ -> it gives the exact file name which is execcute
    logger.info("User uploaded a file", user_id=123, filename="report.pdf")
    logger.error("Failed to process PDF", error="File not found", user_id=123)
    
    
# Create a production-ready Python custom logger class that automatically creates a logs/ directory if it does not already exist and generates a timestamp-based log file name for persistent logging. The logger should log messages to both the console and a file simultaneously. Use the structlog library to implement structured JSON logging. Ensure that each log entry includes an ISO 8601 UTC timestamp and the log level in the output. The logs must be rendered in proper JSON format. The logger should support passing additional contextual fields such as user_id, filename, error, or any custom metadata dynamically. Finally, the class should return a reusable logger instance that can be used across the application.


# import structlog
# import logging
# import sys
# from datetime import datetime

# # Configure structlog to output JSON to stdout for structured logging
# structlog.configure(
#     processors=[
#         structlog.stdlib.filter_by_level,
#         structlog.stdlib.add_logger_name,
#         structlog.stdlib.add_log_level,
#         structlog.stdlib.PositionalArgumentsFormatter(),
#         structlog.processors.TimeStamper(fmt="iso"),
#         structlog.processors.StackInfoRenderer(),
#         structlog.processors.format_exc_info,
#         structlog.processors.UnicodeDecoder(),
#         structlog.processors.JSONRenderer()
#     ],
#     context_class=dict,
#     logger_factory=structlog.stdlib.LoggerFactory(),
#     wrapper_class=structlog.stdlib.BoundLogger,
#     cache_logger_on_first_use=True,
# )

# # Get a logger instance
# logger = structlog.get_logger()

# def log_execution_start(function_name, *args, **kwargs):
#     """Log the start of a function execution."""
#     logger.info("Execution started", function=function_name, args=args, kwargs=kwargs)

# def log_execution_end(function_name, result=None):
#     """Log the end of a function execution."""
#     logger.info("Execution ended", function=function_name, result=result)

# def log_error(function_name, error):
#     """Log an error during execution."""
#     logger.error("Execution error", function=function_name, error=str(error), exc_info=True)

# # Example usage (can be removed or used in other files)
# if __name__ == "__main__":
#     log_execution_start("example_function", arg1="value1")
#     # Simulate some work
#     try:
#         # Your code here
#         result = "success"
#         log_execution_end("example_function", result=result)
#     except Exception as e:
#         log_error("example_function", e)