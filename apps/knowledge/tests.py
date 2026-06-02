from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from knowledge.models import SearchMode
from knowledge.services.asset_lifecycle_demo import MAX_UPLOAD_BYTES, KnowledgeAssetPlatform
from knowledge.vector.base_vector import normalize_for_embedding
from knowledge.vector.pg_vector import PGVector


class FakeEmbedding:
    def __init__(self):
        self.last_query = None

    def embed_query(self, text):
        self.last_query = text
        return [0.01, 0.02, 0.03]


class RejectSearchHandler:
    def support(self, search_mode):
        return False

    def handle(self, *args, **kwargs):
        raise AssertionError("RejectSearchHandler should not be selected")


class AcceptSearchHandler:
    def __init__(self, response, supported_mode=SearchMode.embedding):
        self.response = response
        self.supported_mode = supported_mode
        self.last_query_text = None
        self.last_top_number = None
        self.last_similarity = None

    def support(self, search_mode):
        return search_mode == self.supported_mode

    def handle(self, query_set, query_text, query_embedding, top_number, similarity, search_mode):
        self.last_query_text = query_text
        self.last_top_number = top_number
        self.last_similarity = similarity
        return self.response


class KnowledgeRetrievalTests(SimpleTestCase):
    def test_normalize_for_embedding_removes_emoji_and_extra_spaces(self):
        text = "hello   world 😄\nfrom\tNebulaKB"
        self.assertEqual(normalize_for_embedding(text), "hello world from NebulaKB")

    def test_pgvector_hit_test_uses_supported_handler(self):
        expected = [{"paragraph_id": "p1", "similarity": 0.91, "comprehensive_score": 0.93}]
        accept_handler = AcceptSearchHandler(response=expected)
        fake_embedding = FakeEmbedding()

        fake_queryset = MagicMock()
        fake_queryset.filter.return_value = fake_queryset
        fake_queryset.exclude.return_value = fake_queryset

        with (
            patch("knowledge.vector.pg_vector.QuerySet", return_value=fake_queryset),
            patch("knowledge.vector.pg_vector.search_handle_list", [RejectSearchHandler(), accept_handler]),
        ):
            result = PGVector().hit_test(
                "  test 😄 query  ",
                ["kb-1"],
                ["doc-1"],
                5,
                0.6,
                SearchMode.embedding,
                fake_embedding,
            )

        self.assertEqual(result, expected)
        self.assertEqual(fake_embedding.last_query, "test query")
        self.assertEqual(accept_handler.last_query_text, "test query")
        self.assertEqual(accept_handler.last_top_number, 5)
        self.assertEqual(accept_handler.last_similarity, 0.6)

    def test_pgvector_hit_test_supports_keywords_mode(self):
        expected = [{"paragraph_id": "kw-1", "similarity": 0.77}]
        keywords_handler = AcceptSearchHandler(response=expected, supported_mode=SearchMode.keywords)
        fake_embedding = FakeEmbedding()
        fake_queryset = MagicMock()
        fake_queryset.filter.return_value = fake_queryset
        fake_queryset.exclude.return_value = fake_queryset

        with (
            patch("knowledge.vector.pg_vector.QuerySet", return_value=fake_queryset),
            patch("knowledge.vector.pg_vector.search_handle_list", [keywords_handler]),
        ):
            result = PGVector().hit_test(
                "keyword query",
                ["kb-1"],
                [],
                3,
                0.55,
                SearchMode.keywords,
                fake_embedding,
            )

        self.assertEqual(result, expected)
        self.assertEqual(keywords_handler.last_query_text, "keyword query")

    def test_pgvector_hit_test_supports_blend_mode(self):
        expected = [{"paragraph_id": "blend-1", "similarity": 0.88}]
        blend_handler = AcceptSearchHandler(response=expected, supported_mode=SearchMode.blend)
        fake_embedding = FakeEmbedding()
        fake_queryset = MagicMock()
        fake_queryset.filter.return_value = fake_queryset
        fake_queryset.exclude.return_value = fake_queryset

        with (
            patch("knowledge.vector.pg_vector.QuerySet", return_value=fake_queryset),
            patch("knowledge.vector.pg_vector.search_handle_list", [blend_handler]),
        ):
            result = PGVector().hit_test(
                "blend query",
                ["kb-1"],
                [],
                3,
                0.5,
                SearchMode.blend,
                fake_embedding,
            )

        self.assertEqual(result, expected)
        self.assertEqual(blend_handler.last_query_text, "blend query")

    def test_pgvector_hit_test_returns_empty_when_no_knowledge_ids(self):
        result = PGVector().hit_test(
            "test",
            [],
            [],
            3,
            0.5,
            SearchMode.embedding,
            FakeEmbedding(),
        )
        self.assertEqual(result, [])


