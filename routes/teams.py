import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from core.database import database_transaction
from repositories.team import TeamRepository

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/", methods=["GET", "POST"])
@jwt_required()
def handle_members():
    """
    GET: Retrieve all teams
    POST: add a team
    """
    if request.method == "GET":
        with database_transaction() as (db, cursor):
            repo = TeamRepository(cursor)
            teams = repo.get_all_teams()

            return jsonify(
                {
                    "status": "success",
                    "data": teams,
                }
            )
