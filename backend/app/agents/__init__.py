from .base import TrippyAgent
from .budget import BudgetAgent
from .crew import TrippyCrew
from .destination import DestinationAgent
from .itinerary import ItineraryAgent
from .stay_activity import StayActivityAgent
from .transport import TransportAgent

__all__ = [
    "BudgetAgent",
    "DestinationAgent",
    "ItineraryAgent",
    "StayActivityAgent",
    "TransportAgent",
    "TrippyADKWorkflow",
    "TrippyAgent",
    "TrippyCrew",
    "adk_workflow_service",
]


def __getattr__(name: str):
    if name in {"TrippyADKWorkflow", "adk_workflow_service"}:
        from . import adk_adapter
        return getattr(adk_adapter, name)
    raise AttributeError(name)
