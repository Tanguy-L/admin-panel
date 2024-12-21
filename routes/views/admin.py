from flask import Blueprint, render_template, request, redirect, jsonify
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from mysql.connector import Error
import logging
from functools import wraps
from core.database import get_db, close_db

# Blueprint setup
views = Blueprint("admin_views", __name__, url_prefix="/admin")


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
            SET name = %s, side = %s, channel_id = %s, is_playing = %s
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
            "SELECT team_id FROM teams WHERE name = %s", (TeamConfig.NO_TEAM_NAME,)
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
        logged_out_members = self.member_repo.get_members_by_login_status(False)
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
                self.team_member_repo.update_team_member(member["id"], no_team_id)


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


# Route handlers
@views.route("/", methods=["GET", "POST"])
@handle_db_errors
def render_admin_home():
    if request.method == "POST":
        form_data = request.form.to_dict(flat=False)

        if "edit" in form_data:
            return redirect("/admin/?edit=true")

        if "save" in form_data:
            with database_transaction() as (db, cursor):
                num_players = len(form_data["discord_id"])

                print(form_data)
                for i in range(num_players):
                    player_data = {
                        "discord_id": form_data["discord_id"][i],
                        "steam_id": form_data["steam_id"][i] or None,
                        "weight": float(form_data["weight"][i]),
                        "smoke_color": form_data["smoke_color"][i],
                        "is_logged_in": form_data["is_logged_in"][i],
                    }

                    repo = MemberRepository(cursor)
                    repo.update_member(player_data)

    with database_transaction() as (db, cursor):
        repo = MemberRepository(cursor)
        members = repo.get_all_members()

    return render_template("admin/dashboard.html", members=members)


@views.route("/change_team", methods=["POST"])
@handle_db_errors
def change_team():
    data = request.json

    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    team_id = data.get("team_id")
    member_id = data.get("member_id")

    if not all([team_id, member_id]):
        return jsonify({"error": "Missing team_id or member_id"}), 400

    with database_transaction() as (db, cursor):
        repo = TeamMemberRepository(cursor)
        repo.update_team_member(member_id, team_id)

    return jsonify({"message": "Team updated successfully"}), 200


@views.route("/teams", methods=["GET", "POST"])
@handle_db_errors
def render_teams():
    if request.method == "POST":
        form_data = request.form.to_dict(flat=False)

        if "edit" in form_data:
            return redirect("/admin/teams?edit=true")

        if "save" in form_data:
            with database_transaction() as (db, cursor):
                num_teams = len(form_data["id"])

                for i in range(num_teams):
                    team_data = {
                        "name": form_data["name"][i] or None,
                        "side": form_data["side"][i] or None,
                        "channel_id": form_data["channel_id"][i] or None,
                        "id": form_data["id"][i] or None,
                        "is_playing": form_data["is_playing"][i] or None,
                    }

                    repo = TeamRepository(cursor)
                    repo.update_team(team_data)

    with database_transaction() as (db, cursor):
        repo = TeamRepository(cursor)
        teams = repo.get_all_teams()

    return render_template("admin/teams.html", teams=teams)


@views.route("/teams-players", methods=["GET", "POST"])
@handle_db_errors
def render_teams_players():
    if request.method == "POST":
        form_data = request.form.to_dict(flat=False)

        with database_transaction() as (db, cursor):
            service = TeamService(db, cursor)

            if "clear-teams" in form_data:
                service.clear_teams()
                return redirect("/admin")

            if "generate-teams" in form_data:
                service.generate_balanced_teams()
                return redirect("/admin/teams-players")

    with database_transaction() as (db, cursor):
        repo = TeamRepository(cursor)
        teams = repo.get_all_teams()

    return render_template("admin/teams-players.html", teams=teams)


@views.route("/add-team", methods=["GET", "POST"])
@handle_db_errors
def render_add_team():
    if request.method == "POST":
        form_data = request.form.to_dict(flat=False)

        if "save" in form_data:
            with database_transaction() as (db, cursor):
                team_data = {
                    "name": form_data["name"][0],
                    "side": form_data["side"][0],
                }

                print(team_data)

                repo = TeamRepository(cursor)
                repo.add_team(team_data)

        with database_transaction() as (db, cursor):
            print(form_data)

    new_team = {
        "name": "test",
        "side": "CounterTerrorist",
        "channel_id": 0,
    }

    return render_template("admin/add-team.html", team=new_team)


@views.route("/generate_teams", methods=["GET", "POST"])
@handle_db_errors
def generate_teams():
    with database_transaction() as (db, cursor):
        service = TeamService(db, cursor)
        mayo_weight, ketchup_weight = service.generate_balanced_teams()

    return (
        jsonify(
            {
                "message": "Successfully balanced teams Mayo/Ketchup",
                "mayo_weight": mayo_weight,
                "ketchup_weight": ketchup_weight,
            }
        ),
        200,
    )
