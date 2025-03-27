from dataclasses import dataclass, field
from typing import Optional, Dict, List


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
