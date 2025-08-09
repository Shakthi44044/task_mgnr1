from celery import Celery

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app.config)
    # Celery Beat schedule
    celery.conf.beat_schedule = {
        'daily-overdue-summary': {
            'task': 'tasks.send_daily_overdue_summary',
            'schedule': 24 * 60 * 60,  # every 24 hours
        }
    }
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery