#!/usr/bin/env python
import os
from app import create_app
from logging.handlers import RotatingFileHandler
import sys
import logging

app = create_app(os.environ.get('FLASK_CONFIG', 'testing'))
application = app

handler = logging.StreamHandler(sys.stdout)
#handler = logging.FileHandler('./application.log')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(funcName)s] %(levelname)s: %(message)s '
))
app.logger.addHandler(handler)
# fix gives access to the gunicorn error log facility
app.logger.handlers.extend(logging.getLogger("gunicorn.error").handlers)
# fix gives access to the gunicorn console log facility
app.logger.handlers.extend(logging.getLogger("gunicorn").handlers)

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=5000)
    #app.run(host='127.0.0.1', port=5000)
