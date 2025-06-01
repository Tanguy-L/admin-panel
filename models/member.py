from dataclasses import dataclass
from typing import Optional


@dataclass
class MemberDTO:
    id: int
    discord_id: str
    name: str
    steam_id: Optional[str]
    weight: float
    smoke_color: Optional[str]
    team_id: Optional[int]
    team_name: Optional[str]
    is_logged_in: bool
