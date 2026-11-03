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

    def as_crewai_agent(self) -> dict:
        """
        Returns a CrewAI-compliant agent specification dictionary containing
        the role, goal, backstory, tools, and verbose flag.
        """
        return {
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "tools": self.tools,
            "verbose": self.verbose,
        }

    def as_adk_agent(self):
        """
        Returns an instance of google.adk.Agent representing this specialist agent
        in the Google Agent Development Kit (ADK) framework.
        """
        try:
            import google.adk as adk
            clean_name = self.role.replace(" ", "")
            instruction = f"{self.backstory}\nGoal: {self.goal}"
            return adk.Agent(
                name=clean_name,
                description=f"{self.role}: {self.goal}",
                instruction=instruction,
            )
        except Exception as e:
            return None
