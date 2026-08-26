# coding=utf-8
"""
    @project: lzkb
    @Author：虎
    @file： pg_vector.py
    @date：2023/10/19 15:28
    @desc:
"""
import hashlib
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List

import uuid_utils.compat as uuid
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet, Value
from langchain_core.embeddings import Embeddings

from common.db.search import generate_sql_by_query_dict
from common.db.sql_execute import select_list
from common.utils.common import get_file_content
from common.utils.logger import maxkb_logger
from common.utils.ts_vecto_util import to_ts_vector, to_query
from knowledge.models import Embedding, SearchMode, SourceType
from knowledge.vector.base_vector import BaseVectorStore, normalize_for_embedding
from lzkb.conf import PROJECT_DIR


class PGVector(BaseVectorStore):

    def delete_by_source_ids(self, source_ids: List[str], source_type: str):
        if len(source_ids) == 0:
            return
        knowledge_ids = self._get_knowledge_ids_by_source_ids(source_ids, source_type)
        QuerySet(Embedding).filter(source_id__in=source_ids, source_type=source_type).delete()
        invalidate_retrieval_cache(knowledge_ids)

    def update_by_source_ids(self, source_ids: List[str], instance: Dict):
        knowledge_ids = self._get_knowledge_ids_by_source_ids(source_ids, None)
        QuerySet(Embedding).filter(source_id__in=source_ids).update(**instance)
        invalidate_retrieval_cache(knowledge_ids)

    def vector_is_create(self) -> bool:
        # 项目启动默认是创建好的 不需要再创建
        return True

    def vector_create(self):
        return True

    def _save(self, text, source_type: SourceType, knowledge_id: str, document_id: str, paragraph_id: str,
              source_id: str,
              is_active: bool,
              embedding: Embeddings):
        text = normalize_for_embedding(text)
        text_embedding = [float(x) for x in embedding.embed_query(text)]
        embedding = Embedding(
            id=uuid.uuid7(),
            knowledge_id=knowledge_id,
            document_id=document_id,
            is_active=is_active,
            paragraph_id=paragraph_id,
            source_id=source_id,
            embedding=text_embedding,
            source_type=source_type,
            search_vector=to_ts_vector(text)
        )
        embedding.save()
        return True

    def _batch_save(self, text_list: List[Dict], embedding: Embeddings, is_the_task_interrupted):
        texts = [normalize_for_embedding(row.get('text')) for row in text_list]
        embeddings = embedding.embed_documents(texts)
        embedding_list = [
            Embedding(
                id=uuid.uuid7(),
                document_id=text_list[index].get('document_id'),
                paragraph_id=text_list[index].get('paragraph_id'),
                knowledge_id=text_list[index].get('knowledge_id'),
                is_active=text_list[index].get('is_active', True),
                source_id=text_list[index].get('source_id'),
                source_type=text_list[index].get('source_type'),
                embedding=[float(x) for x in embeddings[index]],
                search_vector=SearchVector(Value(to_ts_vector(text_list[index]['text'])))
            ) for index in range(0, len(texts))]
        if not is_the_task_interrupted():
            QuerySet(Embedding).bulk_create(embedding_list) if len(embedding_list) > 0 else None
        return True

    def hit_test(self, query_text, knowledge_id_list: list[str], exclude_document_id_list: list[str], top_number: int,
                 similarity: float,
                 search_mode: SearchMode,
                 embedding: Embeddings):
        if knowledge_id_list is None or len(knowledge_id_list) == 0:
            return []
        exclude_dict = {}
        query_text = normalize_for_embedding(query_text)
        embedding_query = embedding.embed_query(query_text)
        query_set = QuerySet(Embedding).filter(knowledge_id__in=knowledge_id_list, is_active=True)
        if exclude_document_id_list is not None and len(exclude_document_id_list) > 0:
            exclude_dict.__setitem__('document_id__in', exclude_document_id_list)
        query_set = query_set.exclude(**exclude_dict)
        for search_handle in search_handle_list:
            if search_handle.support(search_mode):
                return search_handle.handle(query_set, query_text, embedding_query, top_number, similarity, search_mode)

    def query(self, query_text: str, query_embedding: List[float], knowledge_id_list: list[str],
              document_id_list: list[str],
              exclude_document_id_list: list[str],
              exclude_paragraph_list: list[str], is_active: bool, top_n: int, similarity: float,
              search_mode: SearchMode):
        from django.core.cache import cache
        from lzkb.const import CONFIG

        cache_enabled = CONFIG.get('CACHE_RETRIEVAL_ENABLED', True)
        if cache_enabled and query_embedding:
            cache_key = self._get_cache_key(knowledge_id_list, query_embedding, document_id_list,
                                            exclude_document_id_list, exclude_paragraph_list, is_active,
                                            top_n, similarity, search_mode)
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        exclude_dict = {}
        if knowledge_id_list is None or len(knowledge_id_list) == 0:
            return []
        query_set = QuerySet(Embedding).filter(knowledge_id__in=knowledge_id_list, is_active=is_active)
        if document_id_list is not None and len(document_id_list) > 0:
            query_set = query_set.filter(document_id__in=document_id_list)
        if exclude_document_id_list is not None and len(exclude_document_id_list) > 0:
            query_set = query_set.exclude(document_id__in=exclude_document_id_list)
        if exclude_paragraph_list is not None and len(exclude_paragraph_list) > 0:
            query_set = query_set.exclude(paragraph_id__in=exclude_paragraph_list)
        query_set = query_set.exclude(**exclude_dict)
        result = None
        for search_handle in search_handle_list:
            if search_handle.support(search_mode):
                result = search_handle.handle(query_set, query_text, query_embedding, top_n, similarity, search_mode)
                break

        if cache_enabled and result is not None and query_embedding:
            ttl = int(CONFIG.get('CACHE_RETRIEVAL_TTL', 300))
            cache.set(cache_key, result, timeout=ttl)
        return result

    RETRIEVAL_CACHE_PREFIX = 'nebula:retrieval'

    @staticmethod
    def _hash_query_embedding(query_embedding):
        # 对完整向量做哈希, 避免只取前几维导致的键碰撞
        embedding_bytes = json.dumps([float(x) for x in query_embedding]).encode('utf-8')
        return hashlib.sha256(embedding_bytes).hexdigest()

    @classmethod
    def _get_cache_key(cls, knowledge_id_list, query_embedding, document_id_list, exclude_document_id_list,
                       exclude_paragraph_list, is_active, top_n, similarity, search_mode):
        key_data = json.dumps({
            'k': sorted([str(k) for k in (knowledge_id_list or [])]),
            'e': cls._hash_query_embedding(query_embedding) if query_embedding else '',
            'd': sorted([str(d) for d in (document_id_list or [])]),
            'ed': sorted([str(d) for d in (exclude_document_id_list or [])]),
            'ep': sorted([str(p) for p in (exclude_paragraph_list or [])]),
            'a': bool(is_active),
            'n': top_n,
            's': similarity,
            'm': str(search_mode),
        }, sort_keys=True)
        # 键中保留 knowledge 维度, 便于按知识库批量失效
        kb_segment = ','.join(sorted([str(k) for k in (knowledge_id_list or [])]))
        digest = hashlib.sha256(key_data.encode('utf-8')).hexdigest()
        return f"{cls.RETRIEVAL_CACHE_PREFIX}:kb={kb_segment}:{digest}"

    def update_by_source_id(self, source_id: str, instance: Dict):
        QuerySet(Embedding).filter(source_id=source_id).update(**instance)

    def update_by_paragraph_id(self, paragraph_id: str, instance: Dict):
        knowledge_ids = self._get_knowledge_ids_by_paragraph_ids([paragraph_id])
        QuerySet(Embedding).filter(paragraph_id=paragraph_id).update(**instance)
        invalidate_retrieval_cache(knowledge_ids)

    def update_by_paragraph_ids(self, paragraph_ids, instance: Dict):
        if not paragraph_ids:
            return
        paragraph_ids = list(paragraph_ids)
        knowledge_ids = self._get_knowledge_ids_by_paragraph_ids(paragraph_ids)
        QuerySet(Embedding).filter(paragraph_id__in=paragraph_ids).update(**instance)
        invalidate_retrieval_cache(knowledge_ids)

    def delete_by_knowledge_id(self, knowledge_id: str):
        QuerySet(Embedding).filter(knowledge_id=knowledge_id).delete()
        invalidate_retrieval_cache([knowledge_id])

    def delete_by_knowledge_id_list(self, knowledge_id_list: List[str]):
        QuerySet(Embedding).filter(knowledge_id__in=knowledge_id_list).delete()
        invalidate_retrieval_cache(knowledge_id_list)

    def delete_by_document_id(self, document_id: str):
        knowledge_ids = self._get_knowledge_ids_by_document_ids([document_id])
        QuerySet(Embedding).filter(document_id=document_id).delete()
        invalidate_retrieval_cache(knowledge_ids)
        return True

    def delete_by_document_id_list(self, document_id_list: List[str]):
        if len(document_id_list) == 0:
            return True
        knowledge_ids = self._get_knowledge_ids_by_document_ids(document_id_list)
        result = QuerySet(Embedding).filter(document_id__in=document_id_list).delete()
        invalidate_retrieval_cache(knowledge_ids)
        return result

    def delete_by_source_id(self, source_id: str, source_type: str):
        knowledge_ids = self._get_knowledge_ids_by_source_ids([source_id], source_type)
        QuerySet(Embedding).filter(source_id=source_id, source_type=source_type).delete()
        invalidate_retrieval_cache(knowledge_ids)
        return True

    def delete_by_paragraph_id(self, paragraph_id: str):
        knowledge_ids = self._get_knowledge_ids_by_paragraph_ids([paragraph_id])
        QuerySet(Embedding).filter(paragraph_id=paragraph_id).delete()
        invalidate_retrieval_cache(knowledge_ids)

    def delete_by_paragraph_ids(self, paragraph_ids: List[str]):
        knowledge_ids = self._get_knowledge_ids_by_paragraph_ids(paragraph_ids)
        QuerySet(Embedding).filter(paragraph_id__in=paragraph_ids).delete()
        invalidate_retrieval_cache(knowledge_ids)

    @staticmethod
    def _get_knowledge_ids_by_document_ids(document_id_list):
        return set(QuerySet(Embedding).filter(document_id__in=document_id_list)
                   .values_list('knowledge_id', flat=True))

    @staticmethod
    def _get_knowledge_ids_by_paragraph_ids(paragraph_id_list):
        if paragraph_id_list is None or len(paragraph_id_list) == 0:
            return set()
        return set(QuerySet(Embedding).filter(paragraph_id__in=paragraph_id_list)
                   .values_list('knowledge_id', flat=True))

    @staticmethod
    def _get_knowledge_ids_by_source_ids(source_id_list, source_type):
        if source_id_list is None or len(source_id_list) == 0:
            return set()
        query_set = QuerySet(Embedding).filter(source_id__in=source_id_list)
        if source_type is not None:
            query_set = query_set.filter(source_type=source_type)
        return set(query_set.values_list('knowledge_id', flat=True))


