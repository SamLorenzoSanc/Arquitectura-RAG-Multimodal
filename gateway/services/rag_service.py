from pathlib import Path

from chromadb import PersistentClient
from dotenv import load_dotenv
from litellm import completion
from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, wait_exponential

load_dotenv(override=True)

WAIT_POLICY = wait_exponential(
    multiplier=1,
    min=10,
    max=240,
)

class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="Orden de relevancia de los fragmentos"
    )


class RAGService:

    SYSTEM_PROMPT = """
    Eres un asistente experto y amable que representa a la empresa Insurellm.

    Contexto:
    {context}
    """

    def __init__(self, model: str = "ollama/llama3", embedding_model: str = "text-embedding-3-large", db_path: str | None = None, collection_name: str = "docs", retrieval_k: int = 20, final_k: int = 10):

        if db_path is None:
            db_path = str( Path(__file__).parent.parent.parent / "notebooks/preprocessed_db")

        self.model = model
        self.embedding_model = embedding_model

        self.retrieval_k = retrieval_k
        self.final_k = final_k

        self.wait = wait_exponential(
            multiplier=1,
            min=10,
            max=240,
        )

        self.openai = OpenAI(api_key="ollama")

        self.chroma = PersistentClient(path=db_path)

        self.collection = self.chroma.get_or_create_collection(
            collection_name
        )

    @retry(wait=WAIT_POLICY)
    def rewrite_query(self, question, history=None):

        if history is None:
            history = []

        prompt = f"""
        Historial:

        {history}

        Pregunta:

        {question}

        Reescribe únicamente la consulta.
        """

        response = completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                }
            ],
        )

        return response.choices[0].message.content
    
    def retrieve(self, question: str) -> list[Result]:

        embedding = self.openai.embeddings.create(
            model=self.embedding_model,
            input=[question],
        ).data[0].embedding

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=self.retrieval_k,
        )

        chunks = []

        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):

            chunks.append(
                Result(
                    page_content=doc,
                    metadata=meta,
                )
            )

        return chunks
    
    def merge_chunks(self, chunks1, chunks2):

        merged = chunks1.copy()

        existing = {
            chunk.page_content
            for chunk in chunks1
        }

        for chunk in chunks2:
            if chunk.page_content not in existing:
                merged.append(chunk)

        return merged
    
    @retry(wait=WAIT_POLICY)
    def rerank(self, question, chunks):
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
        response = completion(model=self.model, messages=messages, response_format=RankOrder)
        reply = response.choices[0].message.content
        order = RankOrder.model_validate_json(reply).order
        return [chunks[i - 1] for i in order]
    
    def build_prompt(self, question, history, chunks):

        context = "\n\n".join(f"Extract from {c.metadata['source']}:\n{c.page_content}" for c in chunks)

        return (
            [{"role": "system", "content": self.SYSTEM_PROMPT.format(context=context)}] + history + [{"role": "user", "content": question}]
        )
    def fetch_context(self, question):
        print("Fetch 1")
        rewritten = self.rewrite_query(question)

        print("Fetch 2")
        original = self.retrieve(question)

        print("Fetch 3")
        rewritten_chunks = self.retrieve(rewritten)

        print("Fetch 4")
        merged = self.merge_chunks(original, rewritten_chunks)

        print("Fetch 5")
        reranked = self.rerank(question, merged)

        print("Fetch 6")


        return reranked[: self.final_k]
    
    @retry(wait=WAIT_POLICY)
    def answer(self,question,history=None):

        if history is None:
            history = []
        print("1")
        chunks = self.fetch_context(question)

        print("2")
        messages = self.build_prompt(question, history, chunks)
        print("3")

        response = completion(model=self.model, messages=messages)

        return (
            response.choices[0].message.content,
            chunks
        )