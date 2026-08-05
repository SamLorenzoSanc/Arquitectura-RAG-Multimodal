import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

import ForceGraph2D from "react-force-graph-2d";

import type { Organization } from "@/types/organization";
import { useOrganization } from "@/context/OrganizationContext";
import OrganizationService from "@/services/organization.service";

import KnowledgeService from "@/services/knowledge.service";
import type { KnowledgeMap } from "@/types/knowledge";

const NODE_COLORS: Record<string, string> = {
    document: "#2563eb",
    chunk: "#10b981",
    entity: "#f59e0b",
    concept: "#8b5cf6",
    relation: "#ef4444",
};

export default function KnowledgeGraphPage() {
    const { selectedOrg, setSelectedOrg } = useOrganization();

    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [selectedNode, setSelectedNode] = useState<any | null>(null);
    const [graph, setGraph] = useState<KnowledgeMap | null>(null);

    const [loadingOrganizations, setLoadingOrganizations] = useState(false);
    const [loadingGraph, setLoadingGraph] = useState(false);

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
                documents: 20,
                chunks: 0,
            };
        }

        return graph.statistics;
    }, [graph]);

    const getFileName = (path?: string) => {
        if (!path) return "";

        return path.split(/[\/\\]/).pop() ?? "";
    };

    /*
    |--------------------------------------------------------------------------
    | ORGANIZACIONES
    |--------------------------------------------------------------------------
    */
    
    useEffect(() => {

        const load = async () => {

            try {

                setLoadingOrganizations(true);

                const data =
                    await OrganizationService.getAll();

                setOrganizations(data);

                if (!selectedOrg && data.length) {
                    setSelectedOrg(data[0]);
                }

            } catch (error) {

                console.error(error);

            } finally {

                setLoadingOrganizations(false);

            }

        };

        void load();

    }, [selectedOrg, setSelectedOrg]);
     useEffect(() => {

        if (!containerRef.current) return;

        const observer =
            new ResizeObserver(([entry]) => {

                setSize({
                    width: entry.contentRect.width,
                    height: entry.contentRect.height,
                });

            });

        observer.observe(containerRef.current);

        return () => observer.disconnect();

    }, []);

    const loadGraph = useCallback(async () => {

    if (!selectedOrg) {
        setGraph(null);
        return;
    }

    try {

        setLoadingGraph(true);

        const response =
            await KnowledgeService.getMap(
                selectedOrg.id
            );

        console.log(
            "KNOWLEDGE GRAPH",
            response
        );

        setGraph(response);

    }
    catch (error) {

        console.error(
            "Knowledge graph error",
            error
        );

        setGraph(null);

    }
    finally {

        setLoadingGraph(false);

    }

}, [selectedOrg]);

useEffect(() => {

    void loadGraph();

}, [loadGraph]);

/*
|--------------------------------------------------------------------------
| RESIZE DEL CONTENEDOR
|--------------------------------------------------------------------------
*/

useEffect(() => {

    if (!containerRef.current)
        return;

    const observer =
        new ResizeObserver(([entry]) => {

            setSize({

                width:
                    entry.contentRect.width,

                height:
                    entry.contentRect.height,

            });

        });

    observer.observe(
        containerRef.current
    );

    
    if (!containerRef.current) return;

    console.log(
        containerRef.current.clientWidth,
        containerRef.current.clientHeight
    );
    return () =>
        observer.disconnect();

}, []);

const graphData = useMemo(() => {

    if (!graph || !graph.graph) {

        return {

            nodes: [],
            links: [],

        };

    }

    return {

        nodes:
            graph.graph.nodes.map(node => ({

                ...node,

                color:
                    NODE_COLORS[node.type] ??
                    "#64748b",

                val:
                    node.weight ??
                    10,

            })),

        links:
            graph.graph.edges.map(edge => ({

                source:
                    edge.source,

                target:
                    edge.target,

                relation:
                    edge.label ??
                    "relación",

                value:
                    edge.weight ??
                    1,

            }))

    };

}, [graph]);
console.log(size);
/*
|--------------------------------------------------------------------------
| AJUSTAR ZOOM AL CARGAR
|--------------------------------------------------------------------------
*/

useEffect(() => {

    if (!graphRef.current)
        return;

    if (graphData.nodes.length === 0)
        return;

    requestAnimationFrame(() => {

        graphRef.current.zoomToFit(
            400,
            80
        );

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

                <h2 className="mb-4 text-xl font-bold">
                    Seleccionar organización
                </h2>

                {
                    loadingOrganizations

                        ? <p>Cargando...</p>

                        : (

                            <select
                                className="rounded border px-4 py-2"
                                onChange={(e) => {

                                    const org =
                                        organizations.find(
                                            o => o.id === e.target.value
                                        );

                                    if (org) {
                                        setSelectedOrg(org);
                                    }

                                }}
                            >

                                <option>
                                    Selecciona
                                </option>

                                {
                                    organizations.map(org => (

                                        <option
                                            key={org.id}
                                            value={org.id}
                                        >
                                            {org.name}
                                        </option>

                                    ))
                                }

                            </select>

                        )

                }

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

        <div className="p-10">

            No existe información para esta organización.

        </div>

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
        
            <span>
                Nodes: {graphStatistics.nodes}
            </span>

            <span>
                Edges: {graphStatistics.edges}
            </span>

            <span>
                Documents: {20}
            </span>

            <span>
                Chunks: {graphStatistics.chunks}
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

                const org =
                    organizations.find(
                        o => o.id === e.target.value
                    );

                if (org) {
                    setSelectedOrg(org);
                }

            }}

        >

            {
                organizations.map(org => (

                    <option
                        key={org.id}
                        value={org.id}
                    >
                        {org.name}
                    </option>

                ))
            }

        </select>

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
                        onNodeClick={(node: any) =>
                            setSelectedNode(node)
                        }
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
                                    {JSON.stringify(
                                        selectedNode.metadata,
                                        null,
                                        2
                                    )}
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