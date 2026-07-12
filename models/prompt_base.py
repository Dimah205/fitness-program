from abc import ABC, abstractmethod

class PromptBase(ABC):
    def __init__(self, prompt_id: str, workout_id: str, message: str):
        self._prompt_id = prompt_id
        self._workout_id = workout_id
        self._message = message
        self._user_reply = None

    @abstractmethod
    def send(self):
        pass

    def set_user_reply(self, reply: str):
        self._user_reply = reply

    def get_user_reply(self):
        return self._user_reply