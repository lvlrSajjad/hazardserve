"""hazardserve: hazard-aware placement and pre-emptive migration for stateful LLM requests."""
from .cost import MigrationCost, NodeSpec, Request, service_time
from .crossover import LINK_CLASSES, LinkClass, crossover_table, crossover_tokens
from .hazard import HazardModel, SurvivalCurve, kaplan_meier
from .policy import HazardAwarePolicy, OraclePolicy, RandomPolicy, ReactivePolicy
from .simulator import Simulator

__all__ = [
    "HazardAwarePolicy",
    "HazardModel",
    "LINK_CLASSES",
    "LinkClass",
    "MigrationCost",
    "NodeSpec",
    "OraclePolicy",
    "RandomPolicy",
    "ReactivePolicy",
    "Request",
    "Simulator",
    "SurvivalCurve",
    "crossover_table",
    "crossover_tokens",
    "kaplan_meier",
    "service_time",
]
__version__ = "0.1.0"
