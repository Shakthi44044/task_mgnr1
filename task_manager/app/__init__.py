from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from flask_mail import Mail
from .celery_worker import make_celery
from ..config import Config

db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
celery = None

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # Attach user_id from JWT (if present) to flask.g
    @app.before_request
    def attach_user_from_jwt():
        try:
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            try:
                g.user_id = int(ident) if ident is not None else None
            except (TypeError, ValueError):
                g.user_id = None
        except Exception:
            g.user_id = None

    from .routes.auth import auth_bp
    from .routes.projects import projects_bp
    from .routes.tasks import tasks_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(projects_bp, url_prefix="/projects")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")

    # Root and health endpoints
    @app.get("/")
    def index():
        return {
            "message": "Task Manager API",
            "endpoints": ["/auth", "/projects", "/tasks", "/healthz"],
        }, 200

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.get("/favicon.ico")
    def favicon():
        return "", 204

    global celery
    celery = make_celery(app)
    # Expose celery to avoid circular imports
    app.extensions = getattr(app, 'extensions', {})
    app.extensions['celery'] = celery

    # Auto-create tables inside container if they don't exist yet
    with app.app_context():
        try:
            from .models import User, Project, Task  # noqa: F401
            db.create_all()
        except Exception as e:
            app.logger.error("DB initialization failed: %s", e)

    return app