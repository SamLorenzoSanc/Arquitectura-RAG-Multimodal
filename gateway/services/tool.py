# services/tool.py
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Importaciones de LangGraph y Ollama
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage

# --- 1. Definición de Herramientas ---
from .forecast_service import run_prophet_forecast, run_arimax_forecast, build_unified_dataset

class DocumentSearchInput(BaseModel):
    query: str = Field(description="La consulta de búsqueda en lenguaje natural para encontrar documentos")
    tenant_id: str = Field(description="El ID del tenant para filtrar documentos")
    knowledge_base_id: str | None = Field(None, description="ID opcional de base de conocimiento")

class ForecastInput(BaseModel):
    island: str = Field(description="La isla canaria objetivo (ej. 'Tenerife_Norte')")
    horizon_months: int = Field(default=3, description="Meses a futuro para la predicción")
    model_type: str = Field(default="prophet", description="Tipo de modelo: 'prophet' o 'arimax'")

@tool("search_documents", args_schema=DocumentSearchInput)
def search_documents_tool(query: str, tenant_id: str, knowledge_base_id: str | None = None):
    """Busca regulaciones (PAC), manuales y datos históricos textuales en la base de datos."""
    # Importar aquí para evitar referencias circulares si es necesario
    from services import rag_service 
    results = rag_service.retrieve(query, tenant_id, knowledge_base_id)
    return results

@tool("predict_agricultural_prices", args_schema=ForecastInput)
def predict_prices_tool(island: str, horizon_months: int, model_type: str):
    """Estima precios futuros o analiza impacto climático en los cultivos."""
 
    try:
        df = build_unified_dataset(island)
        if model_type.lower() == "prophet":
            metrics, points = run_prophet_forecast(df, horizon_months, 0)
        else:
            metrics, points = run_arimax_forecast(df, horizon_months, 0)
        return {"status": "success", "model": model_type, "forecast": points}
    except Exception as e:
        return {"status": "error", "message": str(e)}

tools = [search_documents_tool, predict_prices_tool]

# --- 2. Configuración del LLM Local ---
# Usamos llama3.1 o qwen2.5 optimizados para Tool Calling
llm = ChatOllama(
    model="llama3.1",
    temperature=0, 
    base_url="http://localhost:11434"
)

# --- 3. Prompt del Sistema ---
# En LangGraph, el prompt del sistema se pasa como un SystemMessage directo
system_prompt = """Eres un asistente experto en agricultura inteligente para las Islas Canarias (AgroPS).
Tu objetivo es ayudar a agricultores gestionando sus workspaces.

Tienes acceso a herramientas:
1. search_documents: Para buscar regulaciones (PAC), manuales y datos históricos.
2. predict_agricultural_prices: Para estimar precios futuros o analizar impacto climático.

Ante una pregunta:
1. Piensa si necesitas usar una herramienta.
2. Si es así, llama a la herramienta adecuada.
3. Responde al usuario en español basándote SOLO en los resultados devueltos por las herramientas.
"""

# --- 4. Creación del Agente con LangGraph ---
# create_react_agent construye el AgentState, el bucle de razonamiento y el ejecutor por ti.
agent_executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)