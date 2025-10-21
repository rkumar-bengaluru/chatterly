
from enum import Enum

class AgentUserInteractionState(Enum):
    WAITING_FOR_AGENT = "waiting_question"
    AGENT_GENERATING_AUDIO = "agent_generating_audio"
    AGENT_GENERATING_AUDIO_DONE = "agent_generating_audio_done"
    AGENT_SPEAKING = "agent_speaking"
    AGENT_SPEAKING_DONE = "agent_speaking_done"
    WAITING_SUBTASK_1 = "WAITING_ANSWER"
    WAITING_SUBTASK_2 = "waiting_subtask_2"
    COMPLETED = "Completed"
    TIMED_OUT = "Timed_out"
    WAITING_QUESTION = "waiting_question"
    WAITING_ANSWER = "waiting_answer"