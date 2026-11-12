from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def test_openai_connection():

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    response = llm.invoke(
        "Reply with exactly: OpenAI connection successful"
    )

    print(response.content)

    assert response.content