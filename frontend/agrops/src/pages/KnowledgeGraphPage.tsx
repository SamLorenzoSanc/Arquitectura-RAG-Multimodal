import { useCallback, useEffect, useState } from "react";

import { useOrganization } from "@/context/OrganizationContext";
import KnowledgeService from "@/services/knowledge.service";
import type { KnowledgeMap } from "@/types/knowledge";

import ForceGraph2D from "react-force-graph-2d";

const COLORS = [
    "#10b981",
    "#3b82f6",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#14b8a6",
    "#ec4899",
    "#6366f1",
];

export default function KnowledgeGraphPage() {

    const { selectedOrg } = useOrganization();

    const [graph, setGraph] = useState<KnowledgeMap | null>(null);
    const [loading, setLoading] = useState(false);

    const load = useCallback(async () => {

        if (!selectedOrg) return;

        setLoading(true);

        try {

            const data = await KnowledgeService.getMap(
                selectedOrg.id
            );

            setGraph(data);

        } catch (err) {

            console.error(err);

        } finally {

            setLoading(false);

        }

    }, [selectedOrg]);

    useEffect(() => {

        void load();

    }, [load]);

    if (!selectedOrg) {
        return (
            <div className="flex h-full items-center justify-center text-lg">
                Selecciona una organización.
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex h-full items-center justify-center">
                Cargando Knowledge Graph...
            </div>
        );
    }

    if (!graph) return null;

    // Agrupar documentos por color
    const groups = Array.from(
        new Set(graph.nodes.map((n) => n.group))
    );

    const colorMap: Record<string, string> = {};

    groups.forEach((g, i) => {
        colorMap[g] = COLORS[i % COLORS.length];
    });

    const graphData = {

        nodes: graph.nodes.map((node) => ({
            ...node,
            color: colorMap[node.group],
            val: 8,
        })),

        links: graph.edges.map((edge) => ({
            source: edge.source,
            target: edge.target,
            value: edge.weight,
        })),
    };

    return (

        <div className="flex h-full flex-col bg-slate-50">

            <div className="border-b bg-white px-8 py-6 shadow-sm">

                <h1 className="text-3xl font-bold">
                    Knowledge Graph
                </h1>

                <p className="mt-1 text-gray-500">
                    {selectedOrg.name}
                </p>

            </div>

            <div className="flex flex-1">

                <div className="w-72 border-r bg-white p-5">

                    <h2 className="mb-4 text-lg font-semibold">
                        Leyenda
                    </h2>

                    <div className="space-y-3">

                        {groups.map(group => (

                            <div
                                key={group}
                                className="flex items-center gap-3"
                            >

                                <div
                                    className="h-4 w-4 rounded-full"
                                    style={{
                                        background: colorMap[group]
                                    }}
                                />

                                <span className="truncate text-sm">
                                    {group}
                                </span>

                            </div>

                        ))}

                    </div>

                    <div className="mt-8 rounded-xl bg-slate-50 p-4 text-sm">

                        <p className="font-semibold">
                            Estadísticas
                        </p>

                        <p className="mt-2">
                            📄 Documentos:
                            {" "}
                            {groups.length}
                        </p>

                        <p>
                            🧩 Chunks:
                            {" "}
                            {graph.nodes.length}
                        </p>

                        <p>
                            🔗 Relaciones:
                            {" "}
                            {graph.edges.length}
                        </p>

                    </div>

                </div>

                <div className="flex-1">

                    <ForceGraph2D

                        graphData={graphData}

                        nodeLabel={(node: any) => `
${node.label}
${node.document}
                        `}

                        nodeColor={(node: any) => node.color}

                        nodeVal={(node: any) => node.val}

                        linkWidth={(link: any) =>
                            Math.max(1, link.value * 5)
                        }

                        linkColor={() => "#CBD5E1"}

                        backgroundColor="#ffffff"

                        cooldownTicks={200}

                        enableNodeDrag

                        nodeCanvasObject={(
                            node: any,
                            ctx,
                            globalScale
                        ) => {

                            const label = node.label;

                            const fontSize =
                                14 / globalScale;

                            ctx.font =
                                `${fontSize}px Sans-Serif`;

                            ctx.beginPath();

                            ctx.arc(
                                node.x,
                                node.y,
                                6,
                                0,
                                2 * Math.PI
                            );

                            ctx.fillStyle =
                                node.color;

                            ctx.fill();

                            if (globalScale > 1.5) {

                                ctx.fillStyle = "#111";

                                ctx.fillText(
                                    label,
                                    node.x + 10,
                                    node.y + 4
                                );

                            }

                        }}

                    />

                </div>

            </div>

        </div>

    );

}