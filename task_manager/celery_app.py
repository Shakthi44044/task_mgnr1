from task_manager.app import create_app, celery as flask_celery  # package-safe import

# Initialize the Flask app (sets up extensions and celery instance)
flask_app = create_app()

# Use the Celery instance created by the factory
celery = flask_celery

# Register tasks (import side effects)
import task_manager.app.tasks_email  # noqa: F401,E402
