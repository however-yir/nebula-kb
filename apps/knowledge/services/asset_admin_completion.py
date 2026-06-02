from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set


@dataclass
class KnowledgeBaseTemplate:
    id: str
    name: str
    description: str
    default_tags: List[str]


@dataclass
class AdminChunk:
    id: str
    document_id: str
    text: str
    source_locator: str
    enabled: bool = True
    quality_score: int = 80
    version: int = 1
    history: List[str] = field(default_factory=list)


@dataclass
class AdminDocument:
    id: str
    knowledge_base_id: str
    filename: str
    source: str
    content: str = ""
    total_bytes: int = 0
    uploaded_bytes: int = 0
    status: str = "waiting"
    parse_duration_ms: int = 0
    chunk_count: int = 0
    vector_status: str = "pending"
    index_status: str = "pending"
    parse_log: List[str] = field(default_factory=list)
    retry_count: int = 0
    cancelled: bool = False
    duplicate_of: Optional[str] = None


@dataclass
class AdminKnowledgeBase:
    id: str
    name: str
    template_id: str
    owner: str
    team: str
    tags: Set[str]
    visibility: str = "workspace"
    description_html: str = ""
    status: str = "active"
    capacity_limit_bytes: int = 10 * 1024 * 1024
    model_binding: str = "gpt-demo"
    embedding_model: str = "embedding-demo"
    operational_note: str = ""
    version: int = 1
    updated_at: int = 0
    favorites: Set[str] = field(default_factory=set)
    recent_visits: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)


