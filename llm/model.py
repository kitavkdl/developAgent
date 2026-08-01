"""
llm/model.py

AI Secretary Pro V1.0
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config.settings import settings


def get_llm(
    temperature: float = 0.2,
    streaming: bool = True,
):
    """
    OpenAI Chat Model
    """

    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        streaming=streaming,
    )


def get_embeddings():
    """
    OpenAI Embedding Model
    """

    return OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY,
        model=settings.EMBEDDING_MODEL,
    )


# Singleton
llm = get_llm()

embeddings = get_embeddings()


if __name__ == "__main__":

    response = llm.invoke("안녕하세요.")

    print(response.content)