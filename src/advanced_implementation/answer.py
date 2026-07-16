from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from litellm import completion
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential


load_dotenv(override=True)

# MODEL = "openai/gpt-4.1-nano"
MODEL = "ollama/llama3"
DB_NAME = str(Path(__file__).parent.parent.parent / "notebooks/preprocessed_db")
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent.parent / "knowledge-base"

collection_name = "docs"
embedding_model = "qwen3-embedding:latest"
wait = wait_exponential(multiplier=1, min=10, max=240)

openai = OpenAI()

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

RETRIEVAL_K = 20
FINAL_K = 10

SYSTEM_PROMPT = """
Eres un asistente experto y amable que representa a la empresa Insurellm.
Estás chateando con un usuario sobre Insurellm.
Tu respuesta se evaluará en cuanto a su precisión, relevancia y exhaustividad, así que asegúrate de que se limite a responder a la pregunta y lo haga de forma completa.
Si no sabes la respuesta, dilo.
Para contextualizar, aquí tienes algunos extractos concretos de la base de conocimientos que podrían ser directamente relevantes para la pregunta del usuario:
{context}

Teniendo en cuenta este contexto, responde a la pregunta del usuario. Sé preciso, relevante y exhaustivo.
"""


class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="Orden de relevancia de los fragmentos, de más relevante a menos relevante, según el número de identificación de cada fragmento"
    )


@retry(wait=wait)
def rerank(question, chunks):
    system_prompt = """
        Eres un sistema de reordenación de documentos.
        Se te proporciona una pregunta y una lista de fragmentos de texto relevantes extraídos de una consulta a una base de conocimientos.
        Los fragmentos se proporcionan en el orden en que se han recuperado; este orden debería estar aproximadamente ordenado por relevancia, pero es posible que puedas mejorarlo.
        Debes clasificar los fragmentos proporcionados por orden de relevancia respecto a la pregunta, colocando el más relevante en primer lugar.
        Responde únicamente con la lista de identificadores de los fragmentos clasificados, nada más. Incluye todos los identificadores de fragmentos que se te hayan proporcionado, reordenados.
        """
    user_prompt = f"El usuario ha formulado la siguiente pregunta:\n\n{question}\n\nOrdena todos los fragmentos de texto por relevancia respecto a la pregunta, de más relevante a menos relevante. Incluye todos los identificadores de fragmento que se te han facilitado, reordenados.\n\n"
    user_prompt += "Aquí están los fragmentos:\n\n"
    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += "Responde únicamente con la lista de los identificadores de fragmentos ordenados por prioridad, nada más."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = completion(model=MODEL, messages=messages, response_format=RankOrder)
    reply = response.choices[0].message.content
    order = RankOrder.model_validate_json(reply).order
    return [chunks[i - 1] for i in order]


def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )


@retry(wait=wait)
def rewrite_query(question, history=[]):
    """Rewrite the user's question to be a more specific question that is more likely to surface relevant content in the Knowledge Base."""
    message = f"""
        Estás manteniendo una conversación con un usuario y respondiendo a preguntas sobre la empresa Insurellm.
        Estás a punto de consultar información en una base de conocimientos para responder a la pregunta del usuario.

        Este es el historial de tu conversación con el usuario hasta el momento:
        {history}

        Y esta es la pregunta actual del usuario:
        {question}

        Responde únicamente con una pregunta breve y concisa que vayas a utilizar para buscar en la base de conocimientos.
        Debe ser una pregunta MUY breve y específica que tenga más probabilidades de mostrar resultados. Céntrate en los detalles de la pregunta.
        IMPORTANTE: Responde ÚNICAMENTE con la consulta exacta de la base de conocimientos, nada más.
    """
    response = completion(model=MODEL, messages=[{"role": "system", "content": message}])
    return response.choices[0].message.content


def merge_chunks(chunks, reranked):
    merged = chunks[:]
    existing = [chunk.page_content for chunk in chunks]
    for chunk in reranked:
        if chunk.page_content not in existing:
            merged.append(chunk)
    return merged


def fetch_context_unranked(question):
    query = openai.embeddings.create(model=embedding_model, input=[question]).data[0].embedding
    results = collection.query(query_embeddings=[query], n_results=RETRIEVAL_K)
    chunks = []
    for result in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=result[0], metadata=result[1]))
    return chunks


def fetch_context(original_question):
    rewritten_question = rewrite_query(original_question)
    chunks1 = fetch_context_unranked(original_question)
    chunks2 = fetch_context_unranked(rewritten_question)
    chunks = merge_chunks(chunks1, chunks2)
    reranked = rerank(original_question, chunks)
    return reranked[:FINAL_K]


@retry(wait=wait)
def answer_question(question: str, history: list[dict] = []) -> tuple[str, list]:
    """
    Answer a question using RAG and return the answer and the retrieved context
    """
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)
    response = completion(model=MODEL, messages=messages)
    return response.choices[0].message.content, chunks
