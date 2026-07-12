from models.prompt_base import PromptBase


class RandomPrompt(PromptBase):
    def __init__(self, prompt_id: str, workout_id: str, message: str):
        super().__init__(prompt_id, workout_id, message)

    def send(self):
        """Send the prompt to user."""
        print(f"[Random Prompt] {self._message}")

    def get_prompt_id(self):
        """Get prompt ID."""
        return self._prompt_id

    def get_workout_id(self):
        """Get workout ID."""
        return self._workout_id

    def get_message(self):
        """Get prompt message."""
        return self._message