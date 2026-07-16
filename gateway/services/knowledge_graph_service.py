import numpy as np
import umap

from sklearn.neighbors import NearestNeighbors

class KnowledgeGraphService:


    def __init__(
        self,
        collection
    ):

        self.collection = collection




    async def build_graph(self):


        data = self.collection.get(
            include=[
                "embeddings",
                "documents",
                "metadatas",
            ]
        )



        embeddings = np.array(
            data["embeddings"]
        )


        documents = data["documents"]

        metadatas = data["metadatas"]

        ids = data["ids"]




        if len(embeddings) == 0:


            return {

                "nodes": [],

                "edges": [],

                "stats": {}

            }





        #
        # PROYECCIÓN VISUAL 2D
        #

        reducer = umap.UMAP(

            n_components=2,

            n_neighbors=min(
                15,
                len(embeddings)-1
            ),

            min_dist=0.15,

            metric="cosine",

            random_state=42,

        )


        coords = reducer.fit_transform(
            embeddings
        )





        #
        # NODOS
        #

        nodes = []



        for i, chunk_id in enumerate(ids):


            metadata = (
                metadatas[i]
                or {}
            )


            content = (
                documents[i]
                or ""
            )



            source = metadata.get(
                "source",
                "desconocido"
            )


            title = metadata.get(
                "title",
                source
            )



            nodes.append({

                "id":
                    chunk_id,


                "type":
                    "chunk",



                "label":
                    title,



                "document":
                    source,



                "content":
                    content[:500],



                "metadata":
                    metadata,



                "words":
                    len(
                        content.split()
                    ),



                "x":
                    float(
                        coords[i][0]
                    ),



                "y":
                    float(
                        coords[i][1]
                    ),



                "weight":
                    min(
                        30,
                        max(
                            5,
                            len(content) / 100
                        )
                    ),



                "group":
                    source

            })





        #
        # RELACIONES SEMÁNTICAS
        #

        nn = NearestNeighbors(

            n_neighbors=min(
                6,
                len(embeddings)
            ),

            metric="cosine"

        )



        nn.fit(
            embeddings
        )



        distances, indices = (
            nn.kneighbors(
                embeddings
            )
        )



        edges = []

        visited = set()



        for i in range(
            len(indices)
        ):



            for j in range(
                1,
                len(indices[i])
            ):



                neighbour = (
                    indices[i][j]
                )



                similarity = (
                    1 -
                    distances[i][j]
                )



                #
                # Filtrar relaciones débiles
                #

                if similarity < 0.60:

                    continue




                edge = tuple(
                    sorted(
                        (
                            ids[i],
                            ids[neighbour]
                        )
                    )
                )



                if edge in visited:

                    continue



                visited.add(edge)



                edges.append({

                    "source":
                        edge[0],


                    "target":
                        edge[1],


                    "label":
                        "relación semántica",



                    "weight":
                        float(
                            similarity
                        )

                })






        #
        # INFORMACIÓN GENERAL DEL GRAFO
        #

        stats = {


            "nodes":
                len(nodes),


            "edges":
                len(edges),



            "documents":
                len(
                    set(
                        node["document"]
                        for node in nodes
                    )
                ),



            "average_similarity":
                (
                    sum(
                        edge["weight"]
                        for edge in edges
                    )
                    /
                    len(edges)
                    if edges
                    else 0
                )

        }





        return {


            "nodes":
                nodes,


            "edges":
                edges,


            "stats":
                stats

        }