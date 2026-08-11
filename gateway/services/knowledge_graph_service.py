import re
import math
from collections import Counter, defaultdict

import numpy as np
import umap

from sklearn.neighbors import NearestNeighbors
from sqlalchemy import select

from services.database import AsyncSessionLocal
from models.embedding import Embedding
from models.chunk import Chunk
from models.document import Document


class KnowledgeGraphService:
    def __init__(self, collection=None):
        self.collection = collection

    async def build_graph(
        self,
        tenant_id: str | None = None,
        preview: bool = False,
        knowledge_base_id: str | None = None,
        similarity_threshold: float = 0.45,
        max_neighbors: int = 8,
    ):
        """Construye un grafo de conocimiento.

        Si `self.collection` expone `get(...)` (p. ej. Chroma), lo usará.
        En caso contrario hará una consulta a la base de datos (pgvector)
        para recuperar embeddings y metadatos.
        Incluye todos los chunks del tenant/KB; las aristas semánticas solo
        entre chunks con embedding.
        """

        # Datos iniciales
        embeddings = np.array([])
        documents = []
        metadatas = []
        ids = []
        embedded_indices: list[int] = []

        # 1) Si se solicita preview, construimos un grafo de palabras a partir
        #    de un único documento de ejemplo del tenant.
        if preview:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Document)
                    .where(Document.tenant_id == tenant_id)
                    .order_by(Document.created_at.desc())
                    .limit(1)
                )
                if knowledge_base_id:
                    stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
                doc = (await session.execute(stmt)).scalar_one_or_none()

                if not doc:
                    return {"nodes": [], "edges": [], "stats": {}}

                # Obtener chunks del documento
                stmt_chunks = (
                    select(Chunk)
                    .where(Chunk.document_id == doc.id)
                    .order_by(Chunk.position)
                )
                chunk_rows = (await session.execute(stmt_chunks)).scalars().all()

            full_text = "\n\n".join(
                part
                for chunk in chunk_rows
                for part in [chunk.headline, chunk.summary, chunk.content]
                if part
            )

            # Tokenizar y filtrar stopwords básicos en español
            tokens = [
                w.lower()
                for w in re.findall(r"[\wáéíóúñ]+", full_text, flags=re.UNICODE)
            ]
            STOPWORDS = set(
                [
                    "de",
                    "la",
                    "que",
                    "el",
                    "en",
                    "y",
                    "a",
                    "los",
                    "se",
                    "del",
                    "las",
                    "por",
                    "un",
                    "para",
                    "con",
                    "no",
                    "una",
                    "su",
                    "al",
                    "es",
                    "lo",
                    "como",
                    "más",
                    "pero",
                    "sus",
                    "le",
                    "ya",
                    "o",
                    "este",
                    "sí",
                    "esta",
                    "entre",
                    "cuando",
                    "muy",
                    "sin",
                    "sobre",
                    "también",
                    "me",
                    "hasta",
                    "hay",
                    "donde",
                    "quien",
                ]
            )

            tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
            if not tokens:
                return {"nodes": [], "edges": [], "stats": {}}

            freq = Counter(tokens)
            TOP_K = min(40, len(freq))
            top_words = [w for w, _ in freq.most_common(TOP_K)]

            # Co-ocurrencias (ventana deslizante)
            window = 4
            idx_map = {w: i for i, w in enumerate(top_words)}
            n = len(top_words)
            cooc = [[0] * n for _ in range(n)]
            token_positions = [i for i, t in enumerate(tokens) if t in idx_map]
            for i in range(len(tokens)):
                if tokens[i] not in idx_map:
                    continue
                for j in range(i + 1, min(i + window, len(tokens))):
                    if tokens[j] not in idx_map:
                        continue
                    a = idx_map[tokens[i]]
                    b = idx_map[tokens[j]]
                    cooc[a][b] += 1
                    cooc[b][a] += 1

            # Proyectar palabras a 2D usando UMAP sobre la matriz de coocurrencias

            mat = np.array(cooc, dtype=float)
            if mat.sum() == 0:
                coords = np.random.RandomState(42).rand(len(top_words), 2) * 2 - 1
            else:
                reducer_w = umap.UMAP(
                    n_components=2, n_neighbors=min(10, max(2, n - 1)), random_state=42
                )
                coords = reducer_w.fit_transform(mat)

            # Construir nodos/edges: un nodo documento y nodos por palabra
            nodes = []
            doc_node_id = f"doc:{doc.id}"
            nodes.append(
                {
                    "id": doc_node_id,
                    "type": "document",
                    "label": getattr(
                        doc, "title", getattr(doc, "filename", "documento de prueba")
                    ),
                    "document": getattr(doc, "filename", ""),
                    "content": full_text[:1000],
                    "metadata": {"id": str(doc.id)},
                    "x": 0.0,
                    "y": 0.0,
                    "weight": 50,
                }
            )

            edges = []
            max_freq = max(freq[w] for w in top_words) if top_words else 1
            for i, w in enumerate(top_words):
                nid = f"word:{w}"
                nodes.append(
                    {
                        "id": nid,
                        "type": "word",
                        "label": w,
                        "content": "",
                        "metadata": {"freq": int(freq[w])},
                        "x": float(coords[i][0]),
                        "y": float(coords[i][1]),
                        "weight": min(30, 5 + freq[w]),
                    }
                )

                # doc -> word
                edges.append(
                    {
                        "source": doc_node_id,
                        "target": nid,
                        "label": "contains",
                        "weight": float(freq[w]) / float(max_freq),
                    }
                )

            # word-word edges from cooc
            for i in range(n):
                for j in range(i + 1, n):
                    if cooc[i][j] > 0:
                        edges.append(
                            {
                                "source": f"word:{top_words[i]}",
                                "target": f"word:{top_words[j]}",
                                "label": "cooc",
                                "weight": float(cooc[i][j])
                                / max(1.0, max(max(row) for row in cooc)),
                            }
                        )

            stats = {"nodes": len(nodes), "edges": len(edges), "documents": 1}
            return {"nodes": nodes, "edges": edges, "stats": stats}

        # 2) Si la colección tiene método `get` (Chroma), reutilizamos la lógica existente
        if (
            self.collection
            and hasattr(self.collection, "get")
            and callable(getattr(self.collection, "get"))
        ):
            data = self.collection.get(include=["embeddings", "documents", "metadatas"])
            raw_embeddings = data.get("embeddings", []) or []
            documents = data.get("documents", []) or []
            metadatas = data.get("metadatas", []) or []
            ids = data.get("ids", []) or []
            embeddings_list = []
            for idx, emb in enumerate(raw_embeddings):
                if emb is None:
                    if idx < len(metadatas) and isinstance(metadatas[idx], dict):
                        metadatas[idx] = {**metadatas[idx], "has_embedding": False}
                    continue
                embeddings_list.append(list(emb))
                embedded_indices.append(idx)
                if idx < len(metadatas) and isinstance(metadatas[idx], dict):
                    metadatas[idx] = {**metadatas[idx], "has_embedding": True}
            embeddings = np.array(embeddings_list) if embeddings_list else np.array([])

        else:
            # pgvector: chunks del tenant (opcionalmente de una KB), con o sin embedding
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Chunk, Document, Embedding)
                    .join(Document, Document.id == Chunk.document_id)
                    .outerjoin(Embedding, Embedding.chunk_id == Chunk.id)
                    .where(Document.tenant_id == tenant_id)
                    .order_by(Document.filename, Chunk.position)
                )
                if knowledge_base_id:
                    stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)

                result = await session.execute(stmt)
                rows = result.all()

            embeddings_list = []
            embedded_indices = []
            for idx, (chunk, document, embedding) in enumerate(rows):
                text = "\n\n".join(
                    part
                    for part in [chunk.headline, chunk.summary, chunk.content]
                    if part
                ).strip()
                documents.append(text)

                meta = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "tenant_id": str(document.tenant_id),
                    "knowledge_base_id": str(document.knowledge_base_id),
                    "source": document.filename,
                    "type": document.mime_type,
                    "position": chunk.position,
                    "has_embedding": embedding is not None and embedding.vector is not None,
                }
                metadatas.append(meta)
                ids.append(str(chunk.id))

                if embedding is not None and embedding.vector is not None:
                    embeddings_list.append(list(embedding.vector))
                    embedded_indices.append(idx)

            embeddings = np.array(embeddings_list) if embeddings_list else np.array([])

        if len(ids) == 0:
            return {"nodes": [], "edges": [], "stats": {}}

        # Layout 2D solo con chunks que tienen embedding; el resto se coloca alrededor.
        coords = np.zeros((len(ids), 2), dtype=float)
        if len(embeddings) >= 2:
            reducer = umap.UMAP(
                n_components=2,
                n_neighbors=min(15, max(2, len(embeddings) - 1)),
                min_dist=0.15,
                metric="cosine",
                random_state=42,
            )
            embedded_coords = reducer.fit_transform(embeddings)
            for local_i, global_i in enumerate(embedded_indices):
                coords[global_i] = embedded_coords[local_i]
        elif len(embeddings) == 1:
            coords[embedded_indices[0]] = [0.0, 0.0]

        # Colocar chunks sin embedding en un anillo
        orphan_i = 0
        for i, meta in enumerate(metadatas):
            if meta.get("has_embedding"):
                continue
            angle = (2 * math.pi * orphan_i) / max(1, sum(1 for m in metadatas if not m.get("has_embedding")))
            coords[i] = [math.cos(angle) * 3.5, math.sin(angle) * 3.5]
            orphan_i += 1

        # NODOS (todos los chunks)
        nodes = []
        for i, chunk_id in enumerate(ids):
            metadata = metadatas[i] or {}
            content = documents[i] or ""
            source = metadata.get("source", "desconocido")
            title = metadata.get("title", source)

            nodes.append(
                {
                    "id": chunk_id,
                    "type": "chunk",
                    "label": title,
                    "document": source,
                    "content": content[:500],
                    "metadata": metadata,
                    "words": len(content.split()),
                    "x": float(coords[i][0]),
                    "y": float(coords[i][1]),
                    "weight": min(30, max(5, len(content) / 100)),
                    "group": source,
                    "has_embedding": bool(metadata.get("has_embedding")),
                }
            )

        # RELACIONES SEMÁNTICAS (solo entre chunks con embedding)
        edges = []
        if len(embeddings) >= 2:
            nn = NearestNeighbors(
                n_neighbors=min(max_neighbors + 1, len(embeddings)),
                metric="cosine",
            )
            nn.fit(embeddings)
            distances, indices = nn.kneighbors(embeddings)

            visited = set()
            for i in range(len(indices)):
                src_id = ids[embedded_indices[i]]
                for j in range(1, len(indices[i])):
                    neighbour_local = indices[i][j]
                    neighbour_id = ids[embedded_indices[neighbour_local]]
                    similarity = 1 - distances[i][j]
                    if similarity < similarity_threshold:
                        continue
                    edge = tuple(sorted((src_id, neighbour_id)))
                    if edge in visited:
                        continue
                    visited.add(edge)
                    edges.append(
                        {
                            "source": edge[0],
                            "target": edge[1],
                            "label": "relación semántica",
                            "weight": float(similarity),
                        }
                    )

        n_embedded = len(embedded_indices)
        stats = {
            "nodes": len(nodes),
            "edges": len(edges),
            "documents": len(set(node["document"] for node in nodes)),
            "chunks": len(nodes),
            "chunks_with_embedding": n_embedded,
            "chunks_without_embedding": len(nodes) - n_embedded,
            "similarity_threshold": similarity_threshold,
            "average_similarity": (
                sum(edge["weight"] for edge in edges) / len(edges) if edges else 0
            ),
            "knowledge_base_id": knowledge_base_id,
        }

        return {"nodes": nodes, "edges": edges, "stats": stats}
