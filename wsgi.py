#!/usr/bin/env python
import os
from app import create_app
import socket, struct
import logging
from logging.handlers import RotatingFileHandler

if __name__ == '__main__':
    #app = create_app(os.environ.get('FLASK_CONFIG', 'development'))
    app = create_app(os.environ.get('FLASK_CONFIG', 'testing'))

    handler = RotatingFileHandler('restPetitions.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    # app.run()
    app.run(debug=False, use_reloader=False, host='127.0.0.1', port=5000)


