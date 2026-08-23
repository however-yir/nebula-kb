from unittest.mock import MagicMock, patch

from django.core.exceptions import FieldError
from django.db.models import QuerySet
from django.test import SimpleTestCase

from knowledge.models import Problem, ProblemParagraphMapping, SearchMode
from knowledge.services.asset_admin_completion import KnowledgeAssetAdminCompletion
from knowledge.services.asset_lifecycle_demo import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_UPLOAD_MIME_TYPES,
    KnowledgeAssetPlatform,
)
from knowledge.vector.base_vector import normalize_for_embedding
from knowledge.vector.pg_vector import PGVector, invalidate_retrieval_cache


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


class RetrievalCacheKeyTests(SimpleTestCase):
    """H1: 检索缓存键必须覆盖全部检索范围维度, 且对完整向量做哈希"""

    def _base_kwargs(self):
        return dict(
            knowledge_id_list=["k-1"],
            document_id_list=None,
            exclude_document_id_list=None,
            exclude_paragraph_list=None,
            is_active=True,
            top_n=5,
            similarity=0.6,
            search_mode=SearchMode.embedding,
        )

    def test_cache_key_includes_scope_dimensions(self):
        base = self._base_kwargs()
        key = PGVector._get_cache_key(query_embedding=[0.1, 0.2, 0.3], **base)
        for changed in (
            {"document_id_list": ["d-1"]},
            {"exclude_document_id_list": ["d-2"]},
            {"exclude_paragraph_list": ["p-1"]},
            {"is_active": False},
        ):
            with self.subTest(**changed):
                self.assertNotEqual(key, PGVector._get_cache_key(query_embedding=[0.1, 0.2, 0.3],
                                                                 **{**base, **changed}))

    def test_cache_key_hashes_full_embedding(self):
        base = self._base_kwargs()
        # 前 5 维相同但后续维度不同的向量必须产生不同的键
        self.assertNotEqual(
            PGVector._get_cache_key(query_embedding=[0.1, 0.2, 0.3, 0.4, 0.5], **base),
            PGVector._get_cache_key(query_embedding=[0.1, 0.2, 0.3, 0.4, 0.9], **base),
        )

    def test_cache_key_carries_knowledge_dimension_for_invalidation(self):
        key = PGVector._get_cache_key(
            query_embedding=[0.1],
            knowledge_id_list=["k-2", "k-1"],
            document_id_list=None,
            exclude_document_id_list=None,
            exclude_paragraph_list=None,
            is_active=True,
            top_n=5,
            similarity=0.6,
            search_mode=SearchMode.embedding,
        )
        self.assertTrue(key.startswith(f"{PGVector.RETRIEVAL_CACHE_PREFIX}:kb=k-1,k-2:"))

    def test_invalidate_retrieval_cache_skips_non_redis_backends(self):
        # LocMemCache 等后端没有原生 client, 失效应静默跳过而不是抛错
        invalidate_retrieval_cache(["k-1"])

    def test_invalidate_retrieval_cache_deletes_only_matching_knowledge_keys(self):
        class StubRedisClient:
            def __init__(self, keys):
                self.keys = list(keys)
                self.deleted = []

            def scan_iter(self, match=None, count=None):
                import fnmatch
                return (k for k in self.keys
                        if fnmatch.fnmatch(k.decode() if isinstance(k, bytes) else k, match))

            def delete(self, *keys):
                self.deleted.extend(keys)

        stub = StubRedisClient([
            ':1:nebula:retrieval:kb=k-1:aaaa',            # hit
            ':1:nebula:retrieval:kb=k-1,k-2:bbbb',        # hit (multi knowledge)
            ':1:nebula:retrieval:kb=k-3:cccc',            # miss
            ':1:WORKSPACE:LIST:unrelated',                # miss
            b':1:nebula:retrieval:kb=k-2:dddd',           # miss (bytes key)
        ])
        with patch('django.core.cache.cache') as cache_mock:
            cache_mock.client.get_client.return_value = stub
            invalidate_retrieval_cache(['k-1'])
        self.assertEqual(stub.deleted, [':1:nebula:retrieval:kb=k-1:aaaa',
                                        ':1:nebula:retrieval:kb=k-1,k-2:bbbb'])


