# services/tool.py
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama
from langchain.agents import create_agent

class DocumentSearchInput(BaseModel):
    query: str = Field(description="La consulta de búsqueda en lenguaje natural para encontrar documentos")
    tenant_id: str = Field(description="El ID del tenant para filtrar documentos")
    knowledge_base_id: str | None = Field(None, description="ID opcional de base de conocimiento")


@tool("search_documents", args_schema=DocumentSearchInput)
def search_documents_tool(query: str, tenant_id: str, knowledge_base_id: str | None = None):
    """Busca regulaciones (PAC), manuales y datos históricos textuales en la base de datos."""
    from services import rag as rag_service
    results = rag_service.retrieve(query, tenant_id, knowledge_base_id)
    return results

tools = [search_documents_tool]

llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    base_url="http://localhost:11434"
)

system_prompt = """Eres AgroPS, el asistente documental agrícola.
Tu objetivo es responder con evidencia recuperada del corpus.

Tienes acceso a search_documents para buscar regulaciones, manuales y datos históricos.

Ante una pregunta:
1. Piensa si necesitas usar una herramienta.
2. Si es así, llama a la herramienta adecuada.
3. Responde en español basándote SOLO en los resultados, con esta estructura:
   Diagnóstico; Procedimiento paso a paso; Información técnica; Herramientas y recambios; Precauciones.
"""

agent_executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)
