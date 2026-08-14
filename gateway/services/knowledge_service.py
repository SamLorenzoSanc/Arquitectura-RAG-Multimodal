import numpy as np
import umap

from sqlalchemy import text
from sklearn.neighbors import NearestNeighbors


async def build_knowledge_graph(
    db,
    organization_id: str,
):
    """
    Construye un grafo a partir de los embeddings
    almacenados para una organización.
    """

    result = (
        await db.execute(
            text(
                """
                SELECT

                    id,
                    document_name,
                    title,
                    embedding

                FROM knowledge_chunks

                WHERE organization_id=:organization_id
                """
            ),
            {
                "organization_id": organization_id
            }
        )
    ).mappings().all()

    if len(result) == 0:
        return {
            "nodes": [],
            "edges": []
        }

    embeddings = []
    chunks = []

    for row in result:

        embeddings.append(row["embedding"])
        chunks.append(row)

    embeddings = np.array(embeddings)

    reducer = umap.UMAP(
        n_neighbors=20,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
        n_jobs=1,
    )

    coords = reducer.fit_transform(embeddings)

    nodes = []

    for i, chunk in enumerate(chunks):

        nodes.append(
            {
                "id": str(chunk["id"]),
                "label": chunk["title"],
                "document": chunk["document_name"],
                "cluster": 0,
                "x": float(coords[i][0]),
                "y": float(coords[i][1]),
            }
        )

    nbrs = NearestNeighbors(
        n_neighbors=6,
        metric="cosine",
    )

    nbrs.fit(embeddings)

    distances, indices = nbrs.kneighbors(embeddings)

    edges = []

    for i in range(len(chunks)):

        for j in range(1, len(indices[i])):

            neighbour = indices[i][j]

            similarity = 1 - distances[i][j]

            edges.append(
                {
                    "source": str(chunks[i]["id"]),
                    "target": str(chunks[neighbour]["id"]),
                    "weight": float(similarity),
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
    }