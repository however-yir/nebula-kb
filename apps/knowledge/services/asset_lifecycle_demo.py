from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Dict, Iterable, List, Optional
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for token in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            tokens.append(token)
            tokens.extend(token[index : index + 2] for index in range(len(token) - 1))
        elif len(token) > 1:
            tokens.append(token)
    return [token for token in tokens if len(token.strip()) > 1]


SUPPORTED_UPLOAD_FORMATS = {".md", ".txt"}
SUPPORTED_UPLOAD_MIME_TYPES = {
    ".md": {"text/markdown", "text/plain"},
    ".txt": {"text/plain"},
}
MAX_UPLOAD_BYTES = 64 * 1024


@dataclass
class KnowledgeBase:
    id: str
    tenant_id: str
    name: str
    owner: str
    created_at: datetime = field(default_factory=_now)


@dataclass
class UploadCheck:
    filename: str
    accepted: bool
    reason: Optional[str]
    size_bytes: int
    file_format: str
    content_type: str = ""
    max_bytes: int = MAX_UPLOAD_BYTES


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    heading: str
    citation: str
    source_locator: str
    indexed_at: Optional[datetime] = None
    hits: int = 0


@dataclass
class DocumentRecord:
    id: str
    tenant_id: str
    knowledge_base_id: str
    filename: str
    content: str
    file_format: str
    content_type: str
    source: str
    size_bytes: int
    status: str = "uploaded"
    upload_progress: int = 100
    error: Optional[str] = None
    failure_summary: Optional[str] = None
    chunks: List[Chunk] = field(default_factory=list)
    status_history: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    score: float
    excerpt: str
    citation: str
    retrieval_mode: str = "keyword"
    source_locator: str = ""


@dataclass
class Answer:
    question: str
    answer: str
    hits: List[SearchHit]
    citations: List[str]
    tenant_id: str = ""
    knowledge_base_id: str = ""
    stream_state: str = "completed"
    stream_events: List[str] = field(default_factory=list)
    fallback_reason: Optional[str] = None


@dataclass
class FeedbackRecord:
    id: str
    tenant_id: str
    knowledge_base_id: str
    question: str
    answer: str
    citations: List[str]
    rating: int
    reason: str
    status: str = "open"
    owner: Optional[str] = None
    governance_task_id: Optional[str] = None
    created_at: datetime = field(default_factory=_now)
    closed_at: Optional[datetime] = None


@dataclass
class GovernanceTask:
    id: str
    tenant_id: str
    knowledge_base_id: str
    feedback_id: str
    question: str
    answer: str
    citations: List[str]
    reason: str
    owner: str
    status: str = "open"
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    closed_at: Optional[datetime] = None


