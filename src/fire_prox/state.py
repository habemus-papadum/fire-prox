from enum import Enum, auto


class State(Enum):
    """Represents the state of a FireObject."""
    DETACHED = auto()
    ATTACHED = auto()
    LOADED = auto()
    DELETED = auto()
