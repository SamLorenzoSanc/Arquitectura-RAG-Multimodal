from dataclasses import dataclass

from rag.composition import RagContainer, build_rag_container


@dataclass
class AppContainer:
    rag: RagContainer


def build_app_container() -> AppContainer:
    return AppContainer(rag=build_rag_container())
