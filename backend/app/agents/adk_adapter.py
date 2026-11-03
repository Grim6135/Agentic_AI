"""
TRIPPY Backend — Google Agent Development Kit (ADK) Integration Adapter

Connects the five specialist agents (Destination, Transport, Stay & Activity,
Budget, and Itinerary) into the Google Agent Development Kit (ADK) framework,
allowing deployment as a graph-based multi-agent workflow.
"""

import logging
from typing import Any, Dict, List, Optional
import google.adk as adk

from app.agents.budget import BudgetAgent
from app.agents.destination import DestinationAgent
from app.agents.itinerary import ItineraryAgent
from app.agents.stay_activity import StayActivityAgent
from app.agents.transport import TransportAgent

logger = logging.getLogger("trippy.adk")


class TrippyADKWorkflow:
    """
    Adapter orchestrating the 5 specialist agents as a Google ADK Workflow graph.
    """

    def __init__(self):
        self.destination_specialist = DestinationAgent()
        self.transport_specialist = TransportAgent()
        self.stay_activity_specialist = StayActivityAgent()
        self.budget_specialist = BudgetAgent()
        self.itinerary_specialist = ItineraryAgent()

        self._adk_agents: Dict[str, adk.Agent] = {}
        self._initialize_adk_agents()

    def _initialize_adk_agents(self):
        """Builds Google ADK Agent instances for each specialist."""
        self._adk_agents = {
            "DestinationSpecialist": self.destination_specialist.as_adk_agent(),
            "TransportSpecialist": self.transport_specialist.as_adk_agent(),
            "StayActivitySpecialist": self.stay_activity_specialist.as_adk_agent(),
            "BudgetSpecialist": self.budget_specialist.as_adk_agent(),
            "ItinerarySpecialist": self.itinerary_specialist.as_adk_agent(),
        }

    @property
    def adk_agents(self) -> List[adk.Agent]:
        """Returns all 5 agents as Google ADK Agent objects."""
        return [ag for ag in self._adk_agents.values() if ag is not None]

    def build_workflow(self) -> adk.Workflow:
        """
        Builds and returns the complete Google ADK Workflow representing
        the Trippy travel planning multi-agent system.
        """
        workflow = adk.Workflow(
            name="TrippyMultiAgentPlanningWorkflow",
            description=(
                "Google ADK Multi-Agent Trip Planner coordinating 5 specialist agents: "
                "Destination selection, Transit estimation, Lodging & Activities curation, "
                "Budget validation, and Itinerary synthesis."
            ),
        )
        return workflow

    def get_framework_info(self) -> Dict[str, Any]:
        """Provides diagnostic and version information for Google ADK."""
        return {
            "framework": "Google Agent Development Kit (ADK)",
            "version": getattr(adk, "__version__", "installed"),
            "registered_agents": list(self._adk_agents.keys()),
            "workflow_name": "TrippyMultiAgentPlanningWorkflow",
            "status": "ready",
        }


adk_workflow_service = TrippyADKWorkflow()
