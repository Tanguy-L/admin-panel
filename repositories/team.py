from models.team import TeamDTO
from typing import Dict, List, Optional
from core.config import TeamConfig


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
            SELECT team_id, name, channel_id, side, is_playing, hostname
            FROM teams
            WHERE is_playing
            ORDER BY team_id
        """
        )
        teams = self.cursor.fetchall()
        return teams

    def add_team(self, team: Dict):
        print(team)
        query = """
            INSERT INTO teams (name, side, channel_id, is_playing, hostname)
            VALUES (%s, %s, %s, %s, %s)
        """

        self.cursor.execute(
            query,
            (
                team.get("name"),
                team.get("side"),
                team.get("channel_id"),
                team.get("is_playing"),
                team.get("hostname"),
            ),
        )

        return self.cursor.lastrowid

    def update_team(self, team):
        query = """
            UPDATE teams
            SET name = %s, side = %s,
            channel_id = NULLIF(%s, ''),
            hostname = NULLIF(%s, '')
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
                team.get("hostname"),
                team.get("id"),
            ),
        )

    def get_teams_and_players(self) -> List[TeamDTO]:
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

    def get_all_teams(self) -> List[TeamDTO]:
        # Get basic team info
        self.cursor.execute(
            """
            SELECT team_id, name, channel_id, side, is_playing, hostname
            FROM teams
            ORDER BY team_id
        """
        )
        teams = self.cursor.fetchall()

        return teams

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
                hostname=team["hostname"],
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

    def delete_team(self, team_id: int) -> bool:
        """Delete a member from the database"""
        # First, remove any team memberships
        team_delete_query = "DELETE FROM team_members WHERE team_id = %s"
        self.cursor.execute(team_delete_query, (team_id,))

        # Then delete the member
        query = "DELETE FROM teams WHERE team_id = %s"
        self.cursor.execute(query, (team_id,))

        return self.cursor.rowcount > 0

    def get_team_by_id(self, member_id: int) -> Optional[Dict]:
        """Retrieve a member by their ID"""
        query = """
            SELECT *
            FROM teams
            WHERE team_id = %s
        """
        self.cursor.execute(query, (member_id,))
        return self.cursor.fetchone()

    def get_no_team_id(self) -> int:
        self.cursor.execute(
            "SELECT team_id FROM teams WHERE name = %s",
            (TeamConfig.NO_TEAM_NAME,),
        )
        result = self.cursor.fetchone()
        return result["team_id"]
