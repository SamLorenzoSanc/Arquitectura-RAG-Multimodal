"""Agentic RAG agrícola: el agente decide herramientas (KB, clima, precios).

Comparación controlada frente al Hybrid RAG (Dense+BM25+RRF).
"""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from services.rag_service import (
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    RAGService,
    Result,
)


def _looks_like_price(q: str) -> bool:
    ql = q.lower()
    keys = (
        "precio",
        "mercado",
        "€",
        "euro",
        "cotiz",
        "venta",
        "margen",
        "petróleo",
        "petroleo",
        "gasoil",
        "combustible",
        "flete",
        "prophet",
        "arimax",
        "pronóst",
        "pronost",
    )
    return any(k in ql for k in keys)


def _looks_like_weather(q: str) -> bool:
    ql = q.lower()
    keys = (
        "clima",
        "tiempo",
        "lluvia",
        "precipit",
        "temperatura",
        "calor",
        "frío",
        "frio",
        "sequía",
        "sequia",
        "viento",
        "humedad",
        "meteorolog",
    )
    return any(k in ql for k in keys)


def _looks_like_kb(q: str) -> bool:
    """Por defecto casi siempre consultamos KB; omitir solo saludos vacíos."""
    ql = q.strip().lower()
    if len(ql) < 4:
        return False
    greetings = {"hola", "buenas", "hey", "hi", "hello", "qué tal", "que tal"}
    return ql not in greetings


