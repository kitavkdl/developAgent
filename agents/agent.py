"""
agents/agent.py

AI Secretary Pro V1.0
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from llm.model import llm
from memory.chat_memory import memory
from tools import get_tools


class AIAssistant:
    """AI Secretary"""

    def __init__(self):

        self.tools = get_tools()

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
너는 회사 AI 비서이다.

규칙

1. 회사 규정은 pdf_search를 사용한다.

2. 계산은 calculator를 사용한다.

3. 현재 시간은 current_time을 사용한다.

4. 최신 정보는 web_search를 사용한다.

5. 문서 목록은 document_info를 사용한다.

6. 모르면 모른다고 답한다.

친절하고 간결하게 답변한다.
                    """,
                ),

                MessagesPlaceholder("chat_history"),

                ("human", "{input}"),

                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

        self.agent = create_tool_calling_agent(
            llm=llm,
            tools=self.tools,
            prompt=self.prompt,
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
        )

    # -----------------------------------------

    def ask(self, question: str) -> str:

        result = self.executor.invoke(
            {
                "input": question,
                "chat_history": memory.messages(),
            }
        )

        answer = result["output"]

        memory.add_user(question)

        memory.add_ai(answer)

        return answer


assistant = AIAssistant()


if __name__ == "__main__":

    print("=" * 60)

    while True:

        question = input("\n질문(q 종료): ")

        if question.lower() == "q":
            break

        print()

        print(assistant.ask(question))