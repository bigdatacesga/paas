#!/usr/bin/env python
import logging
import sys
from app import app as application


def setup_flask_logging():
    # Log to stdout
    handler = logging.StreamHandler(sys.stdout)
    # Log to a file
    #handler = logging.FileHandler('./application.log')
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(funcName)s] %(levelname)s: %(message)s '
    ))
    application.logger.addHandler(handler)


# Set default log level for the general logger
# each handler can then restrict the messages logged
application.logger.setLevel(logging.INFO)
setup_flask_logging()


if __name__ == '__main__':
    application.run(port=6000, threaded=False)
