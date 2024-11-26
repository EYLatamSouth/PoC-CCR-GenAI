import os

class folders:

    APP_DIR = os.path.abspath(os.path.dirname('src/'))
    FRONTEND = os.path.join(APP_DIR, 'frontend')
    STATIC = os.path.join(FRONTEND, 'static')
    TEMPLATES = os.path.join(FRONTEND, 'templates')
