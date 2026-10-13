from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app.models.user import User
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token
from app import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    phone = data.get("phone_number")
    password = data.get("password")

    existing_user = User.query.filter_by(
        phone_number=phone
    ).first()

    if existing_user:
        return jsonify({
            "message": "User already exists"
        }), 400

    new_user = User(
        phone_number=phone,
        password_hash=generate_password_hash(password)
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully"
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    phone = data.get("phone_number")
    password = data.get("password")

    user = User.query.filter_by(
        phone_number=phone
    ).first()

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404;

    if not check_password_hash(
        user.password_hash,
        password
    ):
        return jsonify({
            "message": "Invalid credentials"
        }), 401

    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "access_token": access_token
    }), 200
