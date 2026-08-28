"""Contains constants used between modules."""

from typing import Literal, TypeAlias

HOST: str = "localhost"
APP_PORT: Literal[8000] = 8000

# These are ports that are known to the Azure App Registration.
GuiPort: TypeAlias = Literal[5173, 3000, 8000]
AppPort: TypeAlias = Literal[5173, 3000, 8000]

LogLevel: TypeAlias = Literal["debug", "info", "warning", "error", "critical"]
Environment: TypeAlias = Literal["development", "production"]

INVALID_PID = -1
