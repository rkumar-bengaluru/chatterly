
from enum import Enum

class InteractionState(Enum):
    WAITING_QUESTION = "waiting_question"
    WAITING_SUBTASK_1 = "waiting_subtask_1"
    WAITING_SUBTASK_2 = "waiting_subtask_2"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"