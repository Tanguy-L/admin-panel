from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from core.database import database_transaction
from repositories.team_member import TeamMemberRepository

teams_members_bp = Blueprint("teams_members", __name__)


@teams_members_bp.route("", methods=["PATCH"])
@jwt_required()
def handle_team_members():
    """UPDATE TEAM MEMBERS"""
    data = request.get_json()

    if not data:
        return jsonify(
            {
                "status": "error",
                "error": "No data provided",
            }
        )

    if "teams" not in data:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Invalid request format. 'teams'.",
                }
            ),
            400,
        )

    try:
        with database_transaction() as (db, cursor):
            repo = TeamMemberRepository(cursor)

            successful_assignments = []
            failed_assignments = []

            for team in data["teams"]:
                print(team)
                team_id = team.get("id")
                members = team.get("members", [])

                if not team_id or not members:
                    failed_assignments.append(
                        {
                            "team_id": team_id,
                            "members": members,
                            "error": "Invalid team or player list",
                        }
                    )
                    continue

                team_successful = []
                team_failed = []

                for member_id in members:
                    try:
                        repo.update_team_member(member_id, team_id)
                        team_successful.append(member_id)
                    except Exception as e:
                        team_failed.append(
                            {"member_id": member_id, "error": str(e)}
                        )

                # Track overall team assignment results
                if team_failed:
                    failed_assignments.append(
                        {
                            "team_id": team_id,
                            "successful_members": team_successful,
                            "failed_members": team_failed,
                        }
                    )
                else:
                    successful_assignments.append(
                        {"team_id": team_id, "players": team_successful}
                    )

            db.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Members teams changed",
            },
            200,
        )

    except Exception as e:
        return jsonify(
            {"status": "error", "error": f"Unexpected error: {str(e)}"},
            500,
        )