class ParagraphEditProblemTests(SimpleTestCase):
    """H2: 段落编辑 problem_list 必须走 problem_paragraph_mapping, Problem 模型没有段落/文档字段"""

    def test_problem_model_has_no_paragraph_or_document_field(self):
        field_names = {field.name for field in Problem._meta.get_fields()}
        self.assertNotIn("paragraph_id", field_names)
        self.assertNotIn("document_id", field_names)
        self.assertIn("paragraph", {field.name for field in ProblemParagraphMapping._meta.get_fields()})
        self.assertIn("problem", {field.name for field in ProblemParagraphMapping._meta.get_fields()})

    def test_query_problem_via_mapping_does_not_raise_field_error(self):
        # 旧实现 QuerySet(Problem).filter(paragraph_id=...) 直接抛 FieldError
        paragraph_id = "00000000-0000-0000-0000-000000000000"
        with self.assertRaises(FieldError):
            QuerySet(Problem).filter(paragraph_id=paragraph_id)
        try:
            QuerySet(Problem).filter(id__in=QuerySet(ProblemParagraphMapping).filter(
                paragraph_id=paragraph_id).values_list("problem_id", flat=True))
        except FieldError:
            self.fail("querying problems via mapping raised FieldError")

    def test_problem_creation_rejects_mapping_only_kwargs(self):
        import uuid_utils.compat as uuid

        knowledge_id = uuid.uuid7()
        problem = Problem(id=uuid.uuid7(), content="q", knowledge_id=knowledge_id)
        self.assertIsNotNone(problem.id)
        # 段落/文档归属只能记录在 ProblemParagraphMapping 上
        with self.assertRaises(TypeError):
            Problem(id=uuid.uuid7(), content="q", knowledge_id=knowledge_id,
                    paragraph_id="p", document_id="d")

    def test_mapping_creation_carries_problem_document_paragraph(self):
        import uuid_utils.compat as uuid

        mapping = ProblemParagraphMapping(
            id=uuid.uuid7(), problem_id=uuid.uuid7(), document_id=uuid.uuid7(),
            paragraph_id=uuid.uuid7(), knowledge_id=uuid.uuid7())
        self.assertIsNotNone(mapping.id)


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
        self.assertEqual(document.content_type, "text/markdown")

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
        bad_mime = self.platform.validate_upload("policy.md", "content", "application/pdf")

        self.assertFalse(unsupported.accepted)
        self.assertEqual(unsupported.reason, "unsupported file format: .pdf")
        self.assertFalse(oversized.accepted)
        self.assertIn("file exceeds", oversized.reason)
        self.assertFalse(bad_mime.accepted)
        self.assertEqual(bad_mime.reason, "unsupported mime type: application/pdf")
        self.assertEqual(SUPPORTED_UPLOAD_MIME_TYPES[".md"], {"text/markdown", "text/plain"})

        with self.assertRaisesRegex(ValueError, "unsupported file format"):
            self.platform.upload_document(self.tenant_a, self.kb.id, "policy.pdf", "content")
        with self.assertRaisesRegex(ValueError, "unsupported mime type"):
            self.platform.upload_document(
                self.tenant_a,
                self.kb.id,
                "policy.md",
                "content",
                content_type="application/pdf",
            )

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


