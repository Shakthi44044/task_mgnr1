from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from .. import db
from ..models import Task, Project, User
from datetime import datetime
# Email/Celery notifications disabled

VALID_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


tasks_bp = Blueprint('tasks', __name__)


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def task_to_dict(t: Task, include_refs: bool = False):
    data = {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "project_id": t.project_id,
        "assigned_to": t.assigned_to,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
    if include_refs:
        proj = Project.query.get(t.project_id) if t.project_id else None
        user = User.query.get(t.assigned_to) if t.assigned_to else None
        data["project"] = {
            "id": proj.id,
            "name": proj.name,
        } if proj else None
        data["assigned_user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        } if user else None
    return data


@tasks_bp.route('/', methods=['POST'])
@jwt_required()
def create_task():
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip() or None
    status = (data.get("status") or "todo").strip()
    priority = (data.get("priority") or "medium").strip()
    due_date = parse_date(data.get("due_date"))
    project_id = data.get("project_id")
    assigned_to = data.get("assigned_to")

    if not title:
        return jsonify({"error": "'title' is required"}), 400
    if not project_id:
        return jsonify({"error": "'project_id' is required"}), 400

    proj = Project.query.get_or_404(project_id)
    if proj.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    if status not in VALID_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": "Invalid priority"}), 400

    if assigned_to:
        user = User.query.get(assigned_to)
        if not user:
            return jsonify({"error": "assigned_to not found"}), 400

    t = Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        project_id=project_id,
        assigned_to=assigned_to,
    )
    db.session.add(t)
    db.session.commit()

    # Notification disabled

    return jsonify(task_to_dict(t, include_refs=True)), 201


@tasks_bp.route('/', methods=['GET'])
@jwt_required()
def list_tasks():
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Base query: tasks within projects owned by current user
    q = db.session.query(Task).join(Project, Task.project_id == Project.id).filter(Project.owner_id == g.user_id)

    # Filters
    status = request.args.get('status')
    priority = request.args.get('priority')
    due_date = parse_date(request.args.get('due_date'))
    project_id = request.args.get('project_id', type=int)

    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)
    if due_date:
        q = q.filter(Task.due_date == due_date)
    if project_id:
        q = q.filter(Task.project_id == project_id)

    # Sorting
    sort = (request.args.get('sort') or '').strip()
    if sort == 'priority':
        q = q.order_by(Task.priority.desc())
    elif sort == 'due_date':
        # SQLite-safe: non-null first, then ascending dates
        q = q.order_by(Task.due_date.is_(None), Task.due_date.asc())
    else:
        q = q.order_by(Task.created_at.desc())

    # Pagination
    page = max(1, request.args.get('page', default=1, type=int))
    page_size = min(100, max(1, request.args.get('page_size', default=20, type=int)))
    items = q.limit(page_size).offset((page - 1) * page_size).all()

    return jsonify([task_to_dict(t, include_refs=True) for t in items]), 200


@tasks_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id: int):
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    t = Task.query.get_or_404(task_id)
    proj = Project.query.get(t.project_id)
    if not proj or proj.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    return jsonify(task_to_dict(t, include_refs=True)), 200


@tasks_bp.route('/<int:task_id>', methods=['PATCH'])
@jwt_required()
def update_task(task_id: int):
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    t = Task.query.get_or_404(task_id)
    proj = Project.query.get(t.project_id)
    if not proj or proj.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    prev_status = t.status
    prev_assigned = t.assigned_to
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "'title' cannot be empty"}), 400
        t.title = title
    if "description" in data:
        t.description = (data.get("description") or "").strip() or None
    if "status" in data:
        val = (data.get("status") or "").strip()
        if val not in VALID_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        t.status = val
    if "priority" in data:
        val = (data.get("priority") or "").strip()
        if val not in VALID_PRIORITIES:
            return jsonify({"error": "Invalid priority"}), 400
        t.priority = val
    if "due_date" in data:
        t.due_date = parse_date(data.get("due_date"))
    if "assigned_to" in data:
        assigned_to = data.get("assigned_to")
        if assigned_to:
            user = User.query.get(assigned_to)
            if not user:
                return jsonify({"error": "assigned_to not found"}), 400
            t.assigned_to = assigned_to
        else:
            t.assigned_to = None

    db.session.commit()

    # Notifications disabled

    return jsonify(task_to_dict(t, include_refs=True)), 200


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id: int):
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    t = Task.query.get_or_404(task_id)
    proj = Project.query.get(t.project_id)
    if not proj or proj.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(t)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200
