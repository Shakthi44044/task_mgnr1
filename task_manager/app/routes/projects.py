from flask import Blueprint, request, jsonify, g, abort
from flask_jwt_extended import jwt_required
from .. import db
from ..models import Project, Task, User
from datetime import datetime

projects_bp = Blueprint('projects', __name__)


def project_to_dict(p: Project, include_tasks: bool = False):
    data = {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "owner_id": p.owner_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if include_tasks:
        data["tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "assigned_to": t.assigned_to,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in Task.query.filter_by(project_id=p.id).order_by(Task.created_at.desc()).all()
        ]
    return data


@projects_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip() or None
    if not name:
        return jsonify({"error": "'name' is required"}), 400

    p = Project(name=name, description=description, owner_id=g.user_id)
    db.session.add(p)
    db.session.commit()
    return jsonify(project_to_dict(p)), 201


@projects_bp.route('/', methods=['GET'])
@jwt_required()
def list_projects():
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    projects = Project.query.filter_by(owner_id=g.user_id).order_by(Project.created_at.desc()).all()
    return jsonify([project_to_dict(p) for p in projects]), 200


@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id: int):
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    p = Project.query.get_or_404(project_id)
    if p.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    return jsonify(project_to_dict(p, include_tasks=True)), 200


@projects_bp.route('/<int:project_id>', methods=['PATCH'])
@jwt_required()
def update_project(project_id: int):
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    p = Project.query.get_or_404(project_id)
    if p.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "'name' cannot be empty"}), 400
        p.name = name
    if "description" in data:
        desc = data.get("description")
        p.description = (desc or "").strip() or None

    db.session.commit()
    return jsonify(project_to_dict(p)), 200


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id: int):
    if not g.user_id:
        return jsonify({"error": "Unauthorized"}), 401

    p = Project.query.get_or_404(project_id)
    if p.owner_id != g.user_id:
        return jsonify({"error": "Not found"}), 404

    # Manually delete tasks to avoid FK issues if DB lacks ON DELETE CASCADE
    Task.query.filter_by(project_id=p.id).delete(synchronize_session=False)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200
