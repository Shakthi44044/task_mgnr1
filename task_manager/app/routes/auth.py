from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..models import User
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'username, email, password are required'}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'User already exists'}), 400

    hashed_password = generate_password_hash(password)
    user = User(username=username, password=hashed_password, email=email)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'Invalid input'}), 400

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        token = create_access_token(identity=str(user.id))
        return jsonify({'access_token': token, 'user': {'id': user.id, 'username': user.username, 'email': user.email}}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    uid = get_jwt_identity()
    try:
        uid_int = int(uid) if uid is not None else None
    except (TypeError, ValueError):
        uid_int = None
    if uid_int is None:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(uid_int)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': user.id, 'username': user.username, 'email': user.email}), 200
