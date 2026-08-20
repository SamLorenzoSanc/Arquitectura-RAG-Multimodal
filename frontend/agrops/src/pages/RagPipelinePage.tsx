import { useEffect, useMemo, useRef, useState } from "react";

import ForceGraph2D from "react-force-graph-2d";



import { useRagRuntimeConfig } from "@/components/evaluation/FrozenRagConfigBar";

import { useTranslation } from "@/i18n/I18nProvider";



type PipelineNode = {

  id: string;

  label: string;

  role: string;

  detail: string;

  color: string;

  dimmed?: boolean;

  x?: number;

  y?: number;

};



type PipelineLink = {

  source: string;

  target: string;

};



const BG = "#ffffff";



function roundedRect(

  ctx: CanvasRenderingContext2D,

  x: number,

  y: number,

  w: number,

  h: number,

  r: number,

) {

  const radius = Math.min(r, w / 2, h / 2);

  ctx.beginPath();

  ctx.moveTo(x + radius, y);

  ctx.arcTo(x + w, y, x + w, y + h, radius);

  ctx.arcTo(x + w, y + h, x, y + h, radius);

  ctx.arcTo(x, y + h, x, y, radius);

  ctx.arcTo(x, y, x + w, y, radius);

  ctx.closePath();

}



export default function RagPipelinePage() {

  const { t } = useTranslation();

  const { data: config } = useRagRuntimeConfig();

  const graphRef = useRef<any>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const [size, setSize] = useState({ width: 0, height: 0 });

  const [selectedId, setSelectedId] = useState("pregunta");



  useEffect(() => {

    const container = containerRef.current;

    if (!container) return;

    const measure = () => {

      const rect = container.getBoundingClientRect();

      setSize({

        width: Math.max(1, Math.floor(rect.width)),

        height: Math.max(1, Math.floor(rect.height)),

      });

    };

    measure();

    const observer = new ResizeObserver(measure);

    observer.observe(container);

    return () => observer.disconnect();

  }, []);



  const retrievalK = config?.retrieval_k ?? 12;

  const bm25K = config?.bm25_k ?? 12;

  const rrfK = config?.rrf_k ?? 60;

  const finalK = config?.final_k ?? 8;

  const evalK = config?.eval_top_k ?? 3;

  const embed = config?.embedding_model ?? "nomic-embed-text";

  const llm = config?.generation_model ?? "llama3.2:latest";

  const rewriteOn = config?.use_query_rewrite !== false;

  const rerankOn = Boolean(config?.use_reranker);



  const graphData = useMemo(() => {

    const nodes: PipelineNode[] = [

      {

        id: "pregunta",

        label: t("ragPipeline.nodePregunta"),

        role: t("ragPipeline.roleEntrada"),

        color: "#0768A9",

        detail: t("ragPipeline.detailPregunta"),

      },

      {

        id: "agente",

        label: t("ragPipeline.nodeAgente"),

        role: t("ragPipeline.rolePlanificador"),

        color: "#4f46e5",

        detail: t("ragPipeline.detailAgente"),

      },

      {

        id: "sql",

        label: t("ragPipeline.nodeSql"),

        role: t("ragPipeline.rolePostgres"),

        color: "#0f766e",

        detail: t("ragPipeline.detailSql"),

      },

      {

        id: "memoria",

        label: t("ragPipeline.nodeMemoria"),

        role: t("ragPipeline.roleChats"),

        color: "#9d174d",

        detail: t("ragPipeline.detailMemoria"),

      },

      {

        id: "rewrite",

        label: t("ragPipeline.nodeRewrite"),

        role: rewriteOn ? t("ragPipeline.roleRewriteOn") : t("ragPipeline.roleRewriteOff"),

        color: rewriteOn ? "#0f766e" : "#94a3b8",

        dimmed: !rewriteOn,

        detail: rewriteOn ? t("ragPipeline.detailRewriteOn") : t("ragPipeline.detailRewriteOff"),

      },

      {

        id: "grade",

        label: t("ragPipeline.nodeGrader"),

        role: t("ragPipeline.roleRelevante"),

        color: "#4338ca",

        detail: t("ragPipeline.detailGrader"),

      },

      {

        id: "dense",

        label: t("ragPipeline.nodeDenso"),

        role: t("ragPipeline.rolePgvector", { k: retrievalK }),

        color: "#2563eb",

        detail: t("ragPipeline.detailDenso", { model: embed, k: retrievalK }),

      },

      {

        id: "bm25",

        label: t("ragPipeline.nodeBm25"),

        role: t("ragPipeline.roleLexico", { k: bm25K }),

        color: "#d97706",

        detail: t("ragPipeline.detailBm25", { k: bm25K }),

      },

      {

        id: "rrf",

        label: t("ragPipeline.nodeRrf"),

        role: t("ragPipeline.roleFusion", { k: rrfK }),

        color: "#7c3aed",

        detail: t("ragPipeline.detailRrf", { k: rrfK }),

      },

      {

        id: "rerank",

        label: t("ragPipeline.nodeRerank"),

        role: rerankOn ? t("ragPipeline.roleRerankOn") : t("ragPipeline.roleRerankOff"),

        color: rerankOn ? "#be185d" : "#cbd5e1",

        dimmed: !rerankOn,

        detail: rerankOn ? t("ragPipeline.detailRerankOn") : t("ragPipeline.detailRerankOff"),

      },

      {

        id: "topk",

        label: t("ragPipeline.nodeTopk"),

        role: t("ragPipeline.roleTopk", { finalK, evalK }),

        color: "#0f766e",

        detail: t("ragPipeline.detailTopk", { finalK, evalK }),

      },

      {

        id: "llm",

        label: t("ragPipeline.nodeLlm"),

        role: llm,

        color: "#b45309",

        detail: t("ragPipeline.detailLlm", { model: llm }),

      },

      {

        id: "respuesta",

        label: t("ragPipeline.nodeRespuesta"),

        role: t("ragPipeline.roleSalida"),

        color: "#ca8a04",

        detail: t("ragPipeline.detailRespuesta"),

      },

    ];

    const links: PipelineLink[] = [

      { source: "pregunta", target: "agente" },

      { source: "agente", target: "rewrite" },

      { source: "agente", target: "dense" },

      { source: "agente", target: "bm25" },

      { source: "agente", target: "sql" },

      { source: "agente", target: "memoria" },

      { source: "agente", target: "llm" },

      { source: "rewrite", target: "dense" },

      { source: "rewrite", target: "bm25" },

      { source: "dense", target: "rrf" },

      { source: "bm25", target: "rrf" },

      { source: "rrf", target: "rerank" },

      { source: "rerank", target: "topk" },

      { source: "topk", target: "grade" },

      { source: "grade", target: "llm" },

      { source: "grade", target: "rewrite" },

      { source: "sql", target: "llm" },

      { source: "memoria", target: "llm" },

      { source: "llm", target: "respuesta" },

    ];

    return { nodes, links };

  }, [

    bm25K,

    embed,

    evalK,

    finalK,

    llm,

    rerankOn,

    retrievalK,

    rewriteOn,

    rrfK,

    t,

  ]);



  const selected =

    graphData.nodes.find((node) => node.id === selectedId) ?? graphData.nodes[0];



  return (

    <div className="flex min-h-0 flex-1 flex-col gap-4 pb-6">

      <div>

        <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--agro-primary)]">

          {t("ragPipeline.eyebrow")}

        </p>

        <h1 className="mt-1 text-2xl font-extrabold text-slate-900">

          {t("ragPipeline.title")}

        </h1>

        <p className="mt-1 max-w-3xl text-sm text-slate-600">

          {t("ragPipeline.intro")}

        </p>

      </div>



      <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">

        <section className="relative min-h-[520px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          <div ref={containerRef} className="absolute inset-0">

            {size.width > 0 && (

              <ForceGraph2D

                ref={graphRef}

                width={size.width}

                height={size.height}

                graphData={graphData}

                backgroundColor={BG}

                cooldownTicks={80}

                d3VelocityDecay={0.35}

                enableNodeDrag={false}

                linkColor={() => "rgba(7,104,169,0.28)"}

                linkWidth={1.6}

                linkDirectionalArrowLength={6}

                linkDirectionalArrowRelPos={1}

                linkDirectionalParticles={2}

                linkDirectionalParticleWidth={2.4}

                linkDirectionalParticleSpeed={0.006}

                linkDirectionalParticleColor={() => "#0768A9"}

                onEngineStop={() => graphRef.current?.zoomToFit?.(400, 56)}

                nodeLabel={(node: PipelineNode) => `${node.label} · ${node.role}`}

                nodeCanvasObject={(node: PipelineNode, ctx) => {

                  const label = node.label;

                  ctx.font = "700 13px Inter, system-ui, sans-serif";

                  const width = Math.max(118, ctx.measureText(label).width + 28);

                  const height = 40;

                  const x = (node.x ?? 0) - width / 2;

                  const y = (node.y ?? 0) - height / 2;

                  const active = node.id === selectedId;

                  roundedRect(ctx, x, y, width, height, 12);

                  ctx.fillStyle = node.dimmed ? "#f8fafc" : "#ffffff";

                  ctx.fill();

                  ctx.lineWidth = active ? 3 : 1.5;

                  ctx.strokeStyle = active ? node.color : `${node.color}99`;

                  ctx.stroke();

                  ctx.beginPath();

                  ctx.arc(x + 12, node.y ?? 0, 5, 0, Math.PI * 2);

                  ctx.fillStyle = node.color;

                  ctx.fill();

                  ctx.fillStyle = node.dimmed ? "#64748b" : "#0f172a";

                  ctx.textAlign = "center";

                  ctx.textBaseline = "middle";

                  ctx.fillText(label, (node.x ?? 0) + 6, node.y ?? 0);

                }}

                nodePointerAreaPaint={(node: PipelineNode, color, ctx) => {

                  ctx.fillStyle = color;

                  roundedRect(

                    ctx,

                    (node.x ?? 0) - 64,

                    (node.y ?? 0) - 22,

                    128,

                    44,

                    12,

                  );

                  ctx.fill();

                }}

                onNodeClick={(node: PipelineNode) => setSelectedId(node.id)}

                onBackgroundClick={() => setSelectedId("pregunta")}

              />

            )}

          </div>

        </section>



        <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">

            {selected.role}

          </p>

          <h2 className="mt-1 text-lg font-extrabold text-slate-900">

            {selected.label}

          </h2>

          <p className="mt-3 text-sm leading-6 text-slate-600">{selected.detail}</p>

          <ol className="mt-5 space-y-1.5 border-t border-slate-100 pt-4">

            {graphData.nodes.map((node, index) => (

              <li key={node.id}>

                <button

                  type="button"

                  onClick={() => setSelectedId(node.id)}

                  className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs ${

                    node.id === selectedId

                      ? "bg-[color:var(--agro-pill)] font-semibold text-[color:var(--agro-primary)]"

                      : "text-slate-600 hover:bg-slate-50"

                  }`}

                >

                  <span

                    className="h-2 w-2 shrink-0 rounded-full"

                    style={{ background: node.color }}

                  />

                  {index + 1}. {node.label}

                </button>

              </li>

            ))}

          </ol>

        </aside>

      </div>

    </div>

  );

}

