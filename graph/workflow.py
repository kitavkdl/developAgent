"""
graph/workflow.py

AI Secretary Pro V1.0
"""

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from assistant import assistant


class ChatState(TypedDict):
    question: str
    answer: str


# ------------------------------------


def assistant_node(state: ChatState):

    answer = assistant.ask(state["question"])

    return {
        "question": state["question"],
        "answer": answer,
    }


# ------------------------------------

builder = StateGraph(ChatState)

builder.add_node(
    "assistant",
    assistant_node,
)

builder.add_edge(
    START,
    "assistant",
)

builder.add_edge(
    "assistant",
    END,
)

workflow = builder.compile()


# ------------------------------------

if __name__ == "__main__":

    while True:

        q = input("\n질문(q 종료): ")

        if q.lower() == "q":
            break

        result = workflow.invoke(
            {
                "question": q,
                "answer": "",
            }
        )

        print()

        print(result["answer"])