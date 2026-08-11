import { useEffect, useMemo, useRef, useState } from "react";

import ForceGraph2D from "react-force-graph-2d";

import { useOrganization } from "@/context/OrganizationContext";
import {
  useKnowledgeBases,
  useKnowledgeMap,
} from "@/hooks/useCachedApi";

const NODE_COLORS: Record<string, string> = {
  document: "#2563eb",
  chunk: "#10b981",
  entity: "#f59e0b",
  word: "#f59e0b",
  concept: "#8b5cf6",
  relation: "#ef4444",
};

export default function KnowledgeGraphPage() {
  const { selectedOrg, setSelectedOrg, organizations } = useOrganization();

  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [preview, setPreview] = useState(false);
  const [selectedKbId, setSelectedKbId] = useState<string>("");
  const [similarityThreshold, setSimilarityThreshold] = useState(0.45);

  const { data: kbList } = useKnowledgeBases(
    selectedOrg?.id,
  );
  const knowledgeBases = useMemo(
    () => (kbList ?? []).map((kb) => ({ id: kb.id, name: kb.name })),
    [kbList],
  );

  const {
    data: graph,
    isLoading: loadingGraph,
    refetch: refetchGraph,
  } = useKnowledgeMap(selectedOrg?.id, selectedKbId || null, {
    preview,
    similarityThreshold,
  });

  const loadingOrganizations = false;

  const graphRef = useRef<any>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const [size, setSize] = useState({
    width: 0,
    height: 0,
  });

  const graphStatistics = useMemo(() => {
    if (!graph) {
      return {
        nodes: 0,
        edges: 0,
        documents: 0,
        chunks: 0,
        chunks_with_embedding: 0,
        average_similarity: 0,
      };
    }

    return {
      nodes: graph.statistics?.nodes ?? 0,
      edges: graph.statistics?.edges ?? 0,
      documents: graph.statistics?.documents ?? 0,
      chunks: graph.statistics?.chunks ?? 0,
      chunks_with_embedding: graph.statistics?.chunks_with_embedding ?? 0,
      average_similarity: graph.statistics?.average_similarity ?? 0,
    };
  }, [graph]);

  const getFileName = (path?: string) => {
    if (!path) return "";

    return path.split(/[\/\\]/).pop() ?? "";
  };

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver(([entry]) => {
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });

    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setSelectedKbId("");
  }, [selectedOrg?.id]);

  const loadGraph = () => {
    void refetchGraph();
  };

  const graphData = useMemo(() => {
    if (!graph || !graph.graph) {
      return {
        nodes: [],
        links: [],
      };
    }

    return {
      nodes: graph.graph.nodes.map((node) => ({
        ...node,

        color: NODE_COLORS[node.type] ?? "#64748b",

        val: node.weight ?? 10,
      })),

      links: graph.graph.edges.map((edge) => ({
        source: edge.source,

        target: edge.target,

        relation: edge.label ?? "relación",

        value: edge.weight ?? 1,
      })),
    };
  }, [graph]);
  console.log(size);
  /*
|--------------------------------------------------------------------------
| AJUSTAR ZOOM AL CARGAR
|--------------------------------------------------------------------------
*/

  useEffect(() => {
    if (!graphRef.current) return;

    if (graphData.nodes.length === 0) return;

    requestAnimationFrame(() => {
      graphRef.current.zoomToFit(400, 80);
    });
  }, [graphData]);

  /*
|--------------------------------------------------------------------------
| ESTADOS
|--------------------------------------------------------------------------
*/

  if (!selectedOrg) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="rounded-xl bg-white p-8 shadow">
          <h2 className="mb-4 text-xl font-bold">Seleccionar organización</h2>

          {loadingOrganizations ? (
            <p>Cargando...</p>
          ) : (
            <select
              className="rounded border px-4 py-2"
              onChange={(e) => {
                const org = organizations.find((o) => o.id === e.target.value);

                if (org) {
                  setSelectedOrg(org);
                }
              }}
            >
              <option>Selecciona</option>

              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
    );
  }

  if (loadingGraph) {
    return (
      <div className="flex h-full items-center justify-center">
        Generando Knowledge Graph...
      </div>
    );
  }

  if (!graph) {
    return (
      <div className="p-10">No existe información para esta organización.</div>
    );
  }

  return (
    <div
      className="
            flex
            h-full
            w-full
            flex-col
            overflow-hidden
            bg-slate-100
        "
    >
      <header
        className="
            flex
            shrink-0
            items-center
            justify-between
            border-b
            bg-white
            px-8
            py-5
        "
      >
        <div
          className="
                mt-2
                flex
                flex-wrap
                gap-4
                text-sm
            "
        >
          <span>Nodes: {graphStatistics.nodes}</span>

          <span>Edges: {graphStatistics.edges}</span>

          <span>Documents: {graphStatistics.documents}</span>

          <span>Chunks: {graphStatistics.chunks}</span>

          <span>
            Con embedding: {graphStatistics.chunks_with_embedding}
          </span>

          <span>
            Sim. media:{" "}
            {(graphStatistics.average_similarity * 100).toFixed(0)}%
          </span>
        </div>

        <select
          className="
                rounded
                border
                px-4
                py-2
            "
          value={selectedOrg.id}
          onChange={(e) => {
            const org = organizations.find((o) => o.id === e.target.value);

            if (org) {
              setSelectedOrg(org);
            }
          }}
        >
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>

        <div className="flex flex-wrap items-center gap-3">
          <select
            className="rounded border px-3 py-1 text-sm"
            value={selectedKbId}
            onChange={(e) => setSelectedKbId(e.target.value)}
          >
            <option value="">Todas las KBs</option>
            {knowledgeBases.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-sm">
            Umbral
            <input
              type="number"
              min={0.2}
              max={0.95}
              step={0.05}
              value={similarityThreshold}
              onChange={(e) =>
                setSimilarityThreshold(Number(e.target.value) || 0.45)
              }
              className="w-20 rounded border px-2 py-1"
            />
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={preview}
              onChange={(e) => setPreview(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm">Preview (word-level)</span>
          </label>

          <button
            className="rounded border px-3 py-1 text-sm"
            onClick={() => void loadGraph()}
          >
            Reload
          </button>
        </div>
      </header>

      <main
        className="
                flex
                flex-1
                min-h-0
                overflow-hidden
            "
      >
        <div
          ref={containerRef}
          className="
                    relative
                    flex-1
                    min-w-0
                    overflow-hidden
                "
        >
          {
            <ForceGraph2D
              ref={graphRef}
              width={1200}
              height={800}
              graphData={graphData}
              backgroundColor="#f8fafc"
              nodeLabel="label"
              nodeColor={(node: any) => node.color}
              nodeVal={(node: any) => node.val}
              linkWidth={(link: any) => Math.max(1, link.value)}
              linkDirectionalParticles={1}
              linkDirectionalParticleSpeed={() => 0.002}
              cooldownTicks={120}
              onNodeClick={(node: any) => setSelectedNode(node)}
            />
          }
        </div>

        {selectedNode && (
          <aside
            className="
                        w-96
                        shrink-0
                        overflow-y-auto
                        border-l
                        bg-white
                        p-6
                    "
          >
            <button
              className="
                            float-right
                            text-xl
                            text-gray-500
                            hover:text-black
                        "
              onClick={() => setSelectedNode(null)}
            >
              ✕
            </button>

            <h2
              className="
                            mb-6
                            text-xl
                            font-bold
                        "
            >
              {selectedNode.label}
            </h2>

            <div className="space-y-5">
              <div>
                <strong>Archivo</strong>

                <p className="break-all">
                  {getFileName(selectedNode.document)}
                </p>
              </div>

              <div>
                <strong>Tipo</strong>

                <p>{selectedNode.type}</p>
              </div>

              {selectedNode.content && (
                <div>
                  <strong>Contenido</strong>

                  <p
                    className="
                                        whitespace-pre-wrap
                                        break-words
                                        text-sm
                                    "
                  >
                    {selectedNode.content}
                  </p>
                </div>
              )}

              {selectedNode.words && (
                <div>
                  <strong>Palabras</strong>

                  <p>{selectedNode.words}</p>
                </div>
              )}

              {selectedNode.metadata && (
                <div>
                  <strong>Metadata</strong>

                  <pre
                    className="
                                        overflow-x-auto
                                        rounded
                                        bg-gray-100
                                        p-3
                                        text-xs
                                    "
                  >
                    {JSON.stringify(selectedNode.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </aside>
        )}
      </main>
    </div>
  );
}
