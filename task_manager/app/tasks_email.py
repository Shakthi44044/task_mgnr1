from flask import current_app
from flask_mail import Message
from . import mail, db
from .models import User, Task, Project
from datetime import date

# Plain function definitions so this module can be imported before Celery exists.
def send_task_notification(task_id: int, action: str):  # will be wrapped by celery.task later
    """Send email when a task is assigned or status changes.
    action: 'assigned' | 'status_changed'
    """
    with current_app.app_context():
        task = Task.query.get(task_id)
        if not task or not task.assigned_to:
            return
        user = User.query.get(task.assigned_to)
        if not user or not user.email:
            return
        subject = f"Task '{task.title}': {action.replace('_', ' ').title()}"
        body = f"Hello {user.username},\n\nThe task '{task.title}' has been {action}.\n\nStatus: {task.status}\nPriority: {task.priority}\nDue: {task.due_date}\n\nRegards,\nTask Manager"
        msg = Message(subject=subject, recipients=[user.email], body=body)
        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.exception("Failed to send task notification: %s", e)


def send_daily_overdue_summary():  # will be wrapped by celery.task later
    """Send a daily summary email of overdue tasks to each user."""
    with current_app.app_context():
        today = date.today()
        users = User.query.all()
        for u in users:
            overdue = (
                db.session.query(Task)
                .join(Project, Task.project_id == Project.id)
                .filter(Task.assigned_to == u.id)
                .filter(Task.due_date.isnot(None))
                .filter(Task.due_date < today)
                .order_by(Task.due_date.asc())
                .all()
            )
            if not overdue or not u.email:
                continue
            lines = [
                f"- [{t.status}] {t.title} (Project: {t.project.name if t.project else t.project_id}) due {t.due_date}"
                for t in overdue
            ]
            subject = "Your overdue tasks summary"
            body = (
                f"Hello {u.username},\n\nThe following tasks are overdue:\n\n" + "\n".join(lines) + "\n\nRegards,\nTask Manager"
            )
            msg = Message(subject=subject, recipients=[u.email], body=body)
            try:
                mail.send(msg)
            except Exception as e:
                current_app.logger.exception("Failed to send summary email: %s", e)


def init_celery_tasks(celery):
    """Register the above functions as Celery tasks once celery is initialized.
    Rebinds the module-level names so imports elsewhere (e.g., routes) pick up the task objects.
    """
    global send_task_notification, send_daily_overdue_summary
    send_task_notification = celery.task(name='tasks.send_task_notification')(send_task_notification)
    send_daily_overdue_summary = celery.task(name='tasks.send_daily_overdue_summary')(send_daily_overdue_summary)
    return send_task_notification, send_daily_overdue_summary
