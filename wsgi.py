#!/usr/bin/env python
import sys
from app import app as application
import logging


def setup_flask_logging():
    # Log to stdout
    #handler = logging.StreamHandler(sys.stdout)
    # Log to a file
    handler = logging.FileHandler('./application.log')
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(funcName)s] %(levelname)s: %(message)s '
    ))
    application.logger.addHandler(handler)


def setup_gunicorn_logging():
    # fix gives access to the gunicorn error log facility
    application.logger.handlers.extend(logging.getLogger("gunicorn.error").handlers)
    # fix gives access to the gunicorn console log facility
    application.logger.handlers.extend(logging.getLogger("gunicorn").handlers)


# Set default log level for the general logger
# each handler can then restrict the messages logged
application.logger.setLevel(logging.INFO)
setup_flask_logging()
#setup_gunicorn_logging()


if __name__ == '__main__':
    application.run(port=5000, threaded=False)
