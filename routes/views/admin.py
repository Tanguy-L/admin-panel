import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Blueprint,
    jsonify,
    Response,
    redirect,
    render_template,
    request,
)
from mysql.connector import Error

from core.database import close_db, get_db

api = Blueprint("api", __name__)

API_VERSION = "v1"


# Constants and Configuration
@dataclass
class TeamConfig:
    MAYO_TEAM_ID: int = 1
    KETCHUP_TEAM_ID: int = 3
    NO_TEAM_NAME: str = "NoTeam"
    MIN_WEIGHT: int = 0


# Database utilities
@contextmanager
def database_transaction():
    """Context manager for database transactions with automatic rollback"""
    db, cursor = get_db()
    try:
        yield db, cursor
        db.commit()
    except Exception as e:
        logging.error(f"db transactions error : {str(e)}")
        db.rollback()
        raise
    finally:
        close_db(db)


def handle_db_errors(f):
    """Decorator for handling database errors"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Error as e:
            logging.error(f"Database error in {f.__name__}: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return wrapper


# Data Transfer Objects
@dataclass
class MemberDTO:
    id: int
    discord_id: str
    discord_name: str
    steam_id: Optional[str]
    weight: float
    smoke_color: Optional[str]
    team_id: Optional[int]
    team_name: Optional[str]
    is_logged_in: bool


@dataclass
class TeamDTO:
    id: int
    name: str
    side: Optional[str]
    is_playing: bool
    channel_id: Optional[str]
    weight: float = 0
    players: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if self.players is None:
            self.players = []


# Repository Layer
class MemberRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def get_all_members(self) -> List[Dict]:
        query = """
            SELECT
                m.*, t.team_id, t.name as team_name,
                t.channel_id as team_channel_id
            FROM members m
            LEFT JOIN team_members tm ON m.id = tm.member_id
            LEFT JOIN teams t ON tm.team_id = t.team_id
            ORDER BY m.weight DESC
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def update_member(self, member: Dict) -> None:
        print(member)
        query = """
            UPDATE members
            SET steam_id = %s, weight = %s, smoke_color = %s, is_logged_in = %s
            WHERE discord_id = %s
        """
        self.cursor.execute(
            query,
            (
                member.get("steam_id"),
                member.get("weight"),
                member.get("smoke_color"),
                member.get("is_logged_in"),
                member.get("discord_id"),
            ),
        )

    def get_members_by_login_status(self, is_logged_in: bool) -> List[Dict]:
        query = """
            SELECT * FROM members
            WHERE weight > %s
            AND steam_id IS NOT NULL
            AND is_logged_in = %s
            ORDER BY weight DESC
        """
        self.cursor.execute(query, (TeamConfig.MIN_WEIGHT, is_logged_in))
        return self.cursor.fetchall()


class TeamRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def get_teams_with_players_connected(self):
        self.cursor.execute(
            """
            SELECT team_id, name, channel_id, side, is_playing
            FROM teams
            WHERE is_playing
            ORDER BY team_id
        """
        )
        teams = self.cursor.fetchall()

        # Get team players
        self.cursor.execute(
            """
            SELECT
                t.team_id, t.name, m.id as player_id,
                m.discord_name as player_name, m.weight as player_weight
            FROM teams t
            LEFT JOIN team_members tm ON t.team_id = tm.team_id
            LEFT JOIN members m ON m.id = tm.member_id
            WHERE m.discord_name IS NOT NULL
        """
        )
        players = self.cursor.fetchall()

        return self._aggregate_team_data(teams, players)

    def get_teams_connected(self):
        self.cursor.execute(
            """
            SELECT team_id, name, channel_id, side, is_playing
            FROM teams
            WHERE is_playing
            ORDER BY team_id
        """
        )
        teams = self.cursor.fetchall()
        return teams

    def add_team(self, team):
        query = """
            INSERT INTO teams (name, side)
            VALUES (%s, %s)
        """

        self.cursor.execute(
            query,
            (
                team.get("name"),
                team.get("side"),
            ),
        )

    def update_team(self, team):
        query = """
            UPDATE teams
            SET name = %s, side = %s,channel_id =NULLIF(%s, ''),
            is_playing = %s
            WHERE team_id = %s
        """

        self.cursor.execute(
            query,
            (
                team.get("name"),
                team.get("side"),
                team.get("channel_id"),
                team.get("is_playing"),
                team.get("id"),
            ),
        )

    def get_all_teams(self) -> List[TeamDTO]:
        # Get basic team info
        self.cursor.execute(
            """
            SELECT team_id, name, channel_id, side, is_playing
            FROM teams
            ORDER BY team_id
        """
        )
        teams = self.cursor.fetchall()

        # Get team players
        self.cursor.execute(
            """
            SELECT
                t.team_id, t.name, m.id as player_id,
                m.discord_name as player_name, m.weight as player_weight
            FROM teams t
            LEFT JOIN team_members tm ON t.team_id = tm.team_id
            LEFT JOIN members m ON m.id = tm.member_id
            WHERE m.discord_name IS NOT NULL
        """
        )
        players = self.cursor.fetchall()

        return self._aggregate_team_data(teams, players)

    def _aggregate_team_data(
        self, teams: List[Dict], players: List[Dict]
    ) -> List[TeamDTO]:
        team_map = {
            team["team_id"]: TeamDTO(
                id=team["team_id"],
                name=team["name"],
                channel_id=team["channel_id"],
                side=team["side"],
                is_playing=team["is_playing"],
            )
            for team in teams
        }

        for player in players:
            team = team_map.get(player["team_id"])
            if team:
                team.weight += player["player_weight"]
                team.players.append(
                    {
                        "id": player["player_id"],
                        "name": player["player_name"],
                        "weight": player["player_weight"],
                    }
                )

        return list(team_map.values())

    def get_no_team_id(self) -> int:
        self.cursor.execute(
            "SELECT team_id FROM teams WHERE name = %s",
            (TeamConfig.NO_TEAM_NAME,),
        )
        result = self.cursor.fetchone()
        return result["team_id"]


class TeamMemberRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def update_team_member(self, member_id: int, team_id: int) -> None:
        if self._member_has_team(member_id):
            self._update(member_id, team_id)
        else:
            self._insert(member_id, team_id)

    def _member_has_team(self, member_id: int) -> bool:
        self.cursor.execute(
            "SELECT COUNT(*) as count FROM team_members WHERE member_id = %s",
            (member_id,),
        )
        return self.cursor.fetchone()["count"] > 0

    def _update(self, member_id: int, team_id: int) -> None:
        self.cursor.execute(
            "UPDATE team_members SET team_id = %s WHERE member_id = %s",
            (team_id, member_id),
        )

    def _insert(self, member_id: int, team_id: int) -> None:
        self.cursor.execute(
            "INSERT INTO team_members (member_id, team_id) VALUES (%s, %s)",
            (member_id, team_id),
        )


# Service Layer
class TeamService:
    def __init__(self, db, cursor):
        self.db = db
        self.team_repo = TeamRepository(cursor)
        self.member_repo = MemberRepository(cursor)
        self.team_member_repo = TeamMemberRepository(cursor)

    def generate_balanced_teams(self):
        no_team_id = self.team_repo.get_no_team_id()

        # Move logged out members to no team
        logged_out_members = self.member_repo.get_members_by_login_status(
            False
        )
        for member in logged_out_members:
            self.team_member_repo.update_team_member(member["id"], no_team_id)

        # Balance logged in members
        logged_in_members = self.member_repo.get_members_by_login_status(True)
        if not logged_in_members:
            raise ValueError("No active members found")

        teams_connected = self.team_repo.get_teams_connected()

        balancer = TeamBalancer(teams_connected)
        for member in logged_in_members:
            new_team_id = balancer.get_balanced_team(member["weight"])
            self.team_member_repo.update_team_member(member["id"], new_team_id)

        return list(map((lambda x: x["weight"]), balancer.teams_balance))

    def clear_teams(self) -> None:
        no_team_id = self.team_repo.get_no_team_id()
        members = self.member_repo.get_all_members()

        for member in members:
            if member["weight"] > 0 and member["steam_id"]:
                self.team_member_repo.update_team_member(
                    member["id"], no_team_id
                )


class TeamBalancer:
    def __init__(self, teams):
        self.teams_balance = []
        for team in teams:
            print(team)
            self.teams_balance.append(
                {
                    "weight": 0,
                    "id": team["team_id"],
                }
            )

    def get_balanced_team(self, member_weight: float) -> int:
        minTeam = min(self.teams_balance, key=lambda x: x["weight"])
        minTeam["weight"] += member_weight
        return minTeam["id"]


# Version route
@api.route("/", methods=["GET"])
def get_version():
    return jsonify({"version": API_VERSION, "status": "running"})


def _validate_and_update_member(repo, player_data):
    """Helper function to validate and update a single member"""
    required_fields = [
        "discord_id",
        "steam_id",
        "weight",
        "smoke_color",
        "is_logged_in",
    ]

    # Check required fields
    for field in required_fields:
        if field not in player_data:
            raise ValueError(f"Missing required field: {field}")

    # Convert and validate data types
    try:
        validated_data = {
            "discord_id": str(player_data["discord_id"]),
            "steam_id": (
                str(player_data["steam_id"])
                if player_data["steam_id"]
                else None
            ),
            "weight": float(player_data["weight"]),
            "smoke_color": str(player_data["smoke_color"]),
            "is_logged_in": bool(player_data["is_logged_in"]),
        }
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid data format: {str(e)}")

    repo.update_member(validated_data)


# Members route
@api.route("/members", methods=["GET", "POST"])
@handle_db_errors
def handle_members() -> Response:
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
                _validate_and_update_member(repo, data)

            return jsonify(
                {
                    "status": "success",
                    "message": "Members updated successfully",
                }
            )

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data", "status": "error"})
    except ValueError as e:
        return jsonify({"error": str(e), "status": "error"})
