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