class AgenticRAGService:
    """
    Agentic RAG (tool-augmented): planifica herramientas, las ejecuta y sintetiza.

    Tools:
      - search_knowledge_base  → Hybrid retrieve interno (Dense+BM25+RRF)
      - get_weather           → Open-Meteo (zona de cultivo)
      - analyze_crop_prices   → Prophet/ARIMAX + exógenas
    """

    ARCHITECTURE = "agentic_tool_rag"

    SYSTEM_SYNTH = """Eres AgroPS, asistente agentic para agricultores de Canarias.
Perfil de explotación: cultivo={crop}, zona={island}, org={org}.

{farmer_context}

Has usado herramientas. Responde en español, breve y accionable.
Prioriza los hechos del perfil operativo del agricultor frente a conjeturas.
Cita fuentes de la base de conocimiento cuando las uses.
Si una herramienta falló, dilo; no inventes cifras.
Contexto de herramientas:
{tool_context}
"""

    def __init__(self, rag: RAGService | None = None):
        self.rag = rag or RAGService()
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self._farmer_profile_cache: dict[str, Any] | None = None

    def plan_tools(
        self,
        question: str,
        island: str,
        crop: str,
    ) -> list[dict[str, Any]]:
        """Planificador heurístico determinista (reproducible para el TFM)."""
        steps: list[dict[str, Any]] = []
        ql = question.lower()
        if any(
            k in ql
            for k in (
                "mi finca",
                "mi parcela",
                "fitosanit",
                "tratamiento",
                "riego",
                "catastr",
                "dotación",
                "dotacion",
                "carencia",
                "certific",
                "mi explotación",
                "mi explotacion",
            )
        ):
            steps.append(
                {
                    "tool": "get_farm_profile",
                    "reason": "Consultar hechos estructurados de la parcela del agricultor",
                    "args": {},
                }
            )
        if _looks_like_kb(question):
            steps.append(
                {
                    "tool": "search_knowledge_base",
                    "reason": "Recuperar normativa/manuales/conocimiento del tenant",
                    "args": {},
                }
            )
        if _looks_like_weather(question):
            steps.append(
                {
                    "tool": "get_weather",
                    "reason": "Variables climáticas que afectan al cultivo",
                    "args": {"island": island},
                }
            )
        if _looks_like_price(question):
            steps.append(
                {
                    "tool": "analyze_crop_prices",
                    "reason": "Analizar precios y sensibilidades del cultivo",
                    "args": {"island": island, "product_id": crop},
                }
            )
        if not steps:
            steps.append(
                {
                    "tool": "search_knowledge_base",
                    "reason": "Consulta general: recuperar contexto de KB",
                    "args": {},
                }
            )
        return steps

    async def _tool_farm_profile(self) -> dict[str, Any]:
        profile = self._farmer_profile_cache or {}
        if not profile or not profile.get("crop_id"):
            return {
                "ok": False,
                "summary": "No hay parcela estructurada cargada para este turno.",
            }
        treatments = profile.get("treatments") or []
        t_lines = []
        for t in treatments[:5]:
            t_lines.append(
                f"- {t.get('fecha')}: {t.get('producto')} "
                f"({t.get('materia_activa') or 's/m.a.'}), "
                f"carencia {t.get('carencia_dias')} días"
            )
        summary = (
            f"Parcela {profile.get('nombre')} | {profile.get('cultivo')} "
            f"({profile.get('variedad')}) en {profile.get('isla')}. "
            f"Ref.catastral={profile.get('ref_catastral')}, "
            f"{profile.get('superficie_ha')} ha. "
            f"Riego={profile.get('sistema_riego')}, "
            f"agua={profile.get('fuente_agua')}, "
            f"dotación={profile.get('dotacion_m3_ha_anio')} m³/ha·año. "
            f"Certificaciones={profile.get('certificaciones')}. "
            f"Tratamientos:\n" + ("\n".join(t_lines) if t_lines else "ninguno")
        )
        return {"ok": True, "summary": summary, "profile": profile}

    async def _tool_search_kb(
        self,
        question: str,
        tenant_id: str,
        collections: list[str] | None,
    ) -> dict[str, Any]:
        retrieval = await self.rag.fetch_context(
            question,
            tenant_id=tenant_id,
            collections=collections,
            use_reranking=False,
            use_query_rewrite=False,
        )
        chunks = retrieval.get("chunks") or []
        summary_parts = []
        for i, ch in enumerate(chunks[:5], start=1):
            src = (ch.metadata or {}).get("source", "doc")
            summary_parts.append(f"[{i}] ({src}) {ch.page_content[:400]}")
        return {
            "ok": True,
            "chunks": chunks,
            "n_chunks": len(chunks),
            "summary": "\n".join(summary_parts) or "Sin fragmentos relevantes.",
            "retrieval": retrieval.get("retrieval"),
            "retrieval_details": retrieval,
        }

    async def _tool_weather(self, island: str) -> dict[str, Any]:
        try:
            from services.forecast_service import fetch_open_meteo_weather

            df = await self.rag._run_in_thread(fetch_open_meteo_weather, island)
            tail = df.tail(7)
            last = tail.iloc[-1]
            summary = (
                f"Zona {island}. Último día: temp_max={last['max_temp']:.1f}°C, "
                f"precipitación={last['precipitation']:.1f} mm. "
                f"Media 7d temp={tail['max_temp'].mean():.1f}°C, "
                f"lluvia_acum={tail['precipitation'].sum():.1f} mm."
            )
            return {"ok": True, "summary": summary, "island": island}
        except Exception as e:
            return {"ok": False, "summary": f"Clima no disponible: {e}", "island": island}

    async def _tool_prices(self, island: str, product_id: str) -> dict[str, Any]:
        try:
            from services.forecast_service import build_price_analysis

            analysis = await self.rag._run_in_thread(
                build_price_analysis, island, product_id, 3, 0.0
            )
            impact = analysis.get("exogenous_impact") or {}
            shocks = impact.get("sensitivity_shocks") or []
            shock_txt = "; ".join(
                f"{s['label']}: {s['price_delta_pct']:+.2f}%" for s in shocks[:3]
            )
            best = analysis.get("best_model")
            p_mape = (analysis.get("prophet_metrics") or {}).get("MAPE")
            a_mape = (analysis.get("arimax_metrics") or {}).get("MAPE")
            hist = analysis.get("history") or []
            last_price = hist[-1]["price"] if hist else None
            summary = (
                f"Cultivo={impact.get('product', product_id)} en {island}. "
                f"Precio reciente≈{last_price} €/kg. Mejor modelo={best} "
                f"(Prophet MAPE={p_mape}, ARIMAX MAPE={a_mape}). "
                f"Sensibilidad shock+10%: {shock_txt}. "
                f"Volatilidad EWMA={analysis.get('volatility_ewma', {}).get('latest_vol_pct')}%."
            )
            return {"ok": True, "summary": summary, "analysis_meta": {"best_model": best}}
        except Exception as e:
            return {"ok": False, "summary": f"Precios no disponibles: {e}"}

    async def answer(
        self,
        question: str,
        *,
        tenant_id: str,
        collections: list[str] | None = None,
        model: str | None = None,
        history: list | None = None,
        island: str = "La_Palma",
        crop: str = "platano_canarias",
        organization_name: str = "AgroTech",
        farmer_context: str | None = None,
        farmer_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        t0 = time.time()
        active_model = model or self.rag.model
        self._farmer_profile_cache = farmer_profile
        plan = self.plan_tools(question, island, crop)
        trace: list[dict[str, Any]] = []
        chunks: list[Result] = []
        tool_blocks: list[str] = []
        retrieval_info = None
        retrieval_details = None

        for step in plan:
            tool = step["tool"]
            t_tool = time.time()
            if tool == "search_knowledge_base":
                out = await self._tool_search_kb(question, tenant_id, collections)
                if out.get("chunks"):
                    chunks = out["chunks"]
                retrieval_info = out.get("retrieval")
                retrieval_details = out.get("retrieval_details")
            elif tool == "get_weather":
                out = await self._tool_weather(step["args"].get("island", island))
            elif tool == "analyze_crop_prices":
                out = await self._tool_prices(
                    step["args"].get("island", island),
                    step["args"].get("product_id", crop),
                )
            elif tool == "get_farm_profile":
                out = await self._tool_farm_profile()
            else:
                out = {"ok": False, "summary": f"Herramienta desconocida: {tool}"}

            latency = (time.time() - t_tool) * 1000
            summary = out.get("summary", "")
            tool_blocks.append(f"### {tool}\n{summary}")
            trace.append(
                {
                    "tool": tool,
                    "reason": step.get("reason"),
                    "ok": bool(out.get("ok")),
                    "latency_ms": round(latency, 1),
                    "summary": summary[:500],
                }
            )

        tool_context = "\n\n".join(tool_blocks) if tool_blocks else "Sin herramientas."
        system = self.SYSTEM_SYNTH.format(
            crop=crop,
            island=island,
            org=organization_name,
            farmer_context=(farmer_context or "Sin perfil operativo de parcela."),
            tool_context=tool_context,
        )
        messages = [{"role": "system", "content": system}]
        for msg in (history or [])[-6:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        t_gen = time.time()
        response = await self.rag._create_completion(active_model, messages)
        gen_ms = (time.time() - t_gen) * 1000
        answer = response.choices[0].message.content or ""

        related = self.rag.generate_related_questions(question, chunks)

        total_ms = (time.time() - t0) * 1000
        agent_meta = {
            "architecture": self.ARCHITECTURE,
            "label": "Agentic RAG (tool-augmented)",
            "tools_planned": [s["tool"] for s in plan],
            "tools_executed": [t["tool"] for t in trace],
            "agent_trace": trace,
            "farmer_profile": farmer_profile
            or {
                "crop": crop,
                "island": island,
                "organization": organization_name,
            },
            "timings_ms": {
                "generation": round(gen_ms, 1),
                "total": round(total_ms, 1),
            },
        }

        if retrieval_details is None:
            retrieval_details = {"retrieval": retrieval_info or {}, "chunks": chunks}
        retrieval_details["agentic"] = agent_meta
        retrieval_details["architecture"] = self.ARCHITECTURE

        if retrieval_info is None:
            retrieval_info = {
                "original_query": question,
                "rewritten_query": question,
                "retrieved_chunks": len(chunks),
                "rewritten_chunks": 0,
                "merged_chunks": len(chunks),
                "final_chunks": len(chunks),
                "retrieval_k": self.rag.retrieval_k,
                "final_k": self.rag.final_k,
                "reranking": False,
            }
        retrieval_info["architecture"] = self.ARCHITECTURE
        retrieval_info["agent_tools"] = [t["tool"] for t in trace]

        return {
            "answer": answer,
            "chunks": chunks,
            "retrieval": retrieval_info,
            "retrieval_details": retrieval_details,
            "related_questions": related,
            "agent_trace": trace,
            "architecture": self.ARCHITECTURE,
            "latency_ms": round(total_ms, 1),
            "farmer_profile": agent_meta["farmer_profile"],
        }


async def run_hybrid_answer(
    rag: RAGService,
    question: str,
    *,
    tenant_id: str,
    collections: list[str] | None,
    model: str | None,
    history: list | None,
    use_reranking: bool = False,
    use_query_rewrite: bool = False,
    farmer_context: str | None = None,
    farmer_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t0 = time.time()
    result = await rag.answer(
        question=question,
        history=history,
        tenant_id=tenant_id,
        collections=collections,
        model=model,
        use_reranking=use_reranking,
        use_query_rewrite=use_query_rewrite,
        farmer_context=farmer_context,
        farmer_profile=farmer_profile,
    )
    latency = (time.time() - t0) * 1000
    details = result.get("retrieval_details") or {}
    details["architecture"] = "hybrid_dense_bm25_rrf"
    details["label"] = "Hybrid RAG (Dense + BM25 + RRF)"
    if farmer_profile:
        details["farmer_profile"] = farmer_profile
    result["retrieval_details"] = details
    if result.get("retrieval") is not None:
        result["retrieval"]["architecture"] = "hybrid_dense_bm25_rrf"
    result["architecture"] = "hybrid_dense_bm25_rrf"
    result["latency_ms"] = round(latency, 1)
    result["agent_trace"] = None
    result["farmer_profile"] = farmer_profile
    return result


def pack_mode_side(result: dict[str, Any], mode: str) -> dict[str, Any]:
    """Serializa un lado de la comparación para la API."""
    chunks_out = []
    for chunk in result.get("chunks") or []:
        if isinstance(chunk, dict):
            chunks_out.append(chunk)
        else:
            chunks_out.append(
                {
                    "type": getattr(chunk, "type", "chunk"),
                    "page_content": getattr(chunk, "page_content", ""),
                    "metadata": getattr(chunk, "metadata", {}) or {},
                }
            )
    return {
        "mode": mode,
        "architecture": result.get("architecture"),
        "answer": result.get("answer") or "",
        "context": chunks_out,
        "retrieval": result.get("retrieval"),
        "retrieval_details": result.get("retrieval_details"),
        "agent_trace": result.get("agent_trace"),
        "related_questions": result.get("related_questions") or [],
        "latency_ms": result.get("latency_ms"),
    }
