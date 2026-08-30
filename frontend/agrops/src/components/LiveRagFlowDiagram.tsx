"use client";

import { useMemo } from "react";

import { useTranslation } from "@/i18n/I18nProvider";
import type { RagFlowNodeId, RagFlowNodeState } from "@/types";

export type RagFlowMode = "agentic" | "hybrid" | "none";

type Props = {
  mode: RagFlowMode;
  nodes: Partial<Record<RagFlowNodeId, RagFlowNodeState>>;
  caption?: string;
};

type DiagramNode = {
  id: RagFlowNodeId;
  label: string;
  x: number;
  y: number;
  w?: number;
};

type DiagramEdge = {
  from: RagFlowNodeId;
  to: RagFlowNodeId;
};

const STATE_FILL: Record<RagFlowNodeState, string> = {
  idle: "#f8fafc",
  active: "#0768A9",
  done: "#059669",
  error: "#dc2626",
  skipped: "#e2e8f0",
};

const STATE_STROKE: Record<RagFlowNodeState, string> = {
  idle: "#cbd5e1",
  active: "#0768A9",
  done: "#047857",
  error: "#b91c1c",
  skipped: "#94a3b8",
};

const STATE_TEXT: Record<RagFlowNodeState, string> = {
  idle: "#64748b",
  active: "#ffffff",
  done: "#ffffff",
  error: "#ffffff",
  skipped: "#94a3b8",
};

function nodeState(
  nodes: Partial<Record<RagFlowNodeId, RagFlowNodeState>>,
  id: RagFlowNodeId,
): RagFlowNodeState {
  return nodes[id] ?? "idle";
}

function edgeActive(
  nodes: Partial<Record<RagFlowNodeId, RagFlowNodeState>>,
  from: RagFlowNodeId,
  to: RagFlowNodeId,
): boolean {
  const a = nodeState(nodes, from);
  const b = nodeState(nodes, to);
  return (
    (a === "done" || a === "active") &&
    (b === "active" || b === "done" || b === "error")
  );
}

