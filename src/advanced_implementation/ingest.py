from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion
from multiprocessing import Pool
from tenacity import retry, wait_exponential


load_dotenv(override=True)

MODEL = "ollama/llama3"

DB_NAME = str(Path(__file__).parent.parent.parent / "notebooks/preprocessed_db")
collection_name = "docs"
embedding_model = "qwen3-embedding:latest"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent.parent / "knowledge-base"
AVERAGE_CHUNK_SIZE = 100
wait = wait_exponential(multiplier=1, min=10, max=240)


WORKERS = 3

openai = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


class Result(BaseModel):
    page_content: str
    metadata: dict


class Chunk(BaseModel):
    headline: str = Field(
        description="Un título breve para este fragmento, normalmente de unas pocas palabras, que tenga mayor probabilidad de aparecer en una consulta",
    )
    summary: str = Field(
        description="Unas pocas frases que resumen el contenido de este fragmento para responder preguntas habituales"
    )
    original_text: str = Field(
        description="El texto original de este fragmento extraído del documento proporcionado, exactamente como aparece, sin modificarlo de ninguna manera"
    )

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )


class Chunks(BaseModel):
    chunks: list[Chunk]


def fetch_documents():
    """A homemade version of the LangChain DirectoryLoader"""

    documents = []

    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        doc_type = folder.name
        for file in folder.rglob("*.md"):
            with open(file, "r", encoding="utf-8") as f:
                documents.append({"type": doc_type, "source": file.as_posix(), "text": f.read()})

    print(f"Loaded {len(documents)} documents")
    return documents


def make_prompt(document):
    how_many = (len(document["text"]) // AVERAGE_CHUNK_SIZE) + 1
    return f"""
        Tomas un documento y lo divides en fragmentos superpuestos para una base de conocimientos.

        El documento procede de la unidad compartida de una empresa llamada AgroTech.
        El documento es de tipo: {document["type"]}
        El documento se ha obtenido de: {document["source"]}
        - Responde únicamente en español.
        - No inventes información.
        - No completes datos que no aparezcan.
        - No utilices placeholders como:
            - [Insert...]
            - TBD
            - Lorem Ipsum
            - Example
            - Si un dato no existe en el documento, simplemente no lo menciones.
            - Conserva exactamente nombres propios, números y fechas.
            - El campo original_text debe contener exactamente el texto original.
            Debes dividir el documento como consideres oportuno, asegurándote de que todo el documento quede incluido en los fragmentos; no omitas nada.
            Probablemente, este documento debería dividirse en al menos {how_many} fragmentos, pero puedes tener más o menos según convenga, asegurándote de que haya fragmentos individuales para responder a preguntas específicas.
            Debe haber solapamiento entre los fragmentos según sea necesario; normalmente, un solapamiento de alrededor del 25 % o unas 50 palabras, de modo que el mismo texto aparezca en varios fragmentos para obtener los mejores resultados de recuperación.
    
            Para cada fragmento, debes proporcionar un título, un resumen y el texto original del fragmento.
            En conjunto, tus fragmentos deben representar el documento completo con solapamiento.
    
            Aquí está el documento:

            {document["text"]}
    """


def make_messages(document):
    return [
        {"role": "user", "content": make_prompt(document)},
    ]


@retry(wait=wait)
def process_document(document):
    messages = make_messages(document)
    response = completion(model=MODEL, messages=messages, response_format=Chunks)
    reply = response.choices[0].message.content
    doc_as_chunks = Chunks.model_validate_json(reply).chunks
    return [chunk.as_result(document) for chunk in doc_as_chunks]


def create_chunks(documents):
    """
    Create chunks using a number of workers in parallel.
    If you get a rate limit error, set the WORKERS to 1.
    """
    chunks = []
    with Pool(processes=WORKERS) as pool:
        for result in tqdm(pool.imap_unordered(process_document, documents), total=len(documents)):
            chunks.extend(result)
    return chunks


def create_embeddings(chunks):
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [chunk.page_content for chunk in chunks]
    emb = openai.embeddings.create(model=embedding_model, input=texts).data
    vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(collection_name)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore created with {collection.count()} documents")


if __name__ == "__main__":
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