class KnowledgeAssetPlatform:
    """Small in-memory model used by docs, demo scripts, and baseline tests."""

    def __init__(self) -> None:
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.documents: Dict[str, DocumentRecord] = {}
        self.index: Dict[str, List[Chunk]] = {}
        self.answers: List[Answer] = []
        self.feedback: List[FeedbackRecord] = []
        self.governance_tasks: List[GovernanceTask] = []

    def create_knowledge_base(
        self,
        tenant_id: str,
        name: str,
        owner: str,
        knowledge_base_id: Optional[str] = None,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            id=knowledge_base_id or f"kb-{uuid4().hex[:8]}",
            tenant_id=tenant_id,
            name=name,
            owner=owner,
        )
        self.knowledge_bases[kb.id] = kb
        self.index.setdefault(kb.id, [])
        return kb

    def validate_upload(
        self,
        filename: str,
        content: str,
        content_type: Optional[str] = None,
    ) -> UploadCheck:
        suffix = self._file_format(filename)
        size_bytes = len(content.encode("utf-8"))
        if suffix not in SUPPORTED_UPLOAD_FORMATS:
            return UploadCheck(
                filename=filename,
                accepted=False,
                reason=f"unsupported file format: {suffix or 'none'}",
                size_bytes=size_bytes,
                file_format=suffix,
                content_type=content_type or "",
            )
        allowed_mime_types = SUPPORTED_UPLOAD_MIME_TYPES[suffix]
        normalized_content_type = (content_type or "").split(";")[0].strip().lower()
        if normalized_content_type and normalized_content_type not in allowed_mime_types:
            return UploadCheck(
                filename=filename,
                accepted=False,
                reason=f"unsupported mime type: {normalized_content_type}",
                size_bytes=size_bytes,
                file_format=suffix,
                content_type=normalized_content_type,
            )
        if size_bytes > MAX_UPLOAD_BYTES:
            return UploadCheck(
                filename=filename,
                accepted=False,
                reason=f"file exceeds {MAX_UPLOAD_BYTES} bytes",
                size_bytes=size_bytes,
                file_format=suffix,
                content_type=normalized_content_type or sorted(allowed_mime_types)[0],
            )
        return UploadCheck(
            filename=filename,
            accepted=True,
            reason=None,
            size_bytes=size_bytes,
            file_format=suffix,
            content_type=normalized_content_type or sorted(allowed_mime_types)[0],
        )

    def upload_document(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        filename: str,
        content: str,
        content_type: Optional[str] = None,
    ) -> DocumentRecord:
        self._require_kb_access(tenant_id, knowledge_base_id)
        upload_check = self.validate_upload(filename, content, content_type)
        if not upload_check.accepted:
            raise ValueError(upload_check.reason or "upload rejected")
        document = DocumentRecord(
            id=f"doc-{uuid4().hex[:8]}",
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            content=content,
            file_format=upload_check.file_format,
            content_type=upload_check.content_type,
            source=f"local-upload:{filename}",
            size_bytes=upload_check.size_bytes,
            status_history=["waiting", "uploading", "uploaded"],
        )
        self.documents[document.id] = document
        return document

    def parse_document(self, tenant_id: str, document_id: str) -> DocumentRecord:
        document = self._require_document_access(tenant_id, document_id)
        self._transition(document, "parsing")
        document.updated_at = _now()

        if not document.content.strip():
            return self._mark_parse_failed(document, "empty document")
        if "[PARSE_ERROR]" in document.content:
            return self._mark_parse_failed(document, "parser could not extract text layer")

        document.chunks = self._chunk_document(document)
        self._transition(document, "parsed")
        document.error = None
        document.failure_summary = None
        return document

    def index_document(self, tenant_id: str, document_id: str) -> DocumentRecord:
        document = self._require_document_access(tenant_id, document_id)
        self._require_kb_access(tenant_id, document.knowledge_base_id)
        if document.status != "parsed":
            raise ValueError(f"document must be parsed before indexing, got {document.status}")

        self._transition(document, "indexing")
        existing = [
            chunk
            for chunk in self.index[document.knowledge_base_id]
            if chunk.document_id != document.id
        ]
        for chunk in document.chunks:
            chunk.indexed_at = _now()
        self.index[document.knowledge_base_id] = existing + document.chunks
        self._transition(document, "indexed")
        document.updated_at = _now()
        return document

    def ingest_document(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        filename: str,
        content: str,
    ) -> DocumentRecord:
        document = self.upload_document(tenant_id, knowledge_base_id, filename, content)
        self.parse_document(tenant_id, document.id)
        if document.status == "parsed":
            self.index_document(tenant_id, document.id)
        return document

    def ask(self, tenant_id: str, knowledge_base_id: str, question: str) -> Answer:
        self._require_kb_access(tenant_id, knowledge_base_id)
        hits = self.search(tenant_id, knowledge_base_id, question)
        if not hits:
            answer = Answer(
                question=question,
                answer="未找到可靠知识。该问题已进入未命中问题池，等待运营人员补充或更新知识。",
                hits=[],
                citations=[],
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                stream_events=["retrieval_started", "fallback_returned", "completed"],
                fallback_reason="empty_result",
            )
            self.answers.append(answer)
            return answer

        best = hits[0]
        answer_text = f"根据知识库引用：{best.excerpt}"
        answer = Answer(
            question=question,
            answer=answer_text,
            hits=hits,
            citations=[hit.citation for hit in hits],
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            stream_events=["retrieval_started", "citations_attached", "completed"],
        )
        self.answers.append(answer)
        return answer

    def search(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        question: str,
        mode: str = "keyword",
    ) -> List[SearchHit]:
        self._require_kb_access(tenant_id, knowledge_base_id)
        if mode not in {"keyword", "vector"}:
            raise ValueError("mode must be keyword or vector")
        question_terms = set(_tokenize(question))
        if not question_terms:
            return []

        scored: List[SearchHit] = []
        for chunk in self.index.get(knowledge_base_id, []):
            chunk_terms = set(_tokenize(chunk.text + " " + chunk.heading))
            overlap = len(question_terms & chunk_terms)
            score = self._score_hit(overlap, len(question_terms), mode)
            if score > 0:
                chunk.hits += 1
                scored.append(
                    SearchHit(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        score=score,
                        excerpt=self._excerpt(chunk.text),
                        citation=chunk.citation,
                        retrieval_mode=mode,
                        source_locator=chunk.source_locator,
                    )
                )
        scored.sort(key=lambda hit: (-hit.score, hit.citation))
        return scored[:3]

    def submit_feedback(
        self,
        tenant_id: str,
        question: str,
        answer: str,
        rating: int,
        reason: str,
        knowledge_base_id: Optional[str] = None,
        citations: Optional[List[str]] = None,
        owner: str = "knowledge-ops",
    ) -> FeedbackRecord:
        if not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")
        answer_context = self._find_answer_context(tenant_id, question)
        feedback_knowledge_base_id = (
            knowledge_base_id
            or (answer_context.knowledge_base_id if answer_context else None)
            or self._default_knowledge_base_id_for_tenant(tenant_id)
        )
        feedback_citations = list(
            citations if citations is not None else (answer_context.citations if answer_context else [])
        )
        record = FeedbackRecord(
            id=f"fb-{uuid4().hex[:8]}",
            tenant_id=tenant_id,
            knowledge_base_id=feedback_knowledge_base_id,
            question=question,
            answer=answer,
            citations=feedback_citations,
            rating=rating,
            reason=reason,
        )
        self.feedback.append(record)
        if rating <= 2:
            task = self._create_governance_task(record, owner)
            record.governance_task_id = task.id
        return record

    def vote_answer(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        question: str,
        answer: str,
        vote: str,
        citations: Optional[List[str]] = None,
        reason: str = "",
        owner: str = "knowledge-ops",
    ) -> FeedbackRecord:
        if vote not in {"thumbs_up", "thumbs_down"}:
            raise ValueError("vote must be thumbs_up or thumbs_down")
        rating = 5 if vote == "thumbs_up" else 1
        feedback_reason = reason or ("positive feedback" if vote == "thumbs_up" else "negative feedback")
        return self.submit_feedback(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            answer=answer,
            citations=citations or [],
            rating=rating,
            reason=feedback_reason,
            owner=owner,
        )

    def low_quality_answers(
        self,
        tenant_id: str,
        knowledge_base_id: Optional[str] = None,
        reason: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[FeedbackRecord]:
        records = [
            record
            for record in self.feedback
            if record.tenant_id == tenant_id and record.rating <= 2
        ]
        if knowledge_base_id:
            records = [record for record in records if record.knowledge_base_id == knowledge_base_id]
        if reason:
            records = [record for record in records if reason in record.reason]
        if status:
            records = [
                record
                for record in records
                if record.status == status or self._task_status(record.governance_task_id) == status
            ]
        return records

    def close_feedback(self, tenant_id: str, feedback_id: str, owner: str) -> FeedbackRecord:
        for record in self.feedback:
            if record.tenant_id == tenant_id and record.id == feedback_id:
                record.status = "closed"
                record.owner = owner
                record.closed_at = _now()
                if record.governance_task_id:
                    self.update_governance_task(
                        tenant_id,
                        record.governance_task_id,
                        status="closed",
                        owner=owner,
                    )
                return record
        raise KeyError(feedback_id)

    def list_governance_tasks(
        self,
        tenant_id: str,
        knowledge_base_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[GovernanceTask]:
        tasks = [task for task in self.governance_tasks if task.tenant_id == tenant_id]
        if knowledge_base_id:
            tasks = [task for task in tasks if task.knowledge_base_id == knowledge_base_id]
        if status:
            tasks = [task for task in tasks if task.status == status]
        return tasks

    def update_governance_task(
        self,
        tenant_id: str,
        task_id: str,
        status: str,
        owner: Optional[str] = None,
    ) -> GovernanceTask:
        for task in self.governance_tasks:
            if task.tenant_id == tenant_id and task.id == task_id:
                task.status = status
                if owner:
                    task.owner = owner
                task.updated_at = _now()
                if status == "closed":
                    task.closed_at = task.closed_at or task.updated_at
                return task
        raise KeyError(task_id)

    def metrics(self, tenant_id: str) -> Dict[str, object]:
        tenant_answers = [
            answer
            for answer in self.answers
            if self._answer_belongs_to_tenant(answer, tenant_id)
        ]
        total_answers = len(tenant_answers)
        hit_answers = len([answer for answer in tenant_answers if answer.citations])
        tenant_feedback = [record for record in self.feedback if record.tenant_id == tenant_id]
        low_quality = [record for record in tenant_feedback if record.rating <= 2]
        open_feedback = [record for record in tenant_feedback if record.status != "closed"]
        unanswered_questions = [answer.question for answer in tenant_answers if answer.fallback_reason]
        stale_knowledge = self._stale_knowledge_for_tenant(tenant_id)

        return {
            "knowledge_hit_rate": round(hit_answers / total_answers, 4) if total_answers else 0,
            "low_quality_answer_rate": round(len(low_quality) / len(tenant_feedback), 4)
            if tenant_feedback
            else 0,
            "unanswered_question_count": len(unanswered_questions),
            "pending_feedback_count": len(open_feedback),
            "stale_knowledge_count": len(stale_knowledge),
            "unanswered_questions": unanswered_questions,
            "hot_knowledge": self._hot_knowledge_for_tenant(tenant_id),
            "stale_knowledge": stale_knowledge,
            "governance_tasks": [
                {
                    "id": task.id,
                    "knowledge_base_id": task.knowledge_base_id,
                    "question": task.question,
                    "reason": task.reason,
                    "owner": task.owner,
                    "status": task.status,
                }
                for task in self.list_governance_tasks(tenant_id)
            ],
            "feedback_closure_status": {
                "total": len(tenant_feedback),
                "open": len(open_feedback),
                "closed": len(tenant_feedback) - len(open_feedback),
            },
        }

    def metrics_by_knowledge_base(self, tenant_id: str) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for kb in self.knowledge_bases.values():
            if kb.tenant_id != tenant_id:
                continue
            rows.append(
                {
                    "knowledge_base_id": kb.id,
                    "name": kb.name,
                    "owner": kb.owner,
                    "health_score": self.knowledge_base_health(tenant_id, kb.id)["health_score"],
                    **self._metrics_for_knowledge_base(tenant_id, kb.id),
                }
            )
        return rows

    def operations_dashboard_first_screen(self, tenant_id: str) -> Dict[str, object]:
        metrics = self.metrics(tenant_id)
        knowledge_bases = self.metrics_by_knowledge_base(tenant_id)
        return {
            "summary_cards": {
                "knowledge_hit_rate": metrics["knowledge_hit_rate"],
                "low_quality_answer_rate": metrics["low_quality_answer_rate"],
                "pending_feedback_count": metrics["pending_feedback_count"],
                "unanswered_question_count": metrics["unanswered_question_count"],
            },
            "queues": {
                "unanswered_questions": metrics["unanswered_questions"][:5],
                "governance_tasks": metrics["governance_tasks"][:5],
            },
            "knowledge_bases": knowledge_bases,
        }

    def knowledge_base_health(self, tenant_id: str, knowledge_base_id: str) -> Dict[str, object]:
        kb = self._require_kb_access(tenant_id, knowledge_base_id)
        documents = [
            document
            for document in self.documents.values()
            if document.tenant_id == tenant_id and document.knowledge_base_id == knowledge_base_id
        ]
        indexed = [document for document in documents if document.status == "indexed"]
        failed = [document for document in documents if document.status == "failed"]
        metrics = self._metrics_for_knowledge_base(tenant_id, knowledge_base_id)
        penalty = (
            len(failed) * 20
            + int(metrics["pending_feedback_count"]) * 15
            + int(metrics["unanswered_question_count"]) * 10
        )
        score = max(0, min(100, 100 - penalty))
        return {
            "knowledge_base_id": kb.id,
            "name": kb.name,
            "owner": kb.owner,
            "health_score": score,
            "document_count": len(documents),
            "indexed_document_count": len(indexed),
            "failed_document_count": len(failed),
            "pending_feedback_count": metrics["pending_feedback_count"],
            "unanswered_question_count": metrics["unanswered_question_count"],
        }

    def chunk_preview(
        self,
        tenant_id: str,
        document_id: str,
        limit: int = 3,
    ) -> List[Dict[str, object]]:
        document = self._require_document_access(tenant_id, document_id)
        return [
            {
                "chunk_id": chunk.id,
                "heading": chunk.heading,
                "excerpt": self._excerpt(chunk.text, size=80),
                "citation": chunk.citation,
                "source_locator": chunk.source_locator,
            }
            for chunk in document.chunks[:limit]
        ]

    def locate_citation(self, tenant_id: str, citation: str) -> Dict[str, str]:
        for document in self.documents.values():
            if document.tenant_id != tenant_id:
                continue
            for chunk in document.chunks:
                if chunk.citation == citation:
                    return {
                        "document_id": document.id,
                        "filename": document.filename,
                        "chunk_id": chunk.id,
                        "heading": chunk.heading,
                        "source_locator": chunk.source_locator,
                    }
        raise KeyError(citation)

    def _mark_parse_failed(self, document: DocumentRecord, reason: str) -> DocumentRecord:
        self._transition(document, "failed")
        document.error = reason
        document.failure_summary = f"{document.filename}: {reason}"
        document.chunks = []
        return document

    def _chunk_document(self, document: DocumentRecord) -> List[Chunk]:
        chunks: List[Chunk] = []
        heading = document.filename
        buffer: List[str] = []

        for raw_line in document.content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if buffer:
                    chunks.append(self._build_chunk(document, heading, " ".join(buffer), len(chunks)))
                    buffer = []
                heading = line.lstrip("#").strip() or document.filename
            else:
                buffer.append(line)
        if buffer:
            chunks.append(self._build_chunk(document, heading, " ".join(buffer), len(chunks)))
        return chunks

    def _build_chunk(
        self,
        document: DocumentRecord,
        heading: str,
        text: str,
        offset: int,
    ) -> Chunk:
        chunk_id = f"{document.id}-chunk-{offset + 1}"
        return Chunk(
            id=chunk_id,
            document_id=document.id,
            text=text,
            heading=heading,
            citation=f"{document.filename}#{offset + 1}",
            source_locator=f"{document.filename} > {heading} > chunk {offset + 1}",
        )

    def _transition(self, document: DocumentRecord, status: str) -> None:
        document.status = status
        if not document.status_history or document.status_history[-1] != status:
            document.status_history.append(status)
        document.updated_at = _now()

    def _file_format(self, filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[1].lower()

    def _score_hit(self, overlap: int, question_term_count: int, mode: str) -> float:
        if overlap < 2:
            return 0
        if mode == "keyword":
            return float(overlap)
        return round(overlap / max(question_term_count, 1), 4)

    def _require_kb_access(self, tenant_id: str, knowledge_base_id: str) -> KnowledgeBase:
        kb = self.knowledge_bases.get(knowledge_base_id)
        if kb is None:
            raise KeyError(knowledge_base_id)
        if kb.tenant_id != tenant_id:
            raise PermissionError("tenant cannot access this knowledge base")
        return kb

    def _require_document_access(self, tenant_id: str, document_id: str) -> DocumentRecord:
        document = self.documents.get(document_id)
        if document is None:
            raise KeyError(document_id)
        if document.tenant_id != tenant_id:
            raise PermissionError("tenant cannot access this document")
        return document

    def _answer_belongs_to_tenant(self, answer: Answer, tenant_id: str) -> bool:
        if answer.tenant_id:
            return answer.tenant_id == tenant_id
        if not answer.hits:
            return True
        document = self.documents.get(answer.hits[0].document_id)
        return bool(document and document.tenant_id == tenant_id)

    def _create_governance_task(self, record: FeedbackRecord, owner: str) -> GovernanceTask:
        task = GovernanceTask(
            id=f"task-{uuid4().hex[:8]}",
            tenant_id=record.tenant_id,
            knowledge_base_id=record.knowledge_base_id,
            feedback_id=record.id,
            question=record.question,
            answer=record.answer,
            citations=list(record.citations),
            reason=record.reason,
            owner=owner,
        )
        self.governance_tasks.append(task)
        return task

    def _find_answer_context(self, tenant_id: str, question: str) -> Optional[Answer]:
        for answer in reversed(self.answers):
            if answer.tenant_id == tenant_id and answer.question == question:
                return answer
        return None

    def _default_knowledge_base_id_for_tenant(self, tenant_id: str) -> str:
        for kb in self.knowledge_bases.values():
            if kb.tenant_id == tenant_id:
                return kb.id
        raise KeyError(f"tenant has no knowledge base: {tenant_id}")

    def _task_status(self, task_id: Optional[str]) -> Optional[str]:
        if not task_id:
            return None
        for task in self.governance_tasks:
            if task.id == task_id:
                return task.status
        return None

    def _metrics_for_knowledge_base(self, tenant_id: str, knowledge_base_id: str) -> Dict[str, object]:
        answers = [
            answer
            for answer in self.answers
            if answer.tenant_id == tenant_id and answer.knowledge_base_id == knowledge_base_id
        ]
        feedback = [
            record
            for record in self.feedback
            if record.tenant_id == tenant_id and record.knowledge_base_id == knowledge_base_id
        ]
        stale = [
            document.filename
            for document in self.documents.values()
            if document.tenant_id == tenant_id
            and document.knowledge_base_id == knowledge_base_id
            and document.status == "failed"
        ]
        hit_answers = len([answer for answer in answers if answer.citations])
        low_quality = [record for record in feedback if record.rating <= 2]
        return {
            "knowledge_hit_rate": round(hit_answers / len(answers), 4) if answers else 0,
            "low_quality_answer_rate": round(len(low_quality) / len(feedback), 4) if feedback else 0,
            "unanswered_question_count": len([answer for answer in answers if answer.fallback_reason]),
            "pending_feedback_count": len([record for record in feedback if record.status != "closed"]),
            "stale_knowledge_count": len(stale),
        }

    def _hot_knowledge_for_tenant(self, tenant_id: str) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for document in self.documents.values():
            if document.tenant_id != tenant_id:
                continue
            hits = sum(chunk.hits for chunk in document.chunks)
            if hits:
                rows.append({"filename": document.filename, "hits": hits})
        return sorted(rows, key=lambda row: (-int(row["hits"]), str(row["filename"])))[:5]

    def _stale_knowledge_for_tenant(self, tenant_id: str) -> List[str]:
        stale: List[str] = []
        for document in self.documents.values():
            if document.tenant_id != tenant_id:
                continue
            if document.status == "failed":
                stale.append(document.filename)
        return stale

    def _excerpt(self, text: str, size: int = 120) -> str:
        text = " ".join(text.split())
        return text if len(text) <= size else text[: size - 1] + "..."


def ingest_many(
    platform: KnowledgeAssetPlatform,
    tenant_id: str,
    knowledge_base_id: str,
    documents: Iterable[tuple[str, str]],
) -> List[DocumentRecord]:
    return [
        platform.ingest_document(tenant_id, knowledge_base_id, filename, content)
        for filename, content in documents
    ]
