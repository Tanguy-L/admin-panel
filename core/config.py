from dataclasses import dataclass


@dataclass
class TeamConfig:
    MAYO_TEAM_ID: int = 1
    KETCHUP_TEAM_ID: int = 3
    NO_TEAM_NAME: str = "NoTeam"
    MIN_WEIGHT: int = 0


class Config:
    """Application configuration"""

    API_VERSION = "v1"
    # Add other configuration settings here