export default function LiveRagFlowDiagram({ mode, nodes, caption }: Props) {
  const { t } = useTranslation();

  const { diagramNodes, edges, viewBox } = useMemo(() => {
    if (mode === "none") {
      const list: DiagramNode[] = [
        { id: "pregunta", label: t("chat.flowNodeQuestion"), x: 40, y: 48 },
        { id: "generate", label: t("chat.flowNodeLlm"), x: 220, y: 48 },
        { id: "respuesta", label: t("chat.flowNodeAnswer"), x: 400, y: 48 },
      ];
      return {
        diagramNodes: list,
        edges: [
          { from: "pregunta", to: "generate" },
          { from: "generate", to: "respuesta" },
        ] as DiagramEdge[],
        viewBox: "0 0 560 120",
      };
    }

    if (mode === "hybrid") {
      const list: DiagramNode[] = [
        { id: "pregunta", label: t("chat.flowNodeQuestion"), x: 16, y: 70 },
        { id: "dense", label: t("chat.flowNodeDense"), x: 140, y: 28 },
        { id: "bm25", label: t("chat.flowNodeBm25"), x: 140, y: 112 },
        { id: "rrf", label: t("chat.flowNodeRrf"), x: 280, y: 70 },
        { id: "generate", label: t("chat.flowNodeLlm"), x: 410, y: 70 },
        { id: "respuesta", label: t("chat.flowNodeAnswer"), x: 540, y: 70 },
      ];
      return {
        diagramNodes: list,
        edges: [
          { from: "pregunta", to: "dense" },
          { from: "pregunta", to: "bm25" },
          { from: "dense", to: "rrf" },
          { from: "bm25", to: "rrf" },
          { from: "rrf", to: "generate" },
          { from: "generate", to: "respuesta" },
        ] as DiagramEdge[],
        viewBox: "0 0 680 180",
      };
    }

    // agentic
    const list: DiagramNode[] = [
      { id: "pregunta", label: t("chat.flowNodeQuestion"), x: 12, y: 78 },
      { id: "agente", label: t("chat.flowNodeAgent"), x: 130, y: 78 },
      { id: "sql", label: t("chat.flowNodeSql"), x: 250, y: 18, w: 100 },
      { id: "retrieve", label: t("chat.flowNodeRetrieve"), x: 250, y: 78 },
      { id: "memoria", label: t("chat.flowNodeMemory"), x: 250, y: 138, w: 100 },
      { id: "grade", label: t("chat.flowNodeGrade"), x: 390, y: 78 },
      { id: "rewrite", label: t("chat.flowNodeRewrite"), x: 390, y: 18, w: 100 },
      { id: "generate", label: t("chat.flowNodeLlm"), x: 520, y: 78 },
      { id: "respuesta", label: t("chat.flowNodeAnswer"), x: 640, y: 78 },
    ];
    return {
      diagramNodes: list,
      edges: [
        { from: "pregunta", to: "agente" },
        { from: "agente", to: "sql" },
        { from: "agente", to: "retrieve" },
        { from: "agente", to: "memoria" },
        { from: "sql", to: "grade" },
        { from: "retrieve", to: "grade" },
        { from: "memoria", to: "grade" },
        { from: "grade", to: "rewrite" },
        { from: "rewrite", to: "agente" },
        { from: "grade", to: "generate" },
        { from: "agente", to: "generate" },
        { from: "generate", to: "respuesta" },
      ] as DiagramEdge[],
      viewBox: "0 0 780 190",
    };
  }, [mode, t]);

  const byId = useMemo(() => {
    const map = new Map<RagFlowNodeId, DiagramNode>();
    for (const n of diagramNodes) map.set(n.id, n);
    return map;
  }, [diagramNodes]);

  const activeId = diagramNodes.find(
    (n) => nodeState(nodes, n.id) === "active",
  )?.id;

  return (
    <div className="rounded-lg border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[10px] font-bold uppercase tracking-wide text-[color:var(--agro-primary)]">
          {t("chat.flowDiagramTitle")}
        </p>
        {caption ? (
          <p className="truncate text-[11px] text-slate-500">{caption}</p>
        ) : null}
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={viewBox}
          className="h-[160px] w-full min-w-[520px]"
          role="img"
          aria-label={t("chat.flowDiagramTitle")}
        >
          <defs>
            <marker
              id="rag-arrow"
              markerWidth="7"
              markerHeight="7"
              refX="6"
              refY="3.5"
              orient="auto"
            >
              <path d="M0,0 L7,3.5 L0,7 Z" fill="#94a3b8" />
            </marker>
            <marker
              id="rag-arrow-active"
              markerWidth="7"
              markerHeight="7"
              refX="6"
              refY="3.5"
              orient="auto"
            >
              <path d="M0,0 L7,3.5 L0,7 Z" fill="#0768A9" />
            </marker>
          </defs>

          {edges.map((edge) => {
            const from = byId.get(edge.from);
            const to = byId.get(edge.to);
            if (!from || !to) return null;
            const fw = from.w ?? 108;
            const tw = to.w ?? 108;
            const x1 = from.x + fw;
            const y1 = from.y + 18;
            const x2 = to.x;
            const y2 = to.y + 18;
            const active = edgeActive(nodes, edge.from, edge.to);
            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;
            const showPacket =
              active &&
              (nodeState(nodes, edge.to) === "active" ||
                nodeState(nodes, edge.from) === "active");

            return (
              <g key={`${edge.from}-${edge.to}`}>
                <path
                  d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                  fill="none"
                  stroke={active ? "#0768A9" : "#cbd5e1"}
                  strokeWidth={active ? 2.2 : 1.4}
                  strokeDasharray={
                    edge.from === "grade" && edge.to === "rewrite"
                      ? "4 3"
                      : undefined
                  }
                  markerEnd={
                    active ? "url(#rag-arrow-active)" : "url(#rag-arrow)"
                  }
                  className={active ? "transition-all duration-300" : undefined}
                />
                {showPacket ? (
                  <circle r="4.5" fill="#FFD100" stroke="#0768A9" strokeWidth="1">
                    <animateMotion
                      dur="1.1s"
                      repeatCount="indefinite"
                      path={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                    />
                  </circle>
                ) : null}
              </g>
            );
          })}

          {diagramNodes.map((n) => {
            const state = nodeState(nodes, n.id);
            const w = n.w ?? 108;
            const h = 36;
            const isActive = state === "active";
            return (
              <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
                {isActive ? (
                  <rect
                    x={-3}
                    y={-3}
                    width={w + 6}
                    height={h + 6}
                    rx={10}
                    fill="none"
                    stroke="#FFD100"
                    strokeWidth={2}
                    opacity={0.9}
                  >
                    <animate
                      attributeName="opacity"
                      values="0.35;0.95;0.35"
                      dur="1.2s"
                      repeatCount="indefinite"
                    />
                  </rect>
                ) : null}
                <rect
                  width={w}
                  height={h}
                  rx={8}
                  fill={STATE_FILL[state]}
                  stroke={STATE_STROKE[state]}
                  strokeWidth={isActive || state === "done" ? 1.8 : 1.2}
                />
                <text
                  x={w / 2}
                  y={h / 2 + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={STATE_TEXT[state]}
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    fontFamily: "system-ui, sans-serif",
                  }}
                >
                  {n.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-1 flex flex-wrap gap-3 text-[10px] text-slate-500">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-slate-300" />
          {t("chat.flowLegendIdle")}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-[color:var(--agro-primary)]" />
          {t("chat.flowLegendActive")}
          {activeId ? ` · ${activeId}` : ""}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-600" />
          {t("chat.flowLegendDone")}
        </span>
      </div>
    </div>
  );
}

/** Marca un nodo activo y deja done los anteriores de una secuencia típica. */
export function advanceFlowNodes(
  prev: Partial<Record<RagFlowNodeId, RagFlowNodeState>>,
  active: RagFlowNodeId | RagFlowNodeId[],
  done: RagFlowNodeId[] = [],
): Partial<Record<RagFlowNodeId, RagFlowNodeState>> {
  const next = { ...prev };
  for (const id of done) {
    if (next[id] !== "error") next[id] = "done";
  }
  for (const [id, state] of Object.entries(next) as [
    RagFlowNodeId,
    RagFlowNodeState,
  ][]) {
    if (state === "active") next[id] = "done";
  }
  const actives = Array.isArray(active) ? active : [active];
  for (const id of actives) next[id] = "active";
  return next;
}

export function markFlowDone(
  prev: Partial<Record<RagFlowNodeId, RagFlowNodeState>>,
  ids: RagFlowNodeId[],
): Partial<Record<RagFlowNodeId, RagFlowNodeState>> {
  const next = { ...prev };
  for (const id of ids) {
    if (next[id] !== "error") next[id] = "done";
  }
  return next;
}

export function toolToFlowNodes(tool?: string): RagFlowNodeId[] {
  switch (tool) {
    case "query_operational_sql":
      return ["sql"];
    case "recall_conversation":
      return ["memoria"];
    case "search_knowledge_base":
    case "search_regulations":
    case "diagnose_crop":
    case "list_indexed_documents":
      return ["retrieve", "dense", "bm25", "rrf"];
    default:
      return ["retrieve"];
  }
}
