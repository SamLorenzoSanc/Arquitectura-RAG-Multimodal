from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict
from pathlib import Path

from models.document import Document
from parsers.parsed_document import ParsedDocument

from models.knowledge_assets import (
    AssetContent,
    AssetContext,
    AssetMetadata,
    KnowledgeAsset,
)
logger = logging.getLogger(__name__)


class KnowledgeBuilder:

    def __init__(
        self,
        storage_root: Path = Path("storage/knowledge-base"),
    ) -> None:

        self.storage_root = storage_root

    async def ingest(
        self,
        document: Document,
        parsed_document: ParsedDocument,
    ) -> KnowledgeAsset:

        asset = self._build_asset(
            document,
            parsed_document,
        )

        self._create_structure(asset)

        self._save_original(asset)

        self._save_markdown(asset)

        self._save_metadata(asset)

        self._update_index(asset)

        logger.info(
            "Knowledge asset %s stored at %s",
            asset.metadata.asset_id,
            asset.root,
        )

        return asset


    def _build_asset(
        self,
        document: Document,
        parsed: ParsedDocument,
    ) -> KnowledgeAsset:

        root = self._document_root(document)

        context = AssetContext(

            tenant_id=document.tenant_id,

            knowledge_base_id=document.knowledge_base_id,

        )

        metadata = AssetMetadata(

            asset_id=document.id,

            tenant_id=document.tenant_id,

            knowledge_base_id=document.knowledge_base_id,

            uploaded_by=document.owner_id,

            source=document.storage_path,

            mime_type=parsed.metadata.get("mime_type", ""),

            parser=parsed.metadata.get("parser", ""),

            language=parsed.language,

            checksum=parsed.metadata.get("checksum", ""),

            size=document.size or 0,

        )

        content = AssetContent(

            title=parsed.title or document.filename,

            markdown=parsed.markdown,

            summary=parsed.summary,

            language=parsed.language,

            word_count=parsed.word_count,

            character_count=parsed.character_count,

            page_count=parsed.page_count,

            tags=[],

        )

        return KnowledgeAsset(

            context=context,

            metadata=metadata,

            content=content,

            root=root,

        )

    def _create_structure(
        self,
        asset: KnowledgeAsset,
    ) -> None:

        asset.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        asset.processing.mkdir(exist_ok=True)

        asset.chunks.mkdir(exist_ok=True)

        asset.resources.mkdir(exist_ok=True)

        asset.images.mkdir(exist_ok=True)

        asset.tables.mkdir(exist_ok=True)

    ###########################################################################

    def _save_original(
        self,
        asset: KnowledgeAsset,
    ) -> None:

        source = Path(asset.metadata.source)

        if not source.exists():
            return

        destination = asset.root / (
            "original" + source.suffix.lower()
        )

        shutil.copy2(
            source,
            destination,
        )

    ###########################################################################

    def _save_markdown(
        self,
        asset: KnowledgeAsset,
    ) -> None:

        asset.markdown.write_text(

            self._render_markdown(asset),

            encoding="utf8",

        )

    ###########################################################################

    def _save_metadata(
        self,
        asset: KnowledgeAsset,
    ) -> None:

        asset.metadata_file.write_text(

            json.dumps(

                asdict(asset),

                indent=4,

                ensure_ascii=False,

                default=str,

            ),

            encoding="utf8",

        )


    def _render_markdown(
        self,
        asset: KnowledgeAsset,
    ) -> str:

        m = asset.metadata
        c = asset.content

        return f"""---
title: {c.title}
asset_id: {m.asset_id}

tenant_id: {m.tenant_id}
knowledge_base_id: {m.knowledge_base_id}

filename: {Path(m.source).name}
mime_type: {m.mime_type}
parser: {m.parser}
language: {m.language}

checksum: {m.checksum}
size: {m.size}

word_count: {c.word_count}
character_count: {c.character_count}
page_count: {c.page_count}

created_at: {m.created_at.isoformat()}
---

{c.markdown}
"""

    ###########################################################################
    # INDEX
    ###########################################################################

    def _update_index(
        self,
        asset: KnowledgeAsset,
    ) -> None:

        kb_root = (
            self.storage_root
            / str(asset.context.tenant_id)
            / str(asset.context.knowledge_base_id)
        )

        documents = kb_root / "documents"

        documents.mkdir(
            parents=True,
            exist_ok=True,
        )

        lines = [

            "# Knowledge Base",

            "",

            "## Documents",

            "",

        ]

        for doc in sorted(documents.iterdir()):

            if not doc.is_dir():
                continue

            lines.append(
                f"- [{doc.name}](documents/{doc.name}/document.md)"
            )

        (kb_root / "index.md").write_text(

            "\n".join(lines),

            encoding="utf8",

        )

    ###########################################################################
    # PATHS
    ###########################################################################

    def _document_root(
        self,
        document: Document,
    ) -> Path:

        return (

            self.storage_root

            / str(document.tenant_id)

            / str(document.knowledge_base_id)

            / "documents"

            / str(document.id)

        )