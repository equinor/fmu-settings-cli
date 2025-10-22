"""Contains constants used between modules."""

from typing import Literal, TypeAlias

HOST: str = "localhost"
API_PORT: int = 8001
GUI_PORT: int = 8000

GuiPort: TypeAlias = Literal[5173, 3000, 8000]
APP_REG_PORTS: list[int] = [5173, 3000, 8000]
"""These are ports that are known to the Azure App Registration."""

LogLevel: TypeAlias = Literal["debug", "info", "warning", "error", "critical"]

INVALID_PID = -1
