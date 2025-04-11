from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required

import json
from core.database import database_transaction
from repositories.team import TeamRepository

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/<int:team_id>", methods=["PUT", "DELETE"])
@jwt_required()
def handle_team(team_id):
    if request.method == "PUT":
        """UPDATE MEMBER"""
        data = request.get_json()
        if not data:
            abort(400, description="No data provided")

        try:
            with database_transaction() as (db, cursor):
                repo = TeamRepository(cursor)

                # Check if member exists before deleting
                existing_team = repo.get_team_by_id(team_id)
                if not existing_team:
                    return jsonify(
                        {
                            "status": "error",
                            "error": f"Member with ID {data["id"]} not found",
                        },
                        404,
                    )
                # Extract and validate fields
                validated_data = {}

                # Handle fields that can be updated
                if "name" in data:
                    validated_data["name"] = (
                        str(data["name"]) if data["name"] else None
                    )

                if "channel_id" in data:
                    validated_data["channel_id"] = (
                        str(data["channel_id"]) if data["channel_id"] else None
                    )

                if "is_playing" in data:
                    validated_data["is_playing"] = data["is_playing"]

                if "side" in data:
                    validated_data["side"] = data["side"]

                validated_data["id"] = team_id

                print(validated_data)

                # Update member data
                repo.update_team(validated_data)

                updated_member = repo.get_team_by_id(team_id)

                return jsonify(
                    {
                        "status": "success",
                        "message": "Member updated successfully",
                        "data": updated_member,
                    }
                )

        except json.JSONDecodeError:
            return jsonify(
                {"status": "error", "error": "Invalid JSON data"}, 500
            )
        except ValueError as e:
            return jsonify({"status": "error", "error": str(e)}, 500)
        except Exception as e:
            return jsonify(
                {"status": "error", "error": f"Unexpected error: {str(e)}"},
                500,
            )
    """DELETE TEAM"""
    if request.method == "DELETE":
        try:
            with database_transaction() as (db, cursor):
                repo = TeamRepository(cursor)

                # Check if member exists before deleting
                existing_team = repo.get_team_by_id(team_id)
                if not existing_team:
                    return jsonify(
                        {
                            "status": "error",
                            "error": f"Member with ID {team_id} not found",
                        },
                        404,
                    )

                # Delete the member
                repo.delete_team(team_id)

                return jsonify(
                    {
                        "status": "success",
                        "message": "Member deleted successfully",
                    }
                )

        except Exception as e:
            return jsonify(
                {"status": "error", "error": f"Unexpected error: {str(e)}"},
                500,
            )


@teams_bp.route("/", methods=["GET", "POST"])
@teams_bp.route("", methods=["GET", "POST"])
@jwt_required()
def handle_teams_list():
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
    else:
        data = request.get_json()
        if not data:
            return jsonify(
                {
                    "status": "error",
                    "error": "No data provided",
                }
            )

        if not data["name"]:
            return jsonify({"status": "error", "error": "No name given"})

        with database_transaction() as (db, cursor):
            repo = TeamRepository(cursor)

            # Extract and validate fields
            validated_data = {}

            # Handle fields that can be updated
            validated_data["name"] = data["name"]

            validated_data["is_playing"] = 0

            if "channel_id" in data:
                validated_data["channel_id"] = str(data["channel_id"])
            else:
                validated_data["channel_id"] = None

            if "side" in data:
                if (
                    data["side"] == "CounterTerrorist"
                    or data["side"] == "Terrorist"
                ):
                    validated_data["side"] = str(data["side"])
            else:
                validated_data["side"] = None

            try:
                team_id = repo.add_team(validated_data)

                return jsonify(
                    {
                        "status": "success",
                        "message": "Team added successfully",
                        "team": team_id,
                    }
                )
            except Exception as e:
                return jsonify(
                    {
                        "status": "500",
                        "error": "Unexpected error",
                        "details": str(e),
                    },
                    500,
                )
