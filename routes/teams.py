from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required

import json
from core.database import database_transaction
from repositories.team import TeamRepository
from repositories.member import MemberRepository
from repositories.team_member import TeamMemberRepository
from services.team_balancer import TeamBalancer
from core.config import TeamConfig

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
                            "error": f"Member with ID {data['id']} not found",
                        },
                        404,
                    )
                # Extract and validate fields
                validated_data = {}

                # Handle fields that can be updated
                if "name" in data:
                    validated_data["name"] = str(data["name"]) if data["name"] else None

                if "channel_id" in data:
                    validated_data["channel_id"] = (
                        str(data["channel_id"]) if data["channel_id"] else None
                    )

                if "is_playing" in data:
                    validated_data["is_playing"] = data["is_playing"]

                if "side" in data:
                    validated_data["side"] = data["side"]

                if "hostname" in data:
                    validated_data["hostname"] = data["hostname"]

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
            return jsonify({"status": "error", "error": "Invalid JSON data"}, 500)
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


@teams_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_teams():
    """
    Generate balanced teams by distributing connected players based on weight
    """
    try:
        with database_transaction() as (db, cursor):
            team_repo = TeamRepository(cursor)
            member_repo = MemberRepository(cursor)
            team_member_repo = TeamMemberRepository(cursor)

            # Get all teams that are playing, excluding NoTeam
            playing_teams = [
                team
                for team in team_repo.get_teams_connected()
                if team["name"] != TeamConfig.NO_TEAM_NAME
            ]

            if not playing_teams:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "No active teams available for assignment",
                        }
                    ),
                    400,
                )

            # Get all connected players with weight > MIN_WEIGHT
            connected_players = member_repo.get_members_by_login_status(
                is_logged_in=True
            )

            if not connected_players:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "No connected players available for team assignment",
                        }
                    ),
                    400,
                )

            # Initialize team balancer with playing teams
            balancer = TeamBalancer(playing_teams)

            # For each player, assign them to the most balanced team
            assignments = []
            for player in connected_players:
                team_id = balancer.get_balanced_team(player["weight"])
                team_member_repo.update_team_member(player["id"], team_id)
                assignments.append(
                    {
                        "player_id": player["id"],
                        "player_name": player["discord_name"],
                        "weight": player["weight"],
                        "assigned_team_id": team_id,
                    }
                )

            # Get updated team data to return in the response
            updated_teams = team_repo.get_teams_with_players_connected()

            return jsonify(
                {
                    "status": "success",
                    "message": "Teams have been generated successfully",
                    "data": {
                        "assignments": assignments,
                        "teams": updated_teams,
                    },
                }
            )

    except Exception as e:
        return (
            jsonify({"status": "error", "error": f"Unexpected error: {str(e)}"}),
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

            if "hostname" in data:
                validated_data["hostname"] = str(data["hostname"])
            else:
                validated_data["hostname"] = None

            if "side" in data:
                if data["side"] == "CounterTerrorist" or data["side"] == "Terrorist":
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
