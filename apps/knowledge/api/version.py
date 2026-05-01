from rest_framework import serializers

from knowledge.models.knowledge import Knowledge


class KnowledgeVersionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    knowledge_id = serializers.UUIDField()
    version_number = serializers.IntegerField()
    name = serializers.CharField(max_length=256)
    description = serializers.CharField(default='', allow_blank=True)
    document_count = serializers.IntegerField(default=0)
    paragraph_count = serializers.IntegerField(default=0)
    created_by = serializers.UUIDField(allow_null=True)
    create_time = serializers.DateTimeField(read_only=True)
