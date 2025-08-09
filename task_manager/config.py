import os

basedir = os.path.abspath(os.path.dirname(__file__))

def _default_sqlite_uri():
    path = os.path.join(basedir, 'task_manager.db')
    return f'sqlite:///{path}'

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or _default_sqlite_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")