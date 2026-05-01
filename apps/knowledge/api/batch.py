from rest_framework import serializers


class BatchImportSerializer(serializers.Serializer):
    knowledge_id = serializers.UUIDField()
    files = serializers.ListField(child=serializers.FileField(), max_length=100)

    def validate(self, data):
        from knowledge.models.knowledge import Knowledge
        knowledge = Knowledge.objects.filter(id=data['knowledge_id']).first()
        if knowledge and len(data['files']) > knowledge.file_count_limit:
            raise serializers.ValidationError(
                f"File count exceeds limit of {knowledge.file_count_limit}"
            )
        return data


class BatchExportSerializer(serializers.Serializer):
    knowledge_id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
