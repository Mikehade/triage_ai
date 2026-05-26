from __future__ import annotations
from abc import ABC, abstractmethod


class IKnowledgeStore(ABC):
    """
    Concrete base for infrastructure knowledge store implementations.
    Mirrors domain/knowledge/repository.py but lives in infrastructure
    since it carries implementation-level concerns (search config, timeouts).
    """

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def get_drug_interactions(self, medications: list[str]) -> list[dict]:
        raise NotImplementedError