from __future__ import annotations

import asyncio
import logging
import os
import pickle
import re
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path
import ctranslate2
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi
from tenacity import retry, wait_exponential
from sqlalchemy import select

from models.document import Document
from models.chunk import Chunk as ChunkModel
from models.embedding import Embedding
from parsers.base import ParsingContext
from parsers.factory import FileParserFactory

logger = logging.getLogger(__name__)

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

MODEL = os.getenv("RAG_GENERATION_MODEL", "llama3")
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "qwen3-embedding:latest",
)

# Modelo Whisper usado exclusivamente para vídeos.
WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    "small",
)

WHISPER_DEVICE = os.getenv(
    "WHISPER_DEVICE",
    "auto",
)

WHISPER_COMPUTE_TYPE = os.getenv(
    "WHISPER_COMPUTE_TYPE",
    "auto",
)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1",
)

OLLAMA_API_KEY = os.getenv(
    "OLLAMA_API_KEY",
    "ollama",
)

wait_strategy = wait_exponential(multiplier=1, min=2, max=60)

# Debe coincidir con RAGService.bm25_index_dir.
BM25_INDEX_DIR = Path(__file__).resolve().parent / "bm25_indexes"
BM25_INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Markdown generado durante la ingesta.
EXTRACTED_MD_DIR = Path(__file__).resolve().parent / "extracted_md"
EXTRACTED_MD_DIR.mkdir(parents=True, exist_ok=True)

# Directorio temporal para audio de vídeos.
VIDEO_TMP_DIR = Path(
    os.getenv(
        "VIDEO_TMP_DIR",
        str(Path(__file__).resolve().parent / "video_tmp"),
    )
)
VIDEO_TMP_DIR.mkdir(parents=True, exist_ok=True)

client = AsyncOpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY,
)


# ---------------------------------------------------------------------------
# Tipos de vídeo soportados
# ---------------------------------------------------------------------------

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mpeg",
    ".mpg",
    ".m4v",
}

VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/matroska",
    "video/x-matroska",
    "video/webm",
    "video/mpeg",
    "video/x-m4v",
}


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------


class ChunkMetadata(BaseModel):
    """Metadata generada por el LLM para cada chunk."""

    headline: str = Field(
        description="Un título breve de 3 a 5 palabras para este fragmento"
    )
    summary: str = Field(description="Resumen de 1 a 2 oraciones del fragmento")


class VideoSummary(BaseModel):
    """Resultado estructurado del resumen de un vídeo."""

    title: str = Field(description="Título breve y descriptivo del vídeo")
    summary: str = Field(description="Resumen general del contenido del vídeo")
    key_points: list[str] = Field(
        default_factory=list, description="Lista de los puntos principales del vídeo"
    )


class ProcessedChunk(BaseModel):
    """Objeto interno que une el texto original con la metadata generada."""

    headline: str
    summary: str
    original_text: str


# ---------------------------------------------------------------------------
# Servicio de ingesta
# ---------------------------------------------------------------------------


