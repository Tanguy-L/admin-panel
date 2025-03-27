from typing import List, Dict, Optional
from core.config import TeamConfig


class MemberRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def delete_member(self, member_id: int) -> bool:
        """Delete a member from the database"""
        # First, remove any team memberships
        team_delete_query = "DELETE FROM team_members WHERE member_id = %s"
        self.cursor.execute(team_delete_query, (member_id,))

        # Then delete the member
        query = "DELETE FROM members WHERE id = %s"
        self.cursor.execute(query, (member_id,))

        return self.cursor.rowcount > 0

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

    def add_member(self, member_data: Dict) -> int:
        """Add a new member to the database"""
        query = """
            INSERT INTO members
            (discord_id, discord_name, steam_id, weight,
            smoke_color, is_logged_in)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(
            query,
            (
                member_data.get("discord_id"),
                member_data.get("discord_name"),
                member_data.get("steam_id"),
                member_data.get("weight", 0),
                member_data.get("smoke_color"),
                member_data.get("is_logged_in", False),
            ),
        )
        return self.cursor.lastrowid

    def get_member_by_id(self, member_id: int) -> Optional[Dict]:
        """Retrieve a member by their ID"""
        query = """
            SELECT
                m.*, t.team_id, t.name as team_name,
                t.channel_id as team_channel_id
            FROM members m
            LEFT JOIN team_members tm ON m.id = tm.member_id
            LEFT JOIN teams t ON tm.team_id = t.team_id
            WHERE m.id = %s
        """
        self.cursor.execute(query, (member_id,))
        return self.cursor.fetchone()

    def update_member(self, member: Dict, member_id: int) -> None:
        query = """
            UPDATE members
            SET steam_id = %s, weight = %s, smoke_color = %s,
            is_logged_in = %s, discord_id= %s, discord_name = %s
            WHERE id = %s
        """
        self.cursor.execute(
            query,
            (
                member.get("steam_id"),
                member.get("weight"),
                member.get("smoke_color"),
                member.get("is_logged_in"),
                member.get("discord_id"),
                member.get("discord_name"),
                member_id,
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
