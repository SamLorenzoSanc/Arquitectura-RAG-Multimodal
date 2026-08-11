"""Service package initializer.

Expose a lazily-instantiated RAG proxy so importing the `services` package
does not eagerly load heavy ML libraries during test collection.

Important: the proxy must NOT be named `rag_service`, because that collides
with the submodule `services.rag_service` and Python would bind the module
instead of this proxy (`from services import rag_service`).
"""

_rag_instance = None


def get_rag_service():
    """Singleton lazy de RAGService (evita shadowing del submódulo)."""
    global _rag_instance
    if _rag_instance is None:
        from .rag_service import RAGService

        _rag_instance = RAGService()
    return _rag_instance


class _RagProxy:
    def __getattr__(self, name):
        return getattr(get_rag_service(), name)


# Nombre sin colisión con services/rag_service.py
rag = _RagProxy()
