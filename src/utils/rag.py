from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
import gradio as gr

SYSTEM_PROMPT_TEMPLATE = """
        Eres un asistente experto y amable que representa a la empresa AgroTech.
        Estás chateando con un usuario sobre AgroTech.
        Si es pertinente, utiliza el contexto proporcionado para responder a cualquier pregunta.
        Si no sabes la respuesta, dilo.
        Contexto:
        {context}
    """

def connect_chroma(DB_NAME: str, MODEL: str):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)

    retriever = vectorstore.as_retriever()
    llm = ChatOpenAI(temperature=0, model=MODEL)

    return retriever, llm

def answer_question(question: str, history, retriever, llm):
    docs = retriever.invoke(question)
    context = "\n\n".join(doc.page_content for doc in docs)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=question)])
    return response.content
