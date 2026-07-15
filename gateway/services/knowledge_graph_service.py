import numpy as np
import umap

from sklearn.neighbors import NearestNeighbors


class KnowledgeGraphService:

    def __init__(self, collection):

        self.collection = collection

    async def build_graph(self):

        data = self.collection.get(
            include=[
                "embeddings",
                "documents",
                "metadatas"
            ]
        )

        embeddings = np.array(data["embeddings"])

        if len(embeddings) == 0:

            return {
                "nodes": [],
                "edges": []
            }

        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.15,
            metric="cosine",
            random_state=42,
        )

        coords = reducer.fit_transform(embeddings)

        nodes = []

        for i in range(len(data["ids"])):

            metadata = data["metadatas"][i] or {}

            nodes.append({

                "id": data["ids"][i],

                "label": metadata.get(
                    "title",
                    f"Chunk {i}"
                ),

                "document": metadata.get(
                    "source",
                    ""
                ),

                "x": float(coords[i][0]),

                "y": float(coords[i][1]),

                "group": metadata.get(
                    "source",
                    "default"
                )
            })

        nn = NearestNeighbors(
            n_neighbors=min(6, len(embeddings)),
            metric="cosine"
        )

        nn.fit(embeddings)

        distances, indices = nn.kneighbors(embeddings)

        edges = []

        visited = set()

        for i in range(len(indices)):

            for j in range(1, len(indices[i])):

                neighbour = indices[i][j]

                edge = tuple(
                    sorted(
                        (
                            data["ids"][i],
                            data["ids"][neighbour]
                        )
                    )
                )

                if edge in visited:
                    continue

                visited.add(edge)

                edges.append({

                    "source": edge[0],

                    "target": edge[1],

                    "weight": float(
                        1 - distances[i][j]
                    )
                })

        return {

            "nodes": nodes,

            "edges": edges
        }