class KnowledgeAssetAdminCompletionTests(SimpleTestCase):
    def setUp(self):
        self.platform = KnowledgeAssetAdminCompletion()

    def test_knowledge_base_templates_metadata_versions_and_demo_assets(self):
        self.assertIn("Create a knowledge base", self.platform.empty_state_guidance())

        accounts = self.platform.initialize_demo_accounts()
        manifest = self.platform.demo_asset_manifest()
        kb = self.platform.import_demo_knowledge_base()
        copied = self.platform.copy_knowledge_base(kb.id, "Support Copy")
        archived = self.platform.archive_knowledge_base(copied.id)

        self.assertEqual([account["role"] for account in accounts], ["admin", "operator", "viewer"])
        self.assertEqual(manifest["version"], "2026.06")
        self.assertIn("knowledge_base_list", manifest["screenshots"])
        self.assertEqual(manifest["gif_source"], "docs/assets/screenshots/demo.gif")
        self.assertEqual(kb.template_id, "support")
        self.assertEqual(archived.status, "archived")
        self.assertIn("copied_from", " ".join(copied.history))

        tags = self.platform.update_tags(kb.id, add={"refund"}, remove={"faq"})
        self.platform.update_owner(kb.id, "lead@nebulakb.local")
        self.platform.update_description(kb.id, "<p>Support policy</p>")
        self.platform.set_visibility(kb.id, "private")
        self.platform.mark_version(kb.id, "baseline")
        self.platform.favorite(kb.id, "operator")
        recent = self.platform.record_recent_visit(kb.id, "operator")
        binding = self.platform.model_binding_check(kb.id)
        embedding_change = self.platform.change_embedding_model(kb.id, "embedding-v2")
        note = self.platform.set_operational_note(kb.id, "Review quarterly.")

        self.assertIn("refund", tags)
        self.assertEqual(kb.owner, "lead@nebulakb.local")
        self.assertEqual(kb.description_html, "<p>Support policy</p>")
        self.assertEqual(kb.visibility, "private")
        self.assertEqual(kb.version, 2)
        self.assertEqual(recent, ["operator"])
        self.assertEqual(binding["status"], "ok")
        self.assertEqual(embedding_change["status"], "requires_reindex")
        self.assertEqual(note, "Review quarterly.")
        self.assertGreater(self.platform.capacity_stats(kb.id)["used_bytes"], 0)
        self.assertEqual(self.platform.delete_risk_summary(kb.id)["documents"], 1)
        self.assertEqual(self.platform.search_knowledge_bases(query="Support", tag="refund")[0].id, kb.id)
        self.assertEqual(self.platform.list_knowledge_bases(sort_by="updated_at")[0].id, kb.id)

        package = self.platform.export_knowledge_base(kb.id)
        imported = self.platform.import_knowledge_base(package, "Imported Support")
        self.assertEqual(imported.template_id, "support")
        self.assertEqual(self.platform.bulk_delete_knowledge_bases([imported.id]), [imported.id])
        self.assertGreater(self.platform.clean_demo_data(), 0)

    def test_document_resume_parse_chunk_and_retrieval_controls(self):
        kb = self.platform.create_knowledge_base(
            "Policy",
            template_id="policy",
            owner="ops",
            team="Governance",
        )
        document = self.platform.start_resumable_upload(
            kb.id,
            "policy.md",
            total_bytes=100,
            source="local-upload",
        )
        self.platform.append_upload_chunk(document.id, 40)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.platform.complete_upload(document.id, "partial")

        self.platform.append_upload_chunk(document.id, 60)
        self.platform.complete_upload(
            document.id,
            "Refund citation evidence matters. Follow-up context improves confidence. Tiny.",
        )
        parsed = self.platform.parse_document(document.id, duration_ms=88)
        self.platform.bulk_reindex([document.id])

        duplicate = self.platform.start_resumable_upload(kb.id, "policy.md", 12, "local-upload")
        self.platform.append_upload_chunk(duplicate.id, 12)
        self.platform.complete_upload(duplicate.id, "Duplicate")
        cancelled = self.platform.cancel_parse_task(duplicate.id)
        self.assertTrue(cancelled.cancelled)
        retried = self.platform.retry_failed_parse(duplicate.id, "Recovered duplicate content.")

        self.assertEqual(parsed.parse_duration_ms, 88)
        self.assertGreaterEqual(parsed.chunk_count, 3)
        self.assertEqual(parsed.vector_status, "completed")
        self.assertEqual(parsed.index_status, "indexed")
        self.assertTrue(duplicate.duplicate_of)
        self.assertEqual(retried.retry_count, 1)
        self.assertIn("upload_started", self.platform.download_parse_log(document.id))
        self.assertIn(document.id, self.platform.bulk_reparse([document.id]))
        self.assertIn(document.id, self.platform.bulk_reindex([document.id]))
        self.assertTrue(self.platform.redirect_after_upload(document.id).endswith("/chunks"))

        chunk_ids = list(self.platform.chunk_quality_scores(document.id))
        self.assertTrue(self.platform.low_quality_chunks(document.id, threshold=60))
        edited = self.platform.edit_chunk(
            chunk_ids[0],
            "Refund citation evidence matters Follow-up context matters",
        )
        split = self.platform.split_chunk(edited.id, "Follow-up")
        self.platform.batch_update_chunks([edited.id, split.id], quality_score=91)
        merged = self.platform.merge_chunks(edited.id, split.id)
        disabled = self.platform.disable_chunk(merged.id)

        self.assertGreater(edited.version, 1)
        self.assertIn("merged", " ".join(merged.history))
        self.assertFalse(disabled.enabled)
        self.assertEqual(self.platform.chunk_versions(merged.id)["version"], merged.version)

        replacement = self.platform.edit_chunk(chunk_ids[1], "Refund citation evidence remains searchable")
        hits = self.platform.search(
            "refund citation evidence",
            [kb.id],
            mode="hybrid",
            top_k=2,
            threshold=0.1,
            rerank=True,
        )
        answer = self.platform.ask_multi_knowledge(
            "refund citation evidence",
            [kb.id],
            context_enabled=True,
            answer_length="short",
        )
        exported = self.platform.export_retrieval_results(hits)

        self.assertEqual(replacement.quality_score, 85)
        self.assertLessEqual(len(hits), 2)
        self.assertGreater(hits[0]["score"], 0)
        self.assertGreater(answer["confidence"], 0)
        self.assertTrue(answer["context_enabled"])
        self.assertEqual(answer["answer_length"], "short")
        self.assertEqual(exported[0]["chunk_id"], hits[0]["chunk_id"])
