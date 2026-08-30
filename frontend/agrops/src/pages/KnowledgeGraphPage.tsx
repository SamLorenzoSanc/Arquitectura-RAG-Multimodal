import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useOrganization } from "@/context";
import { useKnowledgeBases, useKnowledgeMap } from "@/hooks";
import EmbeddingCloud3D from "@/components/EmbeddingCloud3D";
import { useTranslation } from "@/i18n/I18nProvider";

const BG = "#ffffff";
const CANARY_BLUE = "#0768A9";
const CANARY_YELLOW = "#FFCC00";
function hashHue(value: string): string {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = value.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue} 58% 44%)`;
}

type GraphNode = {
  id: string;
  label: string;
  type?: string;
  document?: string;
  content?: string;
  group?: string;
  has_embedding?: boolean;
  words?: number;
  weight?: number;
  color: string;
  val: number;
  x?: number;
  y?: number;
  z?: number;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  value: number;
};


function nodeId(ref: string | GraphNode): string {
  return typeof ref === "object" ? String(ref.id) : String(ref);
}

function fileName(path: string | undefined, t: (key: string) => string) {
  if (!path) return t("knowledgeGraph.noDocument");
  return path.split(/[\\/]/).pop() ?? path;
}

export default function KnowledgeGraphPage() {
  const { t } = useTranslation();
  const { selectedOrg } = useOrganization();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const [selectedKbId, setSelectedKbId] = useState("");
  const [similarityThreshold, setSimilarityThreshold] = useState(0.45);
  const [search, setSearch] = useState("");
  const [localGraph, setLocalGraph] = useState(false);
  const [showOrphans, setShowOrphans] = useState(true);
  const [showLabels, setShowLabels] = useState(false);
  const [viewMode, setViewMode] = useState<"2d" | "3d">("3d");
  const [charge, setCharge] = useState(-90);
  const [linkDistance, setLinkDistance] = useState(55);
  const [filtersOpen, setFiltersOpen] = useState(true);

  const { data: kbList } = useKnowledgeBases(selectedOrg?.id);
  const knowledgeBases = useMemo(
    () => (kbList ?? []).map((kb) => ({ id: kb.id, name: kb.name })),
    [kbList],
  );

  const {
    data: graph,
    isLoading: loadingGraph,
    error: graphError,
    refetch: refetchGraph,
  } = useKnowledgeMap(selectedOrg?.id, selectedKbId || null, {
    preview: false,
    similarityThreshold,
  });

  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
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
    const frame = requestAnimationFrame(measure);
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    window.addEventListener("resize", measure);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  useEffect(() => {
    setSelectedKbId("");
    setSelectedNode(null);
  }, [selectedOrg?.id]);

  const rawData = useMemo(() => {
    const nodes = (graph?.graph?.nodes ?? []).map((node) => {
      const group = node.group || node.document || "general";
      return {
        ...node,
        group,
        color: node.has_embedding === false ? "#94a3b8" : hashHue(group),
        val: Math.max(1.4, Math.min(6, (node.weight ?? 8) / 6)),
      } as GraphNode;
    });
    const links: GraphLink[] = (graph?.graph?.edges ?? []).map((edge) => ({
      source: edge.source,
      target: edge.target,
      value: edge.weight ?? 1,
    }));
    return { nodes, links };
  }, [graph]);

  const groups = useMemo(() => {
    const counts = new Map<string, { color: string; count: number }>();
    for (const node of rawData.nodes) {
      const key = fileName(node.group, t);
      const prev = counts.get(key) ?? { color: node.color, count: 0 };
      counts.set(key, { color: node.color, count: prev.count + 1 });
    }
    return [...counts.entries()].sort((a, b) => b[1].count - a[1].count);
  }, [rawData.nodes, t]);

  const graphData = useMemo(() => {
    const term = search.trim().toLowerCase();
    let nodes = rawData.nodes.filter((node) =>
      showOrphans ? true : node.has_embedding !== false,
    );
    if (term) {
      nodes = nodes.filter(
        (node) =>
          node.label?.toLowerCase().includes(term) ||
          node.document?.toLowerCase().includes(term) ||
          node.content?.toLowerCase().includes(term),
      );
    }
    if (localGraph && selectedNode) {
      const neighborIds = new Set<string>([selectedNode.id]);
      for (const link of rawData.links) {
        const source = nodeId(link.source);
        const target = nodeId(link.target);
        if (source === selectedNode.id) neighborIds.add(target);
        if (target === selectedNode.id) neighborIds.add(source);
      }
      nodes = nodes.filter((node) => neighborIds.has(node.id));
    }
    const ids = new Set(nodes.map((node) => node.id));
    const links = rawData.links.filter(
      (link) => ids.has(nodeId(link.source)) && ids.has(nodeId(link.target)),
    );
    return { nodes, links };
  }, [rawData, search, showOrphans, localGraph, selectedNode]);

  const focusId = hoverNode?.id ?? selectedNode?.id ?? null;
  const highlight = useMemo(() => {
    if (!focusId) return null;
    const ids = new Set<string>([focusId]);
    for (const link of graphData.links) {
      const source = nodeId(link.source);
      const target = nodeId(link.target);
      if (source === focusId) ids.add(target);
      if (target === focusId) ids.add(source);
    }
    return ids;
  }, [focusId, graphData.links]);

  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(charge);
    fg.d3Force("link")?.distance(linkDistance).strength(0.35);
    fg.d3Force("center")?.strength(0.04);
    fg.d3ReheatSimulation?.();
  }, [charge, linkDistance, graphData]);

  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;
    requestAnimationFrame(() => {
      graphRef.current.zoomToFit(500, 70);
    });
  }, [graphData.nodes.length, localGraph]);

  const stats = graph?.statistics;

  const paintNode = (
    node: GraphNode,
    ctx: CanvasRenderingContext2D,
    globalScale: number,
  ) => {
    const dimmed = Boolean(highlight && !highlight.has(node.id));
    const focused = node.id === focusId;
    const radius = (focused ? 5.4 : 3.2) * Math.sqrt(node.val || 1);
    ctx.save();
    ctx.globalAlpha = dimmed ? 0.12 : 1;
    ctx.beginPath();
    ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, Math.PI * 2);
    ctx.fillStyle = node.color;
    ctx.shadowColor = node.color;
    ctx.shadowBlur = dimmed ? 0 : focused ? 16 : 6;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = node.color === "#ffffff" ? CANARY_BLUE : "rgba(15, 23, 42, 0.2)";
    ctx.lineWidth = focused ? 1.8 : 0.8;
    ctx.stroke();
    const showText =
      showLabels ||
      focused ||
      globalScale > 2.4 ||
      Boolean(search.trim());
    if (showText && !dimmed) {
      const label = fileName(node.label || node.document, t);
      ctx.font = `${Math.max(9, 11 / globalScale)}px Inter, ui-sans-serif, system-ui`;
      ctx.fillStyle = "rgba(15,23,42,0.9)";
      ctx.fillText(label.slice(0, 42), (node.x ?? 0) + radius + 4, (node.y ?? 0) + 3);
    }
    ctx.restore();
  };

  if (!selectedOrg) {
    return (
      <div className="flex h-full items-center justify-center bg-white text-slate-500">
        {t("knowledgeGraph.noOrg")}
      </div>
    );
  }

  return (
    <div className="relative flex h-[calc(100vh-7.5rem)] min-h-[520px] w-full overflow-hidden rounded-xl border border-slate-200 bg-white text-slate-800">
      <div ref={containerRef} className="absolute inset-0">
        {loadingGraph && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/85 text-sm text-slate-500">
            {t("knowledgeGraph.loading")}
          </div>
        )}
        {graphError && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/90 p-6 text-center text-sm text-red-600">
            {t("knowledgeGraph.error")}
          </div>
        )}
        {!loadingGraph && !graphError && rawData.nodes.length === 0 && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white text-sm text-slate-500">
            {t("knowledgeGraph.empty")}
          </div>
        )}
        {size.width > 0 && size.height > 0 && viewMode === "2d" && (
          <ForceGraph2D
            key={`${selectedKbId || "all"}:${rawData.nodes.length}:${rawData.links.length}`}
            ref={graphRef}
            width={size.width}
            height={size.height}
            graphData={graphData}
            backgroundColor={BG}
            nodeRelSize={4}
            nodeVal={(node: GraphNode) => node.val}
            nodeColor={(node: GraphNode) => node.color}
            nodeLabel={(node: GraphNode) => fileName(node.label || node.document, t)}
            nodeCanvasObject={paintNode}
            nodePointerAreaPaint={(node: GraphNode, color, ctx) => {
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x ?? 0, node.y ?? 0, 8, 0, Math.PI * 2);
              ctx.fill();
            }}
            linkColor={(link: GraphLink) => {
              if (!highlight) return "rgba(7,104,169,0.18)";
              const source = nodeId(link.source);
              const target = nodeId(link.target);
              const active =
                highlight.has(source) &&
                highlight.has(target) &&
                (source === focusId || target === focusId);
              return active ? CANARY_BLUE : "rgba(7,104,169,0.05)";
            }}
            linkWidth={(link: GraphLink) => {
              if (!highlight) return 0.6;
              const source = nodeId(link.source);
              const target = nodeId(link.target);
              return source === focusId || target === focusId ? 1.4 : 0.4;
            }}
            cooldownTicks={140}
            onEngineStop={() => graphRef.current?.zoomToFit?.(500, 70)}
            enableNodeDrag
            onNodeHover={(node: GraphNode | null) => setHoverNode(node)}
            onNodeClick={(node: GraphNode) => setSelectedNode(node)}
            onBackgroundClick={() => {
              setSelectedNode(null);
              setHoverNode(null);
            }}
          />
        )}
        {viewMode === "3d" && graphData.nodes.length > 0 && (
          <div className="absolute inset-0">
            <EmbeddingCloud3D
              points={graphData.nodes}
              selectedId={selectedNode?.id ?? null}
              onSelect={(point) =>
                setSelectedNode(
                  point
                    ? (graphData.nodes.find((node) => node.id === point.id) ??
                        null)
                    : null,
                )
              }
            />
          </div>
        )}
      </div>

      <aside className="absolute left-4 top-4 z-20 w-72 rounded-xl border border-blue-100 bg-white/95 p-4 shadow-xl backdrop-blur">
        <div className="mb-3 flex h-1.5 overflow-hidden rounded-full">
          <span className="flex-1 bg-white ring-1 ring-inset ring-slate-200" />
          <span className="flex-1 bg-[#0768A9]" />
          <span className="flex-1 bg-[#FFCC00]" />
        </div>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#0768A9]">
              {t("knowledgeGraph.corpus")}
            </p>
            <h1 className="text-sm font-semibold text-slate-900">
              {t("knowledgeGraph.sidebarTitle")}
            </h1>
          </div>
          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            className="text-[11px] text-slate-500 hover:text-[#0768A9]"
          >
            {filtersOpen ? t("knowledgeGraph.hide") : t("knowledgeGraph.showFilters")}
          </button>
        </div>
        <p className="mb-3 text-[11px] text-slate-500">
          {t("knowledgeGraph.introFull", {
            fragments: stats?.nodes ?? 0,
            docs: stats?.documents ?? groups.length,
            withVector: stats?.chunks_with_embedding ?? 0,
          })}
        </p>
        <div className="mb-3 grid grid-cols-2 gap-1 rounded-md border border-slate-200 p-0.5 text-[11px] font-semibold">
          <button
            type="button"
            onClick={() => setViewMode("3d")}
            className={`rounded py-1 ${
              viewMode === "3d"
                ? "bg-[#0768A9] text-white"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {t("knowledgeGraph.view3d")}
          </button>
          <button
            type="button"
            onClick={() => setViewMode("2d")}
            className={`rounded py-1 ${
              viewMode === "2d"
                ? "bg-[#0768A9] text-white"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {t("knowledgeGraph.view2d")}
          </button>
        </div>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("knowledgeGraph.filterNotes")}
          className="mb-3 h-8 w-full rounded-md border border-slate-200 bg-white px-2.5 text-xs text-slate-800 outline-none placeholder:text-slate-400 focus:border-[#0768A9]"
        />
        {filtersOpen && (
          <div className="space-y-3 text-xs">
            <select
              className="h-8 w-full rounded-md border border-slate-200 bg-white px-2 text-slate-800"
              value={selectedKbId}
              onChange={(event) => setSelectedKbId(event.target.value)}
            >
              <option value="">{t("knowledgeGraph.allBases")}</option>
              {knowledgeBases.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
            <label className="flex items-center justify-between text-slate-600">
              {t("knowledgeGraph.localGraph")}
              <input
                type="checkbox"
                checked={localGraph}
                onChange={(event) => setLocalGraph(event.target.checked)}
              />
            </label>
            <label className="flex items-center justify-between text-slate-600">
              {t("knowledgeGraph.orphans")}
              <input
                type="checkbox"
                checked={showOrphans}
                onChange={(event) => setShowOrphans(event.target.checked)}
              />
            </label>
            <label className="flex items-center justify-between text-slate-600">
              {t("knowledgeGraph.alwaysLabels")}
              <input
                type="checkbox"
                checked={showLabels}
                onChange={(event) => setShowLabels(event.target.checked)}
              />
            </label>
            <label className="block text-slate-500">
              {t("knowledgeGraph.threshold", {
                value: similarityThreshold.toFixed(2),
              })}
              <input
                type="range"
                min={0.2}
                max={0.9}
                step={0.05}
                value={similarityThreshold}
                onChange={(event) =>
                  setSimilarityThreshold(Number(event.target.value))
                }
                className="mt-1 w-full accent-[#0768A9]"
              />
            </label>
            {viewMode === "2d" && (
              <>
            <label className="block text-slate-500">
              {t("knowledgeGraph.repulsion")}
              <input
                type="range"
                min={-180}
                max={-20}
                step={5}
                value={charge}
                onChange={(event) => setCharge(Number(event.target.value))}
                className="mt-1 w-full accent-[#FFCC00]"
              />
            </label>
            <label className="block text-slate-500">
              {t("knowledgeGraph.linkDistance")}
              <input
                type="range"
                min={20}
                max={140}
                step={5}
                value={linkDistance}
                onChange={(event) => setLinkDistance(Number(event.target.value))}
                className="mt-1 w-full accent-[#0768A9]"
              />
            </label>
              </>
            )}
            <button
              type="button"
              onClick={() => void refetchGraph()}
              className="h-8 w-full rounded-md border border-[#0768A9]/30 text-[#0768A9] hover:bg-blue-50"
            >
              {t("knowledgeGraph.reload")}
            </button>
            <div className="max-h-36 space-y-1 overflow-y-auto pt-1">
              {groups.slice(0, 12).map(([name, info]) => (
                <div key={name} className="flex items-center gap-2 text-[11px] text-slate-600">
                  <span
                    className="h-2 w-2 rounded-full border border-slate-300"
                    style={{
                      background: info.color,
                      boxShadow: `0 0 6px ${info.color}`,
                    }}
                  />
                  <span className="truncate">{name}</span>
                  <span className="ml-auto text-slate-400">{info.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>

      {selectedNode && (
        <aside className="absolute bottom-4 right-4 z-20 w-80 max-h-[70%] overflow-y-auto rounded-xl border border-yellow-200 bg-white/95 p-4 shadow-xl backdrop-blur">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-[0.18em] text-[#0768A9]">
                {t("knowledgeGraph.note")}
              </p>
              <h2 className="text-sm font-semibold text-slate-900">
                {fileName(selectedNode.label || selectedNode.document, t)}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-[#0768A9]"
            >
              ✕
            </button>
          </div>
          <p className="mb-2 text-[11px] text-slate-500">
            {fileName(selectedNode.document, t)} ·{" "}
            {selectedNode.has_embedding === false
              ? t("knowledgeGraph.withoutVector")
              : t("knowledgeGraph.withVector")}
            {selectedNode.words
              ? t("knowledgeGraph.words", { count: selectedNode.words })
              : ""}
          </p>
          {selectedNode.content && (
            <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-700">
              {selectedNode.content}
            </p>
          )}
        </aside>
      )}
    </div>
  );
}
