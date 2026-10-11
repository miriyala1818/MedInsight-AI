from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    agent_name: str

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
