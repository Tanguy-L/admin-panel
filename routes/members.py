import json
from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required

from core.database import database_transaction
from repositories.member import MemberRepository
from repositories.team_member import TeamMemberRepository

members_bp = Blueprint("members", __name__)


@members_bp.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


def _validate_and_update_member(repo, player_data):
    """Helper function to validate and update a single member"""
    required_fields = ["weight", "smoke_color", "is_logged_in", "discord_name"]

    # Check required fields
    for field in required_fields:
        if field not in player_data:
            raise ValueError(f"Missing required field: {field}")

    # Convert and validate data types
    try:
        validated_data = {
            "discord_id": (
                str(player_data.get("discord_id", ""))
                if player_data.get("discord_id")
                else None
            ),
            "steam_id": (
                str(player_data.get("steam_id"))
                if player_data.get("steam_id")
                else None
            ),
            "discord_name": str(player_data["discord_name"]),
            "weight": float(player_data["weight"]),
            "smoke_color": str(player_data["smoke_color"]),
            "is_logged_in": bool(player_data["is_logged_in"]),
        }
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid data format: {str(e)}")

    member_id = repo.add_member(validated_data)
    return member_id


@members_bp.route("/connection", methods=["PATCH"])
@jwt_required()
def handle_connection_members():
    """
    PATCH: Change all connections of players
    """
    if request.method == "PATCH":
        data = request.get_json()

        if not data:
            abort(400, description="No data provided")

        if "is_logged_in" in data:
            with database_transaction() as (db, cursor):
                repo = MemberRepository(cursor)
                repo.toggle_connection_all(data["is_logged_in"])

                return jsonify(
                    {
                        "status": "success",
                    }
                )
        else:
            abort(400, description="You have to provide is_logged_in")


@members_bp.route("", methods=["GET", "POST"])
@members_bp.route("/", methods=["GET", "POST"])
@jwt_required()
def handle_members():
    print(f"Preflight request headers: {request.headers}")
    """
    GET: Retrieve all members
    POST: Add one or multiple members
    """
    if request.method == "GET":
        with database_transaction() as (db, cursor):
            repo = MemberRepository(cursor)
            members = repo.get_all_members()

            return jsonify(
                {
                    "status": "success",
                    "data": members,
                }
            )

    # POST method
    data = request.get_json()
    if not data:
        return jsonify(
            {
                "status": "error",
                "error": "No data provided",
            }
        )

    try:
        with database_transaction() as (db, cursor):
            repo = MemberRepository(cursor)

            # Handle batch updates
            if isinstance(data, list):
                for player_data in data:
                    _validate_and_update_member(repo, player_data)
            # Handle single member update
            else:
                id = _validate_and_update_member(repo, data)

                return jsonify(
                    {
                        "status": "success",
                        "message": "Members added successfully",
                        "member": id,
                    }
                )

            return jsonify(
                {
                    "status": "success",
                    "message": "Members added successfully",
                }
            )

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data", "status": "error"})
    except ValueError as e:
        return jsonify({"error": str(e), "status": "error"})


@members_bp.route("/<int:member_id>", methods=["PUT", "DELETE"])
@jwt_required()
def route_member_update(member_id):
    """DELETE MEMBER"""
    if request.method == "DELETE":
        try:
            with database_transaction() as (db, cursor):
                repo = MemberRepository(cursor)

                # Check if member exists before deleting
                existing_member = repo.get_member_by_id(member_id)
                if not existing_member:
                    return jsonify(
                        {
                            "status": "error",
                            "error": f"Member with ID {member_id} not found",
                        },
                        404,
                    )

                # Delete the member
                result = repo.delete_member(member_id)

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

    """ UPDATE MEMBER """
    data = request.get_json()
    if not data:
        abort(400, description="No data provided")

    try:
        with database_transaction() as (db, cursor):
            repo = MemberRepository(cursor)

            # Check if member exists before deleting
            existing_member = repo.get_member_by_id(member_id)
            if not existing_member:
                return jsonify(
                    {
                        "status": "error",
                        "error": f"Member with ID {member_id} not found",
                    },
                    404,
                )
            # Extract and validate fields
            validated_data = {}

            # Handle fields that can be updated
            if "steam_id" in data:
                validated_data["steam_id"] = (
                    str(data["steam_id"]) if data["steam_id"] else None
                )

            if "weight" in data:
                try:
                    validated_data["weight"] = float(data["weight"])
                except (ValueError, TypeError):
                    return jsonify(
                        {
                            "status": "error",
                            "error": "Weight must be a valid number",
                        },
                        422,
                    )

            if "smoke_color" in data:
                validated_data["smoke_color"] = (
                    str(data["smoke_color"]) if data["smoke_color"] else None
                )

            if "is_logged_in" in data:
                validated_data["is_logged_in"] = bool(data["is_logged_in"])

            # Required field for the existing update_member method
            if "discord_id" in data:
                validated_data["discord_id"] = str(data["discord_id"])

            if "discord_name" in data:
                validated_data["discord_name"] = str(data["discord_name"])

            # If team_id is provided, update team membership
            if "team_id" in data:
                team_member_repo = TeamMemberRepository(cursor)

                try:
                    team_id = int(data["team_id"])
                    # Check if team exists
                    cursor.execute(
                        "SELECT * FROM teams WHERE team_id = %s", (team_id,)
                    )
                    if not cursor.fetchone():
                        return jsonify(
                            {
                                "status": "error",
                                "error": f"Team with ID {team_id} not found",
                            },
                            404,
                        )

                    team_member_repo.update_team_member(member_id, team_id)

                except (ValueError, TypeError):
                    return jsonify(
                        {
                            "status": "error",
                            "error": "Team ID must be a valid integer",
                        },
                        422,
                    )

            print(validated_data)

            # Update member data
            repo = MemberRepository(cursor)
            repo.update_member(validated_data, member_id)

            # Fetch updated member data to return
            cursor.execute(
                """
                SELECT
                    m.*, t.team_id, t.name as team_name,
                    t.channel_id as team_channel_id
                FROM members m
                LEFT JOIN team_members tm ON m.id = tm.member_id
                LEFT JOIN teams t ON tm.team_id = t.team_id
                WHERE m.id = %s
            """,
                (member_id,),
            )
            updated_member = cursor.fetchone()

            return jsonify(
                {
                    "status": "success",
                    "message": "Member updated successfully",
                    "data": updated_member,
                }
            )

    except json.JSONDecodeError:
        return jsonify({"status": "error", "error": "Invalid JSON data"}, 500)
    except ValueError as e:
        return jsonify({"status": "error", "error": str(e)}, 500)
    except Exception as e:
        return jsonify(
            {"status": "error", "error": f"Unexpected error: {str(e)}"}, 500
        )