class IngestService:
    """
    Pipeline de ingesta RAG.

    Documentos:
        parser -> Markdown -> chunking -> LLM enrichment
        -> embeddings -> PostgreSQL -> BM25

    Vídeos:
        vídeo -> FFmpeg/audio -> faster-whisper -> transcripción
        -> LLM resumen -> Markdown -> chunking -> LLM enrichment
        -> embeddings -> PostgreSQL -> BM25
    """

    def __init__(self, session):
        self.session = session
        self.parser_factory = FileParserFactory()

        # Lazy-load: no cargamos Whisper hasta procesar realmente un vídeo.
        self._whisper_model = None

    # -----------------------------------------------------------------------
    # Helpers generales
    # -----------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str | None) -> str:
        text = text or ""
        text = unicodedata.normalize("NFKC", text).lower()
        return "".join(
            c
            for c in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(c)
        )

    @classmethod
    def _tokenize(cls, text: str | None) -> list[str]:
        normalized = cls._normalize_text(text)
        return re.findall(
            r"[^\W_]+(?:[-/][^\W_]+)*",
            normalized,
            flags=re.UNICODE,
        )

    @staticmethod
    def _safe_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    @classmethod
    def _bm25_path(cls, tenant_id: str) -> Path:
        return BM25_INDEX_DIR / (f"tenant_{cls._safe_filename(str(tenant_id))}.pkl")

    @staticmethod
    def _is_video(document: Document) -> bool:
        mime_type = (document.mime_type or "").lower().split(";")[0].strip()
        suffix = Path(document.filename or "").suffix.lower()

        return mime_type in VIDEO_MIME_TYPES or suffix in VIDEO_EXTENSIONS

    # -----------------------------------------------------------------------
    # BM25
    # -----------------------------------------------------------------------

    async def _rebuild_bm25_index(self, tenant_id: str):
        """Regenera el índice BM25 del tenant después de una ingesta exitosa."""
        stmt = (
            select(ChunkModel, Document)
            .join(Document, Document.id == ChunkModel.document_id)
            .where(Document.tenant_id == tenant_id)
            .order_by(Document.id, ChunkModel.position)
        )

        result_proxy = await self.session.execute(stmt)
        rows = result_proxy.all()

        documents = []

        for chunk, document in rows:
            text = "\n".join(
                part
                for part in [
                    chunk.headline,
                    chunk.summary,
                    chunk.content,
                ]
                if part
            )

            documents.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "tenant_id": str(document.tenant_id),
                    "knowledge_base_id": str(document.knowledge_base_id),
                    "source": document.filename,
                    "type": document.mime_type,
                    "position": chunk.position,
                    "text": text,
                }
            )

        path = self._bm25_path(tenant_id)

        if not documents:
            if path.exists():
                path.unlink()
            return

        corpus = [self._tokenize(item["text"]) for item in documents]

        # Validación del corpus.
        BM25Okapi(corpus)

        payload = {
            "version": 1,
            "tenant_id": str(tenant_id),
            "documents": documents,
            "created_at": time.time(),
        }

        tmp_path = path.with_suffix(".tmp")

        with tmp_path.open("wb") as fh:
            pickle.dump(
                payload,
                fh,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

        tmp_path.replace(path)

        logger.info(
            "[BM25 INDEX] Tenant %s: %s chunks indexados en %s",
            tenant_id,
            len(documents),
            path,
        )

    # -----------------------------------------------------------------------
    # Vídeo
    # -----------------------------------------------------------------------

    def _get_whisper_model(self):
        if self._whisper_model is not None:
            print("[WHISPER] Modelo ya cargado")
            return self._whisper_model

        print("=" * 80)
        print("[WHISPER] INICIALIZANDO")
        print(f"[WHISPER] model={WHISPER_MODEL}")
        print(f"[WHISPER] device={WHISPER_DEVICE}")
        print(f"[WHISPER] compute_type={WHISPER_COMPUTE_TYPE}")
        print("=" * 80)

        print(f"[WHISPER] CTranslate2={ctranslate2.__version__}")

        print(f"[WHISPER] CUDA devices=" f"{ctranslate2.get_cuda_device_count()}")

        print("[WHISPER] Creando WhisperModel...")

        self._whisper_model = WhisperModel(
            WHISPER_MODEL,
            device="cuda",
            compute_type="float16",
        )

        print("[WHISPER] WhisperModel creado correctamente")

        return self._whisper_model

    async def _extract_audio(self, video_path: Path) -> Path:
        """
        Extrae la pista de audio del vídeo usando FFmpeg.

        Se ejecuta FFmpeg en un thread para evitar problemas con
        asyncio.create_subprocess_exec() en Windows.
        """

        print("=" * 80)
        print("[VIDEO] EXTRACCIÓN DE AUDIO")
        print("=" * 80)

        print(f"[VIDEO] video_path = {video_path}")
        print(f"[VIDEO] exists     = {video_path.exists()}")

        if not video_path.exists():
            raise FileNotFoundError(f"Vídeo no encontrado: {video_path}")

        output_path = VIDEO_TMP_DIR / (
            f"{self._safe_filename(video_path.stem)}_" f"{time.time_ns()}.wav"
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

        print("[VIDEO] Ejecutando FFmpeg...")
        print("[VIDEO] Comando:")
        print(" ".join(command))

        try:
            process = await asyncio.to_thread(
                subprocess.run,
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        except FileNotFoundError as exc:
            print("[VIDEO] FFmpeg NO ENCONTRADO")
            print(f"[VIDEO] Error: {exc}")

            raise RuntimeError(
                "FFmpeg no está instalado o no está disponible "
                "en el PATH del sistema."
            ) from exc

        except Exception as exc:
            print("[VIDEO] ERROR ejecutando FFmpeg")
            print(f"[VIDEO] Tipo: {type(exc).__name__}")
            print(f"[VIDEO] Error: {exc}")

            raise

        print(f"[VIDEO] FFmpeg returncode = {process.returncode}")

        if process.returncode != 0:

            error = process.stderr.decode(
                "utf-8",
                errors="replace",
            )

            print("[VIDEO] FFmpeg terminó con ERROR")
            print("-" * 80)
            print(error)
            print("-" * 80)

            raise RuntimeError("No se pudo extraer el audio del vídeo con FFmpeg.")

        if not output_path.exists():

            print(
                "[VIDEO] ERROR: FFmpeg terminó correctamente " "pero no generó el WAV."
            )

            raise RuntimeError("FFmpeg terminó correctamente pero no generó el audio.")

        print("[VIDEO] Audio extraído correctamente")
        print(f"[VIDEO] output_path = {output_path}")
        print(f"[VIDEO] size        = {output_path.stat().st_size} bytes")

        return output_path

    async def _transcribe_video(
        self,
        audio_path: Path,
    ) -> list[dict]:
        """
        Transcribe el audio usando faster-whisper.

        Devuelve segmentos con timestamps para poder conservar
        referencias temporales en el Markdown.
        """
        model = self._get_whisper_model()

        logger.info("[VIDEO] Transcribiendo audio con Whisper...")

        def transcribe_sync():
            segments, info = model.transcribe(
                str(audio_path),
                language="es",
                vad_filter=True,
                beam_size=5,
            )

            result = []

            for segment in segments:
                text = (segment.text or "").strip()

                if not text:
                    continue

                result.append(
                    {
                        "start": float(segment.start),
                        "end": float(segment.end),
                        "text": text,
                    }
                )

            return result, info

        segments, info = await asyncio.to_thread(transcribe_sync)

        logger.info(
            "[VIDEO] Transcripción completada: %s segmentos | idioma=%s",
            len(segments),
            getattr(info, "language", "unknown"),
        )

        if not segments:
            raise RuntimeError(
                "Whisper no ha encontrado voz/transcripción en el vídeo."
            )

        return segments

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Convierte segundos a HH:MM:SS."""
        total_seconds = max(0, int(seconds))

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _segments_to_transcript(
        self,
        segments: list[dict],
    ) -> str:
        """
        Convierte los segmentos Whisper a texto legible con timestamps.
        """
        lines = []

        for segment in segments:
            start = self._format_timestamp(segment["start"])
            end = self._format_timestamp(segment["end"])
            text = segment["text"].strip()

            lines.append(f"[{start} - {end}] {text}")

        return "\n".join(lines)

    async def _summarize_transcript(
        self,
        transcript: str,
        document: Document,
    ) -> VideoSummary:
        """
        Genera título, resumen y puntos principales del vídeo.

        Para evitar superar el contexto del LLM con vídeos largos,
        primero limitamos el texto enviado a esta fase. La transcripción
        completa se conserva posteriormente en Markdown.
        """
        # Aproximadamente 30k caracteres de contexto.
        summary_input = transcript[:30000]

        prompt = f"""
            Analiza exclusivamente la siguiente transcripción de un vídeo.

            Devuelve:
            - title: un título descriptivo de máximo 10 palabras.
            - summary: un resumen de 2 a 4 frases.
            - key_points: entre 2 y 5 puntos principales.

            REGLAS ESTRICTAS:
            - Escribe únicamente en español.
            - Utiliza exclusivamente información presente en la transcripción.
            - No inventes información.
            - No añadas notas.
            - No añadas explicaciones.
            - No añadas comentarios sobre la respuesta.
            - No escribas "Note:", "Nota:", "Let me know", ni texto similar.
            - No añadas emojis.
            - No repitas el prompt.
            - Si la transcripción es corta, genera menos puntos.
            - Cada key_point debe ser una frase breve y factual.
            - No introduzcas caracteres extraños ni contenido fuera de los campos solicitados.

            ARCHIVO:
            {document.filename}

            TRANSCRIPCIÓN:
            {summary_input}
        """

        logger.info(
            "[VIDEO] Generando resumen con modelo=%s",
            MODEL,
        )

        response = await client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format=VideoSummary,
        )

        parsed = response.choices[0].message.parsed

        if parsed is None:
            raise RuntimeError("El LLM no devolvió un resumen estructurado del vídeo.")

        return parsed

    def _build_video_markdown(
        self,
        document: Document,
        summary: VideoSummary,
        transcript: str,
    ) -> str:
        """
        Construye el documento Markdown que entrará posteriormente
        en el pipeline normal de chunking y embeddings.
        """
        title = summary.title.strip() or document.title or document.filename
        general_summary = summary.summary.strip()

        points = "\n".join(
            f"- {point.strip()}"
            for point in summary.key_points
            if point and point.strip()
        )

        if not points:
            points = "- No se han identificado puntos principales."

        markdown = f"""# {title}

            ## Resumen

            {general_summary}

            ## Puntos principales

            {points}

            ## Transcripción

            {transcript}
            """

        return markdown.strip() + "\n"

    async def _process_video(
        self,
        document: Document,
        file_path: Path,
    ) -> str:
        """
        Pipeline completo de vídeo:

            vídeo
              -> extracción de audio
              -> Whisper
              -> resumen LLM
              -> Markdown

        Devuelve el Markdown final.
        """
        logger.info(
            "[VIDEO] Iniciando procesamiento de %s",
            document.filename,
        )

        audio_path: Path | None = None

        try:
            # 1. Extraer audio.
            audio_path = await self._extract_audio(file_path)

            # 2. Transcribir.
            segments = await self._transcribe_video(audio_path)

            transcript = self._segments_to_transcript(segments)

            if len(transcript.strip()) < 10:
                raise RuntimeError("La transcripción generada es demasiado corta.")

            # 3. Resumir.
            summary = await self._summarize_transcript(
                transcript,
                document,
            )

            # 4. Crear Markdown.
            markdown = self._build_video_markdown(
                document=document,
                summary=summary,
                transcript=transcript,
            )

            # 5. Persistir Markdown.
            output_filename = f"{Path(document.filename).stem}_" f"{document.id}.md"

            output_file_path = EXTRACTED_MD_DIR / output_filename

            output_file_path.write_text(
                markdown,
                encoding="utf-8",
            )

            logger.info(
                "[VIDEO] Markdown generado: %s",
                output_file_path.resolve(),
            )

            return markdown

        finally:
            # El WAV es temporal y no debe quedarse almacenado.
            if audio_path is not None:
                try:
                    audio_path.unlink(missing_ok=True)
                except Exception:
                    logger.warning(
                        "[VIDEO] No se pudo eliminar el audio temporal %s",
                        audio_path,
                        exc_info=True,
                    )

    # -----------------------------------------------------------------------
    # Pipeline principal
    # -----------------------------------------------------------------------

    async def process(self, document: Document) -> int:
        """
        Procesa un documento o vídeo completo.

        Pipeline:
            parser -> markdown
            -> chunking
            -> enriquecimiento LLM
            -> embeddings
            -> PostgreSQL
            -> BM25
        """

        print("\n" + "=" * 80)
        print("[PROCESS] INICIO")
        print("=" * 80)

        print(f"[PROCESS] document.id       = {document.id}")
        print(f"[PROCESS] document.filename = {document.filename}")
        print(f"[PROCESS] document.mime_type = {document.mime_type}")
        print(f"[PROCESS] document.owner_id  = {document.owner_id}")
        print(f"[PROCESS] document.tenant_id = {document.tenant_id}")
        print(f"[PROCESS] storage_path       = {document.storage_path}")

        # -------------------------------------------------------------------
        # 1. ARCHIVO
        # -------------------------------------------------------------------

        print("\n[PROCESS] PASO 1 - Comprobando archivo...")

        file_path = Path(document.storage_path)

        print(f"[PROCESS] file_path = {file_path}")
        print(f"[PROCESS] exists    = {file_path.exists()}")

        if not file_path.exists():
            print("[PROCESS] ERROR: el archivo no existe")
            raise FileNotFoundError(f"El archivo almacenado no existe: {file_path}")

        print("[PROCESS] Archivo encontrado correctamente")

        # -------------------------------------------------------------------
        # 2. PARSING / TRANSCRIPCIÓN
        # -------------------------------------------------------------------

        print("\n[PROCESS] PASO 2 - Detectando tipo de archivo...")

        try:
            is_video = self._is_video(document)

            print(f"[PROCESS] is_video = {is_video}")

        except Exception as e:
            print("[PROCESS] ERROR en _is_video")
            print(f"[PROCESS] {type(e).__name__}: {e}")
            raise

        # -------------------------------------------------------------------
        # 3. PARSER
        # -------------------------------------------------------------------

        if is_video:

            print("\n[PROCESS] PASO 3 - Procesando VIDEO")

            try:
                print("[PROCESS] Iniciando _process_video()...")

                markdown = await self._process_video(
                    document=document,
                    file_path=file_path,
                )

                print("[PROCESS] _process_video() completado")
                print(f"[PROCESS] Markdown generado: {len(markdown)} caracteres")

            except Exception as e:
                print("\n[PROCESS] !!! ERROR EN VIDEO !!!")
                print(f"[PROCESS] Tipo: {type(e).__name__}")
                print(f"[PROCESS] Error: {e}")
                raise

        else:

            print("\n[PROCESS] PASO 3 - Procesando DOCUMENTO")

            try:
                print("[PROCESS] Creando parser...")

                parser = self.parser_factory.create(file_path)

                print(f"[PROCESS] Parser creado: {type(parser).__name__}")

                print("[PROCESS] Construyendo contexto...")

                context = self.build_context(document)

                print("[PROCESS] Contexto creado")

                print("[PROCESS] Ejecutando parser.parse()...")

                parsed = await parser.parse(
                    file_path,
                    context,
                )

                print("[PROCESS] parser.parse() completado")

                markdown = parsed.markdown

                print(f"[PROCESS] Markdown obtenido: " f"{len(markdown)} caracteres")

                if len(markdown.strip()) < 10:
                    print("[PROCESS] WARNING: " "Markdown extremadamente corto")

                # -----------------------------------------------------------
                # Guardar Markdown
                # -----------------------------------------------------------

                print("[PROCESS] Guardando Markdown...")

                output_filename = f"{Path(document.filename).stem}_" f"{document.id}.md"

                output_file_path = EXTRACTED_MD_DIR / output_filename

                output_file_path.write_text(
                    markdown,
                    encoding="utf-8",
                )

                print(
                    f"[PROCESS] Markdown guardado en: " f"{output_file_path.resolve()}"
                )

            except Exception as e:
                print("\n[PROCESS] !!! ERROR EN PARSER !!!")
                print(f"[PROCESS] Tipo: {type(e).__name__}")
                print(f"[PROCESS] Error: {e}")
                raise

        # -------------------------------------------------------------------
        # 4. CHUNKING
        # -------------------------------------------------------------------

        print("\n[PROCESS] PASO 4 - Iniciando CHUNKING...")

        try:

            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]

            print("[PROCESS] Creando MarkdownHeaderTextSplitter...")

            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on,
                strip_headers=False,
            )

            print("[PROCESS] Ejecutando split por headers...")

            header_splits = markdown_splitter.split_text(markdown)

            print(f"[PROCESS] Header splits: " f"{len(header_splits)}")

            print("[PROCESS] Creando RecursiveCharacterTextSplitter...")

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
            )

            print("[PROCESS] Ejecutando split final...")

            raw_chunks = text_splitter.split_documents(header_splits)

            print(f"[PROCESS] Raw chunks generados: " f"{len(raw_chunks)}")

            if not raw_chunks:
                print("[PROCESS] ERROR: no se generaron chunks")

                raise RuntimeError("No se han generado chunks a partir del Markdown.")

        except Exception as e:

            print("\n[PROCESS] !!! ERROR EN CHUNKING !!!")
            print(f"[PROCESS] Tipo: {type(e).__name__}")
            print(f"[PROCESS] Error: {e}")

            raise

        # -------------------------------------------------------------------
        # 5. ENRIQUECIMIENTO LLM
        # -------------------------------------------------------------------

        print("\n[PROCESS] PASO 5 - ENRIQUECIMIENTO LLM")

        try:

            print(f"[PROCESS] Chunks a enriquecer: " f"{len(raw_chunks)}")

            print(f"[PROCESS] Modelo LLM: {MODEL}")

            tasks = [self._enrich_chunk(chunk.page_content) for chunk in raw_chunks]

            print(f"[PROCESS] Tasks creadas: {len(tasks)}")

            print("[PROCESS] Ejecutando asyncio.gather()...")

            enriched_chunks = await asyncio.gather(*tasks)

            print("[PROCESS] Enriquecimiento completado")

            print(f"[PROCESS] Enriched chunks: " f"{len(enriched_chunks)}")

        except Exception as e:

            print("\n[PROCESS] !!! ERROR EN ENRIQUECIMIENTO LLM !!!")
            print(f"[PROCESS] Tipo: {type(e).__name__}")
            print(f"[PROCESS] Error: {e}")

            raise

        # -------------------------------------------------------------------
        # 6. EMBEDDINGS + POSTGRESQL
        # -------------------------------------------------------------------

        print("\n[PROCESS] PASO 6 - EMBEDDINGS + POSTGRESQL")

        try:

            print(f"[PROCESS] Modelo embeddings: " f"{EMBEDDING_MODEL}")

            print(f"[PROCESS] Chunks para embeddings: " f"{len(enriched_chunks)}")

            print("[PROCESS] Llamando a " "create_embeddings_and_save()...")

            await self.create_embeddings_and_save(
                document=document,
                chunks=enriched_chunks,
            )

            print("[PROCESS] create_embeddings_and_save() " "completado correctamente")

        except Exception as e:

            print("\n[PROCESS] !!! ERROR EN EMBEDDINGS/DB !!!")
            print(f"[PROCESS] Tipo: {type(e).__name__}")
            print(f"[PROCESS] Error: {e}")

            raise

        # -------------------------------------------------------------------
        # 7. BM25
        # -------------------------------------------------------------------

        print("\n[PROCESS] PASO 7 - BM25")

        try:

            print(f"[PROCESS] tenant_id = " f"{document.tenant_id}")

            print("[PROCESS] Reconstruyendo índice BM25...")

            await self._rebuild_bm25_index(str(document.tenant_id))

            print("[PROCESS] BM25 reconstruido correctamente")

        except Exception as e:

            print("\n[PROCESS] !!! ERROR EN BM25 !!!")
            print(f"[PROCESS] Tipo: {type(e).__name__}")
            print(f"[PROCESS] Error: {e}")

            raise

        print("\n" + "=" * 80)
        print("[PROCESS] COMPLETADO CORRECTAMENTE")
        print(f"[PROCESS] Documento : {document.filename}")
        print(f"[PROCESS] Chunks    : {len(enriched_chunks)}")
        print(f"[PROCESS] Tenant    : {document.tenant_id}")
        print("=" * 80 + "\n")

        return len(enriched_chunks)

    # -----------------------------------------------------------------------
    # Enriquecimiento de chunks
    # -----------------------------------------------------------------------

    @retry(wait=wait_strategy)
    async def _enrich_chunk(
        self,
        chunk_text: str,
    ) -> ProcessedChunk:
        """
        Genera headline y summary para cada chunk.

        Se conserva el texto original completo para el embedding y
        para el contexto RAG.
        """
        prompt = f"""
            Analiza el siguiente texto y extrae:

            1. Un título breve de 3 a 5 palabras.
            2. Un resumen sintético de 1 o 2 frases.

            Reglas:
            - Responde únicamente en español.
            - No inventes información.
            - El título debe describir fielmente el fragmento.
            - El resumen debe contener únicamente información presente
              en el texto.

            Texto:
            {chunk_text}
        """

        response = await client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format=ChunkMetadata,
        )

        parsed = response.choices[0].message.parsed

        headline = (
            parsed.headline.strip() if parsed and parsed.headline else "Sin título"
        )

        summary = parsed.summary.strip() if parsed and parsed.summary else "Sin resumen"

        return ProcessedChunk(
            headline=headline,
            summary=summary,
            original_text=chunk_text,
        )

    # -----------------------------------------------------------------------
    # Embeddings + persistencia
    # -----------------------------------------------------------------------

    async def create_embeddings_and_save(
        self,
        document: Document,
        chunks: list[ProcessedChunk],
    ):
        if not chunks:
            logger.warning("[EMBEDDINGS] No hay chunks para procesar.")
            return

        texts_to_embed = [
            (f"{chunk.headline}\n\n" f"{chunk.summary}\n\n" f"{chunk.original_text}")
            for chunk in chunks
        ]

        all_vectors = []

        # Mantener el batching existente.
        batch_size = 10

        logger.info(
            "[EMBEDDINGS] Generando vectores con '%s' " "para %s fragmentos",
            EMBEDDING_MODEL,
            len(texts_to_embed),
        )

        for i in range(
            0,
            len(texts_to_embed),
            batch_size,
        ):
            batch = texts_to_embed[i : i + batch_size]

            response = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )

            vectors_in_batch = [emb.embedding for emb in response.data]

            if len(vectors_in_batch) != len(batch):
                raise RuntimeError(
                    "El número de embeddings devuelto "
                    "no coincide con el número de textos."
                )

            all_vectors.extend(vectors_in_batch)

            logger.info(
                "[EMBEDDINGS BATCH %s] " "Vectores=%s dimensión=%s",
                i // batch_size + 1,
                len(vectors_in_batch),
                len(vectors_in_batch[0]),
            )

        # -------------------------------------------------------------------
        # Persistir chunks
        # -------------------------------------------------------------------

        chunk_models = []

        for position, chunk in enumerate(chunks):
            db_chunk = ChunkModel(
                document_id=document.id,
                position=position,
                headline=chunk.headline,
                summary=chunk.summary,
                content=chunk.original_text,
            )

            self.session.add(db_chunk)
            chunk_models.append(db_chunk)

        await self.session.flush()

        # -------------------------------------------------------------------
        # Persistir embeddings
        # -------------------------------------------------------------------

        for db_chunk, vector in zip(
            chunk_models,
            all_vectors,
        ):
            db_embedding = Embedding(
                chunk_id=db_chunk.id,
                model=EMBEDDING_MODEL,
                vector=vector,
            )

            self.session.add(db_embedding)

        await self.session.commit()

        logger.info(
            "[DB] Guardados %s chunks y %s embeddings "
            "correctamente. embedding_model=%s",
            len(chunk_models),
            len(all_vectors),
            EMBEDDING_MODEL,
        )

    # -----------------------------------------------------------------------
    # Contexto del parser
    # -----------------------------------------------------------------------

    def build_context(
        self,
        document: Document,
    ) -> ParsingContext:
        return ParsingContext(
            tenant_id=document.tenant_id,
            organization_id=None,
            department_id=None,
            member_id=document.owner_id,
            uploaded_by=document.owner_id,
            language="es",
            tags=[],
        )