class ISearch(ABC):
    @abstractmethod
    def support(self, search_mode: SearchMode):
        pass

    @abstractmethod
    def handle(self, query_set, query_text, query_embedding, top_number: int,
               similarity: float, search_mode: SearchMode):
        pass


class EmbeddingSearch(ISearch):
    def handle(self,
               query_set,
               query_text,
               query_embedding,
               top_number: int,
               similarity: float,
               search_mode: SearchMode):
        exec_sql, exec_params = generate_sql_by_query_dict({'embedding_query': query_set},
                                                           select_string=get_file_content(
                                                               os.path.join(PROJECT_DIR, "apps", "knowledge", 'sql',
                                                                            'embedding_search.sql')),
                                                           with_table_name=True)
        embedding_model = select_list(exec_sql, [
            len(query_embedding),
            json.dumps(query_embedding),
            *exec_params,
            similarity,
            top_number
        ])
        return embedding_model

    def support(self, search_mode: SearchMode):
        return search_mode.value == SearchMode.embedding.value


class KeywordsSearch(ISearch):
    def handle(self,
               query_set,
               query_text,
               query_embedding,
               top_number: int,
               similarity: float,
               search_mode: SearchMode):
        exec_sql, exec_params = generate_sql_by_query_dict({'keywords_query': query_set},
                                                           select_string=get_file_content(
                                                               os.path.join(PROJECT_DIR, "apps", "knowledge", 'sql',
                                                                            'keywords_search.sql')),
                                                           with_table_name=True)
        embedding_model = select_list(exec_sql, [
            to_query(query_text),
            *exec_params,
            similarity,
            top_number
        ])
        return embedding_model

    def support(self, search_mode: SearchMode):
        return search_mode.value == SearchMode.keywords.value


