"use client";

import {
    ResponsiveContainer,
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    Tooltip,
} from "recharts";

import type { KnowledgeMap } from "@/types/knowledge";


interface Props {

    graph: KnowledgeMap;

}



export default function KnowledgeMap1({
    graph
}: Props) {


    const nodes = graph.graph.nodes;



    return (

        <div className="h-[700px] rounded-xl border bg-white p-4">


            <ResponsiveContainer
                width="100%"
                height="100%"
            >


                <ScatterChart>


                    <XAxis
                        type="number"
                        dataKey="x"
                        hide
                    />


                    <YAxis
                        type="number"
                        dataKey="y"
                        hide
                    />


                    <Tooltip
                        formatter={
                            (_, __, item:any)=>[
                                item.payload.label,
                                item.payload.document ?? ""
                            ]
                        }

                    />

                    <Scatter
                        data={nodes}
                    />
                </ScatterChart>
            </ResponsiveContainer>
        </div>
    );

}