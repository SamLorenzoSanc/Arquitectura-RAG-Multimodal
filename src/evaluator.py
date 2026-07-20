import gradio as gr
import pandas as pd
from collections import defaultdict
from dotenv import load_dotenv

from evaluation.eval import evaluate_all_retrieval, evaluate_all_answers

load_dotenv(override=True)

# Color coding thresholds - Retrieval
MRR_GREEN = 0.9
MRR_AMBER = 0.75
NDCG_GREEN = 0.9
NDCG_AMBER = 0.75
COVERAGE_GREEN = 90.0
COVERAGE_AMBER = 75.0

# Color coding thresholds - Answer (1-5 scale)
ANSWER_GREEN = 4.5
ANSWER_AMBER = 4.0


def get_color_theme(value: float, metric_type: str) -> tuple[str, str]:
    """Get gradient colors and glowing borders based on metric values."""
    is_green = False
    is_amber = False

    if metric_type == "mrr":
        is_green, is_amber = value >= MRR_GREEN, value >= MRR_AMBER
    elif metric_type == "ndcg":
        is_green, is_amber = value >= NDCG_GREEN, value >= NDCG_AMBER
    elif metric_type == "coverage":
        is_green, is_amber = value >= COVERAGE_GREEN, value >= COVERAGE_AMBER
    elif metric_type in ["accuracy", "completeness", "relevance"]:
        is_green, is_amber = value >= ANSWER_GREEN, value >= ANSWER_AMBER

    if is_green:
        return "rgba(16, 185, 129, 0.15)", "#10b981"  # Emerald Green
    elif is_amber:
        return "rgba(245, 158, 11, 0.15)", "#f59e0b"  # Amber Orange
    else:
        return "rgba(239, 68, 68, 0.15)", "#ef4444"   # Rose Red


def format_metric_html(
    label: str,
    value: float,
    metric_type: str,
    is_percentage: bool = False,
    score_format: bool = False,
) -> str:
    """Format a metric into a futuristic glassmorphism KPI card."""
    bg_color, border_color = get_color_theme(value, metric_type)
    
    if is_percentage:
        value_str = f"{value:.1f}%"
    elif score_format:
        value_str = f"{value:.2f} <span style='font-size: 16px; color: #6b7280;'>/ 5.0</span>"
    else:
        value_str = f"{value:.4f}"

    return f"""
    <div style="
        margin: 12px 0; 
        padding: 20px; 
        background: {bg_color}; 
        border-radius: 12px; 
        border: 1px solid {border_color}; 
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease;
    ">
        <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 6px;">
            {label}
        </div>
        <div style="font-size: 32px; font-weight: 800; color: #ffffff; text-shadow: 0 0 10px {border_color}88;">
            {value_str}
        </div>
    </div>
    """


def run_retrieval_evaluation(progress=gr.Progress()):
    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    category_mrr = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_retrieval():
        count += 1
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_coverage += result.keyword_coverage
        category_mrr[test.category].append(result.mrr)

        progress(prog_value, desc=f"⚡ Analizando prueba #{count}...")

    avg_mrr = total_mrr / count
    avg_ndcg = total_ndcg / count
    avg_coverage = total_coverage / count

    final_html = f"""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        {format_metric_html("Mean Reciprocal Rank (MRR)", avg_mrr, "mrr")}
        {format_metric_html("Normalized DCG (nDCG)", avg_ndcg, "ndcg")}
        {format_metric_html("Cobertura de Palabras Clave", avg_coverage, "coverage", is_percentage=True)}
        
        <div style="margin-top: 15px; padding: 12px; background: rgba(16, 185, 129, 0.1); border-radius: 8px; text-align: center; border: 1px solid #10b981; color: #34d399; font-weight: 600;">
         Evaluación de Recuperación Completada: {count} Tests Ejecutados
        </div>
    </div>
    """

    category_data = [
        {"Categoría": category, "MRR Promedio": sum(scores) / len(scores)}
        for category, scores in category_mrr.items()
    ]

    return final_html, pd.DataFrame(category_data)