class BlendSearch(ISearch):
    def handle(self,
               query_set,
               query_text,
               query_embedding,
               top_number: int,
               similarity: float,
               search_mode: SearchMode):
        exec_sql, exec_params = generate_sql_by_query_dict({'embedding_query': query_set},
                                                           select_string=get_file_content(
                                                               os.path.join(PROJECT_DIR, "apps", "knowledge", 'sql',
                                                                            'blend_search.sql')),
                                                           with_table_name=True)
        embedding_model = select_list(exec_sql, [
            len(query_embedding),
            json.dumps(query_embedding),
            to_query(query_text),
            *exec_params, similarity,
            top_number
        ])
        return embedding_model

    def support(self, search_mode: SearchMode):
        return search_mode.value == SearchMode.blend.value


search_handle_list = [EmbeddingSearch(), KeywordsSearch(), BlendSearch()]


def invalidate_retrieval_cache(knowledge_ids):
    """
    按知识库维度失效检索结果缓存 (nebula:retrieval:kb=...:* 键结构, 见 PGVector._get_cache_key)。
    仅 django-redis 后端支持 scan; 其他后端(如测试中的 LocMemCache)静默跳过。
    """
    knowledge_id_set = {str(k) for k in (knowledge_ids or [])}
    if not knowledge_id_set:
        return
    try:
        from django.core.cache import cache
        # django_redis 的原生客户端, 其他缓存后端没有 client 属性
        client = cache.client.get_client(write=True)
        marker = f"{PGVector.RETRIEVAL_CACHE_PREFIX}:kb="
        keys_to_delete = []
        for key in client.scan_iter(match=f"*{marker}*", count=500):
            key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
            marker_index = key_str.find(marker)
            if marker_index == -1:
                continue
            kb_segment = key_str[marker_index + len(marker):].split(':', 1)[0]
            cached_knowledge_ids = {k for k in kb_segment.split(',') if k}
            if knowledge_id_set & cached_knowledge_ids:
                keys_to_delete.append(key_str)
        if keys_to_delete:
            client.delete(*keys_to_delete)
    except AttributeError:
        pass
    except Exception as e:
        # 缓存失效失败不应阻断数据删除流程
        maxkb_logger.error(f'invalidate retrieval cache failed: {e}')
