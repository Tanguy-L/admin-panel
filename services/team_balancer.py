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
        """
        Assign a member to the team with the lowest current weight

        Args:
            member_weight (float): Weight of the member to be assigned

        Returns:
            int: Team ID of the balanced team
        """
        minTeam = min(self.teams_balance, key=lambda x: x["weight"])
        minTeam["weight"] += member_weight
        return minTeam["id"]