def run_answer_evaluation(progress=gr.Progress()):
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0
    category_accuracy = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_answers():
        count += 1
        total_accuracy += result.accuracy
        total_completeness += result.completeness
        total_relevance += result.relevance
        category_accuracy[test.category].append(result.accuracy)

        progress(prog_value, desc=f"🧠 Evaluando respuesta #{count}...")

    avg_accuracy = total_accuracy / count
    avg_completeness = total_completeness / count
    avg_relevance = total_relevance / count

    final_html = f"""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        {format_metric_html("Precisión Fáctica (Accuracy)", avg_accuracy, "accuracy", score_format=True)}
        {format_metric_html("Exhaustividad (Completeness)", avg_completeness, "completeness", score_format=True)}
        {format_metric_html("Pertinencia (Relevance)", avg_relevance, "relevance", score_format=True)}
        
        <div style="margin-top: 15px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; text-align: center; border: 1px solid #3b82f6; color: #60a5fa; font-weight: 600;">
            Auditoría Humana/LLM Finalizada: {count} Evaluaciones Completadas
        </div>
    </div>
    """

    category_data = [
        {"Categoría": category, "Precisión Promedio": sum(scores) / len(scores)}
        for category, scores in category_accuracy.items()
    ]

    return final_html, pd.DataFrame(category_data)


CUSTOM_CSS = """
/* Fondo general Cyberpunk/Dark */
body, .gradio-container {
    background-color: #0b0f19 !important;
    font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif !important;
}

/* Encabezados y títulos */
h1 {
    font-size: 2.2em !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #a78bfa 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0px !important;
}

/* Estilo de Botones */
button.primary-btn {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    border: none !important;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4) !important;
    transition: all 0.3s ease !important;
    border-radius: 8px !important;
}

button.primary-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6) !important;
}

/* Pestañas (Tabs) */
.tabs {
    border-bottom: 1px solid #1f2937 !important;
}

.tab-nav button {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #9ca3af !important;
}

.tab-nav button.selected {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
    background: transparent !important;
}
"""

def main():
    theme = gr.themes.Monochrome(
        primary_hue="purple",
        radius_size="lg",
    )

    with gr.Blocks(title="AgroRAG Performance Lab", theme=theme, css=CUSTOM_CSS) as app:
        
        # HEADER PRINCIPAL
        with gr.Row():
            with gr.Column():
                gr.Markdown("#AGRO-RAG AUDIT DASHBOARD")
                gr.Markdown("<span style='color: #6b7280; font-size: 14px;'>Sistema de Monitoreo e Insights para el Pipeline AgroTech RAG</span>")

        gr.HTML("<hr style='border: 0; height: 1px; background: #1f2937; margin: 15px 0;'>")

        # PANEL DE EVALUACIÓN CON PESTAÑAS (TABS)
        with gr.Tabs():
            
            # PESTAÑA 1: RETRIEVAL
            with gr.TabItem("Métrica de Recuperación (IR)"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Indicadores de Contexto")
                        retrieval_button = gr.Button("▶ Ejecutar Auditoría IR", elem_classes=["primary-btn"], size="lg")
                        retrieval_metrics = gr.HTML(
                            "<div style='padding: 40px; text-align: center; color: #4b5563; border: 1px dashed #1f2937; border-radius: 12px; margin-top: 15px;'>Haz clic en <b>Ejecutar Auditoría IR</b> para procesar la métrica de contexto.</div>"
                        )

                    with gr.Column(scale=2):
                        gr.Markdown("### Rendimiento por Categoría Normativa")
                        retrieval_chart = gr.BarPlot(
                            x="Categoría",
                            y="MRR Promedio",
                            title="",
                            y_lim=[0, 1],
                            height=380,
                            color_accent="#8b5cf6"
                        )

            # PESTAÑA 2: ANSWER EVALUATION
            with gr.TabItem("Evaluación de Calidad de Respuesta"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Calificación LLM-as-a-Judge")
                        answer_button = gr.Button("▶ Ejecutar Auditoría de Calidad", elem_classes=["primary-btn"], size="lg")
                        answer_metrics = gr.HTML(
                            "<div style='padding: 40px; text-align: center; color: #4b5563; border: 1px dashed #1f2937; border-radius: 12px; margin-top: 15px;'>Haz clic en <b>Ejecutar Auditoría de Calidad</b> para comenzar la evaluación del modelo.</div>"
                        )

                    with gr.Column(scale=2):
                        gr.Markdown("### Precisión Técnica por Dominio")
                        answer_chart = gr.BarPlot(
                            x="Categoría",
                            y="Precisión Promedio",
                            title="",
                            y_lim=[1, 5],
                            height=380,
                            color_accent="#38bdf8"
                        )

        # BINDINGS / EVENTOS
        retrieval_button.click(
            fn=run_retrieval_evaluation,
            outputs=[retrieval_metrics, retrieval_chart],
        )

        answer_button.click(
            fn=run_answer_evaluation,
            outputs=[answer_metrics, answer_chart],
        )

    app.launch(inbrowser=True)


if __name__ == "__main__":
    main()