"""
TRIPPY Backend — Base Agent Architecture

Provides the foundation for the five specialist CrewAI agents.
Compatible with standard CrewAI Agent specifications while supporting
both LLM-assisted execution and deterministic fallbacks.
"""

from typing import Any, Callable, List, Optional
from pydantic import BaseModel


class TrippyAgent:
    """
    Represents an autonomous agent with a role, goal, backstory,
    reusable tools, and typed execution contract.
    """

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[List[Callable[..., Any]]] = None,
        verbose: bool = True,
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.verbose = verbose

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role='{self.role}'>"
