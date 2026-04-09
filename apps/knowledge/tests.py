from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from knowledge.models import SearchMode
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
        text = "hello   world 😄\nfrom\tLZKB"
        self.assertEqual(normalize_for_embedding(text), "hello world from LZKB")

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
