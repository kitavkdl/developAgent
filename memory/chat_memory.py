"""
memory/chat_memory.py

AI Secretary Pro V1.0
"""

from langchain_core.chat_history import InMemoryChatMessageHistory


class ChatMemory:

    def __init__(self):

        self.history = InMemoryChatMessageHistory()

    # ----------------------------

    def add_user(self, text: str):

        self.history.add_user_message(text)

    # ----------------------------

    def add_ai(self, text: str):

        self.history.add_ai_message(text)

    # ----------------------------

    def messages(self):

        return self.history.messages

    # ----------------------------

    def clear(self):

        self.history.clear()


memory = ChatMemory()