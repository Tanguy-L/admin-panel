import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    if request.json is None:
        return jsonify({"msg": "No JSON data provided"}), 400

    username = request.json.get("username")
    password = request.json.get("password")

    usernam_env = os.getenv("APP_USERNAME")
    password_env = os.getenv("APP_PASSWORD")

    if username is None or password is None:
        return jsonify({"msg": "Missing username or password"}), 400

    if username != usernam_env or password != password_env:
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)


@auth_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