class KnowledgeAssetLifecycleDemoTests(SimpleTestCase):
    def setUp(self):
        self.platform = KnowledgeAssetPlatform()
        self.tenant_a = "tenant-a"
        self.tenant_b = "tenant-b"
        self.kb = self.platform.create_knowledge_base(
            tenant_id=self.tenant_a,
            knowledge_base_id="kb-service",
            name="客服政策库",
            owner="ops-a",
        )
        self.platform.create_knowledge_base(
            tenant_id=self.tenant_b,
            knowledge_base_id="kb-private",
            name="隔离知识库",
            owner="ops-b",
        )
        self.content = """
# 入库治理 SOP

## 解析失败处理

如果扫描件缺少文本层、文件损坏或格式不受支持，文档状态必须标记为 failed，负责人需要在 2 个工作日内补充 OCR 版本。

## 引用返回

问答答案必须返回引用，引用至少包含文档标题、切片编号和命中摘要。
"""

    def test_file_upload_creates_document_record(self):
        document = self.platform.upload_document(
            self.tenant_a, self.kb.id, "import-sop.md", self.content
        )

        self.assertEqual(document.status, "uploaded")
        self.assertEqual(document.tenant_id, self.tenant_a)
        self.assertEqual(document.knowledge_base_id, self.kb.id)

    def test_parse_failure_records_error(self):
        document = self.platform.upload_document(
            self.tenant_a, self.kb.id, "broken.txt", "[PARSE_ERROR]"
        )
        parsed = self.platform.parse_document(self.tenant_a, document.id)

        self.assertEqual(parsed.status, "failed")
        self.assertEqual(parsed.error, "parser could not extract text layer")
        self.assertEqual(parsed.chunks, [])

    def test_index_success_after_parse(self):
        document = self.platform.ingest_document(
            self.tenant_a, self.kb.id, "import-sop.md", self.content
        )

        self.assertEqual(document.status, "indexed")
        self.assertGreaterEqual(len(document.chunks), 2)
        self.assertTrue(all(chunk.indexed_at is not None for chunk in document.chunks))

    def test_upload_precheck_rejects_unsupported_format_and_large_file(self):
        unsupported = self.platform.validate_upload("policy.pdf", "content")
        oversized = self.platform.validate_upload("policy.md", "x" * (MAX_UPLOAD_BYTES + 1))

        self.assertFalse(unsupported.accepted)
        self.assertEqual(unsupported.reason, "unsupported file format: .pdf")
        self.assertFalse(oversized.accepted)
        self.assertIn("file exceeds", oversized.reason)

        with self.assertRaisesRegex(ValueError, "unsupported file format"):
            self.platform.upload_document(self.tenant_a, self.kb.id, "policy.pdf", "content")

    def test_document_state_machine_chunk_preview_and_citation_location(self):
        document = self.platform.ingest_document(
            self.tenant_a, self.kb.id, "import-sop.md", self.content
        )

        self.assertEqual(document.upload_progress, 100)
        self.assertEqual(document.file_format, ".md")
        self.assertEqual(document.source, "local-upload:import-sop.md")
        self.assertEqual(
            document.status_history,
            ["waiting", "uploading", "uploaded", "parsing", "parsed", "indexing", "indexed"],
        )

        preview = self.platform.chunk_preview(self.tenant_a, document.id, limit=1)
        self.assertEqual(len(preview), 1)
        self.assertTrue(preview[0]["citation"].startswith("import-sop.md#"))
        self.assertIn("import-sop.md", preview[0]["source_locator"])

        locator = self.platform.locate_citation(self.tenant_a, preview[0]["citation"])
        self.assertEqual(locator["document_id"], document.id)
        self.assertEqual(locator["source_locator"], preview[0]["source_locator"])

    def test_permission_isolation_between_tenants(self):
        self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)

        with self.assertRaises(PermissionError):
            self.platform.ask(self.tenant_b, self.kb.id, "解析失败后怎么办？")

    def test_retrieval_hit_returns_answer_with_citations(self):
        self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)

        answer = self.platform.ask(self.tenant_a, self.kb.id, "解析失败后应该如何处理？")

        self.assertIsNone(answer.fallback_reason)
        self.assertGreaterEqual(len(answer.hits), 1)
        self.assertGreaterEqual(len(answer.citations), 1)
        self.assertTrue(answer.citations[0].startswith("import-sop.md#"))
        self.assertIn("根据知识库引用", answer.answer)
        self.assertEqual(answer.knowledge_base_id, self.kb.id)
        self.assertEqual(answer.stream_state, "completed")
        self.assertIn("citations_attached", answer.stream_events)

    def test_keyword_and_vector_search_return_scores_and_source_locators(self):
        self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)

        keyword_hits = self.platform.search(
            self.tenant_a, self.kb.id, "解析失败后应该如何处理？", mode="keyword"
        )
        vector_hits = self.platform.search(
            self.tenant_a, self.kb.id, "解析失败后应该如何处理？", mode="vector"
        )

        self.assertGreaterEqual(keyword_hits[0].score, 2)
        self.assertEqual(keyword_hits[0].retrieval_mode, "keyword")
        self.assertIn("import-sop.md", keyword_hits[0].source_locator)
        self.assertGreater(vector_hits[0].score, 0)
        self.assertLessEqual(vector_hits[0].score, 1)
        self.assertEqual(vector_hits[0].retrieval_mode, "vector")

    def test_empty_result_has_fallback(self):
        self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)

        answer = self.platform.ask(self.tenant_a, self.kb.id, "火星基地餐饮报销规则是什么？")

        self.assertEqual(answer.fallback_reason, "empty_result")
        self.assertEqual(answer.citations, [])
        self.assertIn("未找到可靠知识", answer.answer)
        self.assertEqual(answer.stream_state, "completed")
        self.assertIn("fallback_returned", answer.stream_events)

    def test_feedback_record_and_low_quality_review(self):
        feedback = self.platform.submit_feedback(
            tenant_id=self.tenant_a,
            question="解析失败后应该如何处理？",
            answer="缺少 SLA 的答案",
            rating=2,
            reason="没有明确负责人和处理时限。",
        )

        low_quality = self.platform.low_quality_answers(self.tenant_a)
        self.assertEqual([record.id for record in low_quality], [feedback.id])

        closed = self.platform.close_feedback(
            self.tenant_a, feedback.id, owner="knowledge-ops"
        )
        self.assertEqual(closed.status, "closed")
        self.assertEqual(closed.owner, "knowledge-ops")

    def test_thumbs_votes_create_feedback_and_dashboard_first_screen(self):
        document = self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)
        answer = self.platform.ask(self.tenant_a, self.kb.id, "解析失败后应该如何处理？")
        thumbs_up = self.platform.vote_answer(
            self.tenant_a,
            self.kb.id,
            "点赞是否可用？",
            "答案可接受",
            vote="thumbs_up",
            citations=[document.chunks[0].citation],
        )
        thumbs_down = self.platform.vote_answer(
            self.tenant_a,
            self.kb.id,
            answer.question,
            answer.answer,
            vote="thumbs_down",
            citations=answer.citations,
            reason="答案缺少负责人和 SLA。",
            owner="ops-a",
        )

        self.assertEqual(thumbs_up.rating, 5)
        self.assertIsNone(thumbs_up.governance_task_id)
        self.assertEqual(thumbs_down.rating, 1)
        self.assertIsNotNone(thumbs_down.governance_task_id)

        dashboard = self.platform.operations_dashboard_first_screen(self.tenant_a)
        self.assertIn("summary_cards", dashboard)
        self.assertIn("queues", dashboard)
        self.assertEqual(dashboard["summary_cards"]["pending_feedback_count"], 2)
        self.assertEqual(dashboard["queues"]["governance_tasks"][0]["owner"], "ops-a")
        self.assertEqual(dashboard["knowledge_bases"][0]["knowledge_base_id"], self.kb.id)

    def test_negative_feedback_creates_governance_task_and_health_metrics(self):
        self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)
        answer = self.platform.ask(self.tenant_a, self.kb.id, "解析失败后应该如何处理？")
        self.platform.ask(self.tenant_a, self.kb.id, "火星基地餐饮报销规则是什么？")

        feedback = self.platform.submit_feedback(
            tenant_id=self.tenant_a,
            knowledge_base_id=self.kb.id,
            question=answer.question,
            answer=answer.answer,
            citations=answer.citations,
            rating=2,
            reason="答案缺少负责人和 SLA。",
            owner="ops-a",
        )

        tasks = self.platform.list_governance_tasks(self.tenant_a, knowledge_base_id=self.kb.id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(feedback.governance_task_id, tasks[0].id)
        self.assertEqual(tasks[0].question, answer.question)
        self.assertEqual(tasks[0].answer, answer.answer)
        self.assertEqual(tasks[0].citations, answer.citations)
        self.assertEqual(tasks[0].reason, "答案缺少负责人和 SLA。")
        self.assertEqual(tasks[0].owner, "ops-a")
        self.assertEqual(tasks[0].status, "open")

        metrics = self.platform.metrics(self.tenant_a)
        self.assertEqual(metrics["knowledge_hit_rate"], 0.5)
        self.assertEqual(metrics["low_quality_answer_rate"], 1)
        self.assertEqual(metrics["unanswered_question_count"], 1)
        self.assertEqual(metrics["pending_feedback_count"], 1)
        self.assertEqual(metrics["stale_knowledge_count"], 0)
        self.assertEqual(metrics["governance_tasks"][0]["id"], tasks[0].id)

        by_kb = self.platform.metrics_by_knowledge_base(self.tenant_a)
        self.assertEqual(by_kb[0]["knowledge_base_id"], self.kb.id)
        self.assertLess(by_kb[0]["health_score"], 100)
        self.assertEqual(by_kb[0]["pending_feedback_count"], 1)

    def test_knowledge_base_health_tracks_failed_docs_feedback_and_unanswered_questions(self):
        self.platform.ingest_document(self.tenant_a, self.kb.id, "import-sop.md", self.content)
        failed = self.platform.ingest_document(self.tenant_a, self.kb.id, "broken.txt", "[PARSE_ERROR]")
        self.platform.ask(self.tenant_a, self.kb.id, "火星基地餐饮报销规则是什么？")
        self.platform.submit_feedback(
            tenant_id=self.tenant_a,
            knowledge_base_id=self.kb.id,
            question="解析失败后应该如何处理？",
            answer="缺少引用",
            citations=[],
            rating=2,
            reason="引用缺失",
        )

        health = self.platform.knowledge_base_health(self.tenant_a, self.kb.id)
        self.assertEqual(failed.failure_summary, "broken.txt: parser could not extract text layer")
        self.assertEqual(health["document_count"], 2)
        self.assertEqual(health["indexed_document_count"], 1)
        self.assertEqual(health["failed_document_count"], 1)
        self.assertEqual(health["pending_feedback_count"], 1)
        self.assertEqual(health["unanswered_question_count"], 1)
        self.assertEqual(health["health_score"], 55)

    def test_low_quality_answers_supports_knowledge_reason_and_status_filters(self):
        other_kb = self.platform.create_knowledge_base(
            tenant_id=self.tenant_a,
            knowledge_base_id="kb-billing",
            name="计费政策库",
            owner="billing-ops",
        )
        first = self.platform.submit_feedback(
            tenant_id=self.tenant_a,
            knowledge_base_id=self.kb.id,
            question="解析失败后应该如何处理？",
            answer="缺少负责人",
            citations=["import-sop.md#1"],
            rating=2,
            reason="负责人缺失",
        )
        self.platform.submit_feedback(
            tenant_id=self.tenant_a,
            knowledge_base_id=other_kb.id,
            question="计费规则是什么？",
            answer="缺少引用",
            citations=[],
            rating=1,
            reason="引用缺失",
        )
        self.platform.close_feedback(self.tenant_a, first.id, owner="ops-a")

        self.assertEqual(
            [record.id for record in self.platform.low_quality_answers(self.tenant_a, knowledge_base_id=self.kb.id)],
            [first.id],
        )
        self.assertEqual(
            [record.reason for record in self.platform.low_quality_answers(self.tenant_a, reason="引用")],
            ["引用缺失"],
        )
        self.assertEqual(
            [record.id for record in self.platform.low_quality_answers(self.tenant_a, status="closed")],
            [first.id],
        )