class KnowledgeAssetAdminCompletion:
    """In-memory acceptance model for knowledge-admin P1/P2 completion."""

    def __init__(self) -> None:
        self.templates = {
            "support": KnowledgeBaseTemplate(
                id="support",
                name="Support FAQ",
                description="Customer support question-answering template.",
                default_tags=["support", "faq"],
            ),
            "policy": KnowledgeBaseTemplate(
                id="policy",
                name="Policy Manual",
                description="Policy document governance template.",
                default_tags=["policy", "governance"],
            ),
        }
        self.demo_data_version = "2026.06"
        self.knowledge_bases: Dict[str, AdminKnowledgeBase] = {}
        self.documents: Dict[str, AdminDocument] = {}
        self.chunks: Dict[str, AdminChunk] = {}
        self._counter = 0
        self._clock = 0

    def initialize_demo_accounts(self) -> List[Dict[str, str]]:
        return [
            {"email": "admin@nebulakb.local", "role": "admin"},
            {"email": "operator@nebulakb.local", "role": "operator"},
            {"email": "viewer@nebulakb.local", "role": "viewer"},
        ]

    def demo_asset_manifest(self) -> Dict[str, object]:
        return {
            "version": self.demo_data_version,
            "scenario": "import -> parse -> retrieve -> feedback -> governance",
            "screenshots": {
                "knowledge_base_list": "docs/assets/screenshots/knowledge-base-list.svg",
                "document_ingestion": "docs/assets/screenshots/document-ingestion.svg",
                "qa_feedback": "docs/assets/screenshots/qa-feedback.svg",
                "admin_dashboard": "docs/assets/screenshots/admin-dashboard.svg",
            },
            "gif_source": "docs/assets/screenshots/demo.gif",
            "faq": [
                "Use scripts/demo_knowledge_admin.py to inspect the knowledge-admin path.",
                "Run demo cleanup through clean_demo_data() when resetting local data.",
            ],
        }

    def import_demo_knowledge_base(self) -> AdminKnowledgeBase:
        kb = self.create_knowledge_base(
            "Support Demo",
            template_id="support",
            owner="operator@nebulakb.local",
            team="Customer Success",
            tags={"demo"},
        )
        document = self.start_resumable_upload(
            kb.id,
            "refund-policy.md",
            total_bytes=128,
            source="demo-data/knowledge-sample/02-search-feedback.md",
        )
        self.append_upload_chunk(document.id, 128)
        self.complete_upload(document.id, "Refund requests require citations and feedback follow-up.")
        self.parse_document(document.id)
        self.bulk_reindex([document.id])
        return kb

    def clean_demo_data(self) -> int:
        count = len(self.knowledge_bases) + len(self.documents) + len(self.chunks)
        self.knowledge_bases.clear()
        self.documents.clear()
        self.chunks.clear()
        return count

    def create_knowledge_base(
        self,
        name: str,
        template_id: str,
        owner: str,
        team: str,
        tags: Optional[Iterable[str]] = None,
        visibility: str = "workspace",
    ) -> AdminKnowledgeBase:
        if template_id not in self.templates:
            raise ValueError(f"unknown knowledge base template: {template_id}")
        if visibility not in {"private", "workspace", "public"}:
            raise ValueError("visibility must be private, workspace, or public")
        template = self.templates[template_id]
        kb = AdminKnowledgeBase(
            id=self._next_id("kb"),
            name=name,
            template_id=template_id,
            owner=owner,
            team=team,
            tags=set(template.default_tags) | set(tags or []),
            visibility=visibility,
        )
        kb.history.append(f"created_from_template:{template_id}")
        self._touch(kb)
        self.knowledge_bases[kb.id] = kb
        return kb

    def archive_knowledge_base(self, knowledge_base_id: str) -> AdminKnowledgeBase:
        kb = self._kb(knowledge_base_id)
        kb.status = "archived"
        kb.history.append("archived")
        self._touch(kb)
        return kb

    def copy_knowledge_base(self, knowledge_base_id: str, new_name: str) -> AdminKnowledgeBase:
        source = self._kb(knowledge_base_id)
        copied = self.create_knowledge_base(
            new_name,
            source.template_id,
            source.owner,
            source.team,
            source.tags,
            source.visibility,
        )
        copied.description_html = source.description_html
        copied.model_binding = source.model_binding
        copied.embedding_model = source.embedding_model
        copied.history.append(f"copied_from:{source.id}")
        return copied

    def bulk_delete_knowledge_bases(self, knowledge_base_ids: Sequence[str]) -> List[str]:
        deleted: List[str] = []
        for knowledge_base_id in knowledge_base_ids:
            if knowledge_base_id in self.knowledge_bases:
                del self.knowledge_bases[knowledge_base_id]
                deleted.append(knowledge_base_id)
        return deleted

    def update_tags(self, knowledge_base_id: str, add: Iterable[str] = (), remove: Iterable[str] = ()) -> Set[str]:
        kb = self._kb(knowledge_base_id)
        kb.tags.update(add)
        kb.tags.difference_update(remove)
        kb.history.append("tags_updated")
        self._touch(kb)
        return kb.tags

    def update_owner(self, knowledge_base_id: str, owner: str) -> AdminKnowledgeBase:
        kb = self._kb(knowledge_base_id)
        kb.owner = owner
        kb.history.append(f"owner:{owner}")
        self._touch(kb)
        return kb

    def update_description(self, knowledge_base_id: str, description_html: str) -> AdminKnowledgeBase:
        kb = self._kb(knowledge_base_id)
        kb.description_html = description_html
        kb.history.append("description_updated")
        self._touch(kb)
        return kb

    def set_visibility(self, knowledge_base_id: str, visibility: str) -> AdminKnowledgeBase:
        kb = self._kb(knowledge_base_id)
        if visibility not in {"private", "workspace", "public"}:
            raise ValueError("visibility must be private, workspace, or public")
        kb.visibility = visibility
        kb.history.append(f"visibility:{visibility}")
        self._touch(kb)
        return kb

    def capacity_stats(self, knowledge_base_id: str) -> Dict[str, int]:
        kb = self._kb(knowledge_base_id)
        used = sum(document.total_bytes for document in self._documents_for_kb(knowledge_base_id))
        return {
            "used_bytes": used,
            "limit_bytes": kb.capacity_limit_bytes,
            "remaining_bytes": max(kb.capacity_limit_bytes - used, 0),
        }

    def list_knowledge_bases(self, sort_by: str = "updated_at") -> List[AdminKnowledgeBase]:
        if sort_by == "updated_at":
            return sorted(self.knowledge_bases.values(), key=lambda kb: kb.updated_at, reverse=True)
        if sort_by == "name":
            return sorted(self.knowledge_bases.values(), key=lambda kb: kb.name)
        raise ValueError("sort_by must be updated_at or name")

    def search_knowledge_bases(
        self,
        query: str = "",
        tag: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> List[AdminKnowledgeBase]:
        rows = list(self.knowledge_bases.values())
        if query:
            rows = [kb for kb in rows if query.lower() in kb.name.lower()]
        if tag:
            rows = [kb for kb in rows if tag in kb.tags]
        if visibility:
            rows = [kb for kb in rows if kb.visibility == visibility]
        return rows

    def empty_state_guidance(self) -> str:
        if self.knowledge_bases:
            return ""
        return "Create a knowledge base from a template or import demo knowledge."

    def delete_risk_summary(self, knowledge_base_id: str) -> Dict[str, int]:
        documents = self._documents_for_kb(knowledge_base_id)
        chunk_count = sum(document.chunk_count for document in documents)
        return {"documents": len(documents), "chunks": chunk_count, "applications": 0}

    def export_knowledge_base(self, knowledge_base_id: str) -> Dict[str, object]:
        kb = self._kb(knowledge_base_id)
        return {
            "id": kb.id,
            "name": kb.name,
            "template_id": kb.template_id,
            "tags": sorted(kb.tags),
            "version": kb.version,
            "documents": [document.filename for document in self._documents_for_kb(kb.id)],
        }

    def import_knowledge_base(self, package: Dict[str, object], new_name: str) -> AdminKnowledgeBase:
        return self.create_knowledge_base(
            new_name,
            str(package["template_id"]),
            owner="imported-owner",
            team="Imported",
            tags=set(package.get("tags", [])),
        )

    def mark_version(self, knowledge_base_id: str, label: str) -> AdminKnowledgeBase:
        kb = self._kb(knowledge_base_id)
        kb.version += 1
        kb.history.append(f"version:{kb.version}:{label}")
        self._touch(kb)
        return kb

    def change_history(self, knowledge_base_id: str) -> List[str]:
        return list(self._kb(knowledge_base_id).history)

    def favorite(self, knowledge_base_id: str, user_id: str) -> None:
        self._kb(knowledge_base_id).favorites.add(user_id)

    def record_recent_visit(self, knowledge_base_id: str, user_id: str) -> List[str]:
        kb = self._kb(knowledge_base_id)
        kb.recent_visits = [user_id] + [item for item in kb.recent_visits if item != user_id]
        return kb.recent_visits[:5]

    def model_binding_check(self, knowledge_base_id: str) -> Dict[str, str]:
        kb = self._kb(knowledge_base_id)
        return {"model": kb.model_binding, "embedding_model": kb.embedding_model, "status": "ok"}

    def change_embedding_model(self, knowledge_base_id: str, embedding_model: str) -> Dict[str, str]:
        kb = self._kb(knowledge_base_id)
        old = kb.embedding_model
        kb.embedding_model = embedding_model
        kb.history.append(f"embedding_changed:{old}->{embedding_model}")
        return {"status": "requires_reindex", "from": old, "to": embedding_model}

    def set_operational_note(self, knowledge_base_id: str, note: str) -> str:
        kb = self._kb(knowledge_base_id)
        kb.operational_note = note
        kb.history.append("operational_note_updated")
        return kb.operational_note

    def start_resumable_upload(
        self,
        knowledge_base_id: str,
        filename: str,
        total_bytes: int,
        source: str,
    ) -> AdminDocument:
        self._kb(knowledge_base_id)
        document = AdminDocument(
            id=self._next_id("doc"),
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            source=source,
            total_bytes=total_bytes,
            status="uploading",
        )
        document.parse_log.append("upload_started")
        self.documents[document.id] = document
        return document

    def append_upload_chunk(self, document_id: str, size_bytes: int) -> AdminDocument:
        document = self._document(document_id)
        document.uploaded_bytes = min(document.uploaded_bytes + size_bytes, document.total_bytes)
        document.parse_log.append(f"uploaded:{document.uploaded_bytes}/{document.total_bytes}")
        return document

    def complete_upload(self, document_id: str, content: str) -> AdminDocument:
        document = self._document(document_id)
        if document.uploaded_bytes < document.total_bytes:
            raise ValueError("resumable upload is incomplete")
        document.duplicate_of = self.detect_duplicate(document.knowledge_base_id, document.filename, exclude=document.id)
        document.content = content
        document.status = "uploaded"
        document.parse_log.append("upload_completed")
        return document

    def detect_duplicate(self, knowledge_base_id: str, filename: str, exclude: str = "") -> Optional[str]:
        for document in self._documents_for_kb(knowledge_base_id):
            if document.id != exclude and document.filename == filename and document.status != "cancelled":
                return document.id
        return None

    def parse_document(self, document_id: str, duration_ms: int = 120) -> AdminDocument:
        document = self._document(document_id)
        if document.cancelled:
            raise ValueError("cancelled parse task cannot continue")
        document.status = "parsed"
        document.parse_duration_ms = duration_ms
        document.vector_status = "completed"
        document.index_status = "pending"
        document.parse_log.append(f"parsed:{duration_ms}ms")
        self._replace_chunks(document, self._split_content(document))
        return document

    def bulk_reparse(self, document_ids: Sequence[str]) -> List[str]:
        return [self.parse_document(document_id).id for document_id in document_ids]

    def bulk_reindex(self, document_ids: Sequence[str]) -> List[str]:
        indexed: List[str] = []
        for document_id in document_ids:
            document = self._document(document_id)
            document.index_status = "indexed"
            document.status = "indexed"
            document.parse_log.append("indexed")
            indexed.append(document.id)
        return indexed

    def redirect_after_upload(self, document_id: str) -> str:
        document = self._document(document_id)
        return f"/knowledge/{document.knowledge_base_id}/documents/{document.id}/chunks"

    def retry_failed_parse(self, document_id: str, recovered_content: str) -> AdminDocument:
        document = self._document(document_id)
        document.retry_count += 1
        document.cancelled = False
        document.content = recovered_content
        document.parse_log.append("retry_started")
        return self.parse_document(document.id)

    def download_parse_log(self, document_id: str) -> str:
        return "\n".join(self._document(document_id).parse_log)

    def cancel_parse_task(self, document_id: str) -> AdminDocument:
        document = self._document(document_id)
        document.cancelled = True
        document.status = "cancelled"
        document.parse_log.append("cancelled")
        return document

    def chunk_quality_scores(self, document_id: str) -> Dict[str, int]:
        return {chunk.id: chunk.quality_score for chunk in self._chunks_for_document(document_id)}

    def low_quality_chunks(self, document_id: str, threshold: int = 60) -> List[AdminChunk]:
        return [chunk for chunk in self._chunks_for_document(document_id) if chunk.quality_score < threshold]

    def edit_chunk(self, chunk_id: str, text: str) -> AdminChunk:
        chunk = self._chunk(chunk_id)
        chunk.text = text
        chunk.version += 1
        chunk.history.append("edited")
        return chunk

    def merge_chunks(self, first_chunk_id: str, second_chunk_id: str) -> AdminChunk:
        first = self._chunk(first_chunk_id)
        second = self._chunk(second_chunk_id)
        first.text = f"{first.text}\n{second.text}"
        first.version += 1
        first.history.append(f"merged:{second.id}")
        del self.chunks[second.id]
        self._document(first.document_id).chunk_count -= 1
        return first

    def split_chunk(self, chunk_id: str, marker: str) -> AdminChunk:
        chunk = self._chunk(chunk_id)
        if marker not in chunk.text:
            raise ValueError("split marker not found")
        left, right = chunk.text.split(marker, 1)
        chunk.text = left.strip()
        chunk.version += 1
        new_chunk = AdminChunk(
            id=self._next_id("chunk"),
            document_id=chunk.document_id,
            text=right.strip(),
            source_locator=f"{chunk.source_locator}:split",
            quality_score=chunk.quality_score,
            history=[f"split_from:{chunk.id}"],
        )
        self.chunks[new_chunk.id] = new_chunk
        self._document(chunk.document_id).chunk_count += 1
        return new_chunk

    def disable_chunk(self, chunk_id: str) -> AdminChunk:
        chunk = self._chunk(chunk_id)
        chunk.enabled = False
        chunk.history.append("disabled")
        return chunk

    def batch_update_chunks(self, chunk_ids: Sequence[str], quality_score: int) -> List[str]:
        updated: List[str] = []
        for chunk_id in chunk_ids:
            chunk = self._chunk(chunk_id)
            chunk.quality_score = quality_score
            chunk.history.append(f"quality:{quality_score}")
            updated.append(chunk.id)
        return updated

    def chunk_versions(self, chunk_id: str) -> Dict[str, object]:
        chunk = self._chunk(chunk_id)
        return {"version": chunk.version, "history": list(chunk.history)}

    def search(
        self,
        query: str,
        knowledge_base_ids: Sequence[str],
        mode: str = "hybrid",
        top_k: int = 3,
        threshold: float = 0.0,
        rerank: bool = False,
    ) -> List[Dict[str, object]]:
        if mode not in {"keyword", "vector", "hybrid"}:
            raise ValueError("mode must be keyword, vector, or hybrid")
        terms = {term.lower() for term in query.split() if term.strip()}
        hits: List[Dict[str, object]] = []
        for chunk in self.chunks.values():
            if not chunk.enabled or self._document(chunk.document_id).knowledge_base_id not in knowledge_base_ids:
                continue
            chunk_terms = {term.lower().strip(".,") for term in chunk.text.split()}
            overlap = len(terms & chunk_terms)
            keyword_score = float(overlap)
            vector_score = overlap / max(len(terms), 1)
            score = {
                "keyword": keyword_score,
                "vector": vector_score,
                "hybrid": keyword_score + vector_score,
            }[mode]
            if rerank:
                score += chunk.quality_score / 1000
            confidence = min(score / max(len(terms), 1), 1.0)
            if score >= threshold and score > 0:
                hits.append(
                    {
                        "chunk_id": chunk.id,
                        "score": round(score, 4),
                        "confidence": round(confidence, 4),
                        "source_locator": chunk.source_locator,
                        "text": chunk.text,
                    }
                )
        hits.sort(key=lambda hit: (-float(hit["score"]), str(hit["chunk_id"])))
        return hits[:top_k]

    def ask_multi_knowledge(
        self,
        query: str,
        knowledge_base_ids: Sequence[str],
        context_enabled: bool = True,
        answer_length: str = "concise",
    ) -> Dict[str, object]:
        hits = self.search(query, knowledge_base_ids, mode="hybrid", top_k=5, threshold=0.1, rerank=True)
        return {
            "answer": hits[0]["text"] if hits else "No trusted knowledge found.",
            "confidence": hits[0]["confidence"] if hits else 0,
            "citations": [hit["source_locator"] for hit in hits],
            "context_enabled": context_enabled,
            "answer_length": answer_length,
        }

    def export_retrieval_results(self, hits: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
        return [
            {
                "chunk_id": hit["chunk_id"],
                "score": hit["score"],
                "source_locator": hit["source_locator"],
            }
            for hit in hits
        ]

    def _replace_chunks(self, document: AdminDocument, chunks: List[AdminChunk]) -> None:
        for chunk_id, chunk in list(self.chunks.items()):
            if chunk.document_id == document.id:
                del self.chunks[chunk_id]
        for chunk in chunks:
            self.chunks[chunk.id] = chunk
        document.chunk_count = len(chunks)

    def _split_content(self, document: AdminDocument) -> List[AdminChunk]:
        parts = [part.strip() for part in document.content.replace("\n", " ").split(".") if part.strip()]
        if not parts:
            parts = [document.content.strip() or document.filename]
        chunks: List[AdminChunk] = []
        for index, text in enumerate(parts, start=1):
            score = 50 if len(text) < 12 else 85
            chunks.append(
                AdminChunk(
                    id=self._next_id("chunk"),
                    document_id=document.id,
                    text=text,
                    source_locator=f"{document.filename}#chunk-{index}",
                    quality_score=score,
                    history=["created"],
                )
            )
        return chunks

    def _documents_for_kb(self, knowledge_base_id: str) -> List[AdminDocument]:
        return [
            document
            for document in self.documents.values()
            if document.knowledge_base_id == knowledge_base_id
        ]

    def _chunks_for_document(self, document_id: str) -> List[AdminChunk]:
        return [chunk for chunk in self.chunks.values() if chunk.document_id == document_id]

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def _touch(self, kb: AdminKnowledgeBase) -> None:
        self._clock += 1
        kb.updated_at = self._clock

    def _kb(self, knowledge_base_id: str) -> AdminKnowledgeBase:
        try:
            return self.knowledge_bases[knowledge_base_id]
        except KeyError as exc:
            raise KeyError(knowledge_base_id) from exc

    def _document(self, document_id: str) -> AdminDocument:
        try:
            return self.documents[document_id]
        except KeyError as exc:
            raise KeyError(document_id) from exc

    def _chunk(self, chunk_id: str) -> AdminChunk:
        try:
            return self.chunks[chunk_id]
        except KeyError as exc:
            raise KeyError(chunk_id) from exc
