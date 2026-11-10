from rest_framework import serializers

from .models import Spec


class SpecPayloadSerializer(serializers.Serializer):
    """Contract the model must satisfy. Anything else is a provider error."""

    summary = serializers.CharField(max_length=2000)
    acceptance_criteria = serializers.ListField(
        child=serializers.CharField(max_length=500), min_length=1, max_length=10
    )
    implementation_steps = serializers.ListField(
        child=serializers.CharField(max_length=500), min_length=1, max_length=10
    )
    risks = serializers.ListField(child=serializers.CharField(max_length=500), max_length=10)
    out_of_scope = serializers.ListField(child=serializers.CharField(max_length=500), max_length=10)
    size = serializers.ChoiceField(choices=Spec.Size.choices)


class SpecCreateSerializer(serializers.Serializer):
    issue_url = serializers.CharField(max_length=500)


class SpecSerializer(serializers.ModelSerializer):
    published = serializers.BooleanField(read_only=True)

    class Meta:
        model = Spec
        fields = (
            "id",
            "issue_url",
            "repo",
            "issue_number",
            "issue_title",
            "summary",
            "acceptance_criteria",
            "implementation_steps",
            "risks",
            "out_of_scope",
            "size",
            "body_markdown",
            "model",
            "prompt_version",
            "latency_ms",
            "input_chars",
            "truncated",
            "published",
            "published_issue_url",
            "published_issue_number",
            "created_at",
        )
        read_only_fields = fields


class SpecConfigSerializer(serializers.Serializer):
    ai_enabled = serializers.BooleanField()
    publish_enabled = serializers.BooleanField()
    model = serializers.CharField()
    prompt_version = serializers.CharField()
    max_input_chars = serializers.IntegerField()
