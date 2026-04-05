from typing import Optional

from pydantic import BaseModel, ConfigDict


class Server(BaseModel):
    id: int
    ip: str
    port: int
    mode: str
    modeAlt: str
    category: str
    players: int
    maxplayers: int
    faceit_avg: int
    location: str
    map: str
    prime: int
    num: Optional[int] = None
    time_avg_complete: Optional[int] = None
    id_games: int
    name_alt: Optional[str] = None


class ServersPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    result: str
    servers: dict[str, dict[str, dict[str, list[Server]]]]


class ServersModule(BaseModel):
    data: ServersPayload


class Modules(BaseModel):
    model_config = ConfigDict(extra="ignore")
    servers: ServersModule


class DataBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    modules: Modules


class Servers(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: DataBlock
