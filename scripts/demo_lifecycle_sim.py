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


@dataclass
class KnowledgeBase:
    id: str
    tenant_id: str
    name: str
    owner: str
    created_at: datetime = field(default_factory=_now)


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    heading: str
    citation: str
    indexed_at: Optional[datetime] = None
    hits: int = 0


@dataclass
class DocumentRecord:
    id: str
    tenant_id: str
    knowledge_base_id: str
    filename: str
    content: str
    status: str = "uploaded"
    error: Optional[str] = None
    chunks: List[Chunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    score: int
    excerpt: str
    citation: str


@dataclass
class Answer:
    question: str
    answer: str
    hits: List[SearchHit]
    citations: List[str]
    fallback_reason: Optional[str] = None


@dataclass
class FeedbackRecord:
    id: str
    tenant_id: str
    question: str
    answer: str
    rating: int
    reason: str
    status: str = "open"
    owner: Optional[str] = None
    created_at: datetime = field(default_factory=_now)
    closed_at: Optional[datetime] = None


class KnowledgeAssetPlatform:
    """Small in-memory model used by docs, demo scripts, and baseline tests."""

    def __init__(self) -> None:
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.documents: Dict[str, DocumentRecord] = {}
        self.index: Dict[str, List[Chunk]] = {}
        self.answers: List[Answer] = []
        self.feedback: List[FeedbackRecord] = []

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

    def upload_document(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        filename: str,
        content: str,
    ) -> DocumentRecord:
        self._require_kb_access(tenant_id, knowledge_base_id)
        document = DocumentRecord(
            id=f"doc-{uuid4().hex[:8]}",
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            content=content,
        )
        self.documents[document.id] = document
        return document

    def parse_document(self, tenant_id: str, document_id: str) -> DocumentRecord:
        document = self._require_document_access(tenant_id, document_id)
        document.updated_at = _now()

        if not document.content.strip():
            return self._mark_parse_failed(document, "empty document")
        if "[PARSE_ERROR]" in document.content:
            return self._mark_parse_failed(document, "parser could not extract text layer")

        document.chunks = self._chunk_document(document)
        document.status = "parsed"
        document.error = None
        return document

    def index_document(self, tenant_id: str, document_id: str) -> DocumentRecord:
        document = self._require_document_access(tenant_id, document_id)
        self._require_kb_access(tenant_id, document.knowledge_base_id)
        if document.status != "parsed":
            raise ValueError(f"document must be parsed before indexing, got {document.status}")

        existing = [
            chunk
            for chunk in self.index[document.knowledge_base_id]
            if chunk.document_id != document.id
        ]
        for chunk in document.chunks:
            chunk.indexed_at = _now()
        self.index[document.knowledge_base_id] = existing + document.chunks
        document.status = "indexed"
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
        )
        self.answers.append(answer)
        return answer

    def search(self, tenant_id: str, knowledge_base_id: str, question: str) -> List[SearchHit]:
        self._require_kb_access(tenant_id, knowledge_base_id)
        question_terms = set(_tokenize(question))
        if not question_terms:
            return []

        scored: List[SearchHit] = []
        for chunk in self.index.get(knowledge_base_id, []):
            chunk_terms = set(_tokenize(chunk.text + " " + chunk.heading))
            score = len(question_terms & chunk_terms)
            if score >= 2:
                chunk.hits += 1
                scored.append(
                    SearchHit(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        score=score,
                        excerpt=self._excerpt(chunk.text),
                        citation=chunk.citation,
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
    ) -> FeedbackRecord:
        if not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")
        record = FeedbackRecord(
            id=f"fb-{uuid4().hex[:8]}",
            tenant_id=tenant_id,
            question=question,
            answer=answer,
            rating=rating,
            reason=reason,
        )
        self.feedback.append(record)
        return record

    def low_quality_answers(self, tenant_id: str) -> List[FeedbackRecord]:
        return [
            record
            for record in self.feedback
            if record.tenant_id == tenant_id and record.rating <= 2
        ]

    def close_feedback(self, tenant_id: str, feedback_id: str, owner: str) -> FeedbackRecord:
        for record in self.feedback:
            if record.tenant_id == tenant_id and record.id == feedback_id:
                record.status = "closed"
                record.owner = owner
                record.closed_at = _now()
                return record
        raise KeyError(feedback_id)

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

        return {
            "knowledge_hit_rate": round(hit_answers / total_answers, 4) if total_answers else 0,
            "low_quality_answer_rate": round(len(low_quality) / len(tenant_feedback), 4)
            if tenant_feedback
            else 0,
            "unanswered_questions": [
                answer.question for answer in tenant_answers if answer.fallback_reason
            ],
            "hot_knowledge": self._hot_knowledge_for_tenant(tenant_id),
            "stale_knowledge": self._stale_knowledge_for_tenant(tenant_id),
            "feedback_closure_status": {
                "total": len(tenant_feedback),
                "open": len(open_feedback),
                "closed": len(tenant_feedback) - len(open_feedback),
            },
        }

    def _mark_parse_failed(self, document: DocumentRecord, reason: str) -> DocumentRecord:
        document.status = "failed"
        document.error = reason
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
        )

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
        if not answer.hits:
            return True
        document = self.documents.get(answer.hits[0].document_id)
        return bool(document and document.tenant_id == tenant_id)

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
