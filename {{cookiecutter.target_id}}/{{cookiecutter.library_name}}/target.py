"""{{ cookiecutter.destination_name }} target class."""
{% set DEFAULT_FALLBACK_SINKS = 'Fallback | record' -%}
{%- set sinks_csv = ((cookiecutter.sinks | default('', true)) | trim) or DEFAULT_FALLBACK_SINKS -%}
{%- set is_fallback_only = (sinks_csv == DEFAULT_FALLBACK_SINKS) -%}
{%- set ns = namespace(has_record=false, has_batch=false) -%}
{%- for s in sinks_csv.split(',') if s.strip() -%}
{%- set p = s.strip().split('|') -%}
{%- set m = (p[1].strip() | lower) if (p | length) > 1 else 'record' -%}
{%- if m == 'batch' -%}{%- set ns.has_batch = true -%}{%- else -%}{%- set ns.has_record = true -%}{%- endif -%}
{%- endfor -%}

{% set auth_m = cookiecutter.auth_method | default('Basic Auth', true) %}

from __future__ import annotations

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.target_sdk.target import TargetHotglue
{% if auth_m == "OAuth2" %}from {{ cookiecutter.library_name }}.auth import {{ cookiecutter.destination_name }}Authenticator
{% endif %}{%- if ns.has_record and ns.has_batch %}from {{ cookiecutter.library_name }}.client import {{ cookiecutter.destination_name }}RecordSink, {{ cookiecutter.destination_name }}BatchSink
{% elif ns.has_record and not is_fallback_only %}from {{ cookiecutter.library_name }}.client import {{ cookiecutter.destination_name }}RecordSink
{% elif ns.has_batch %}from {{ cookiecutter.library_name }}.client import {{ cookiecutter.destination_name }}BatchSink
{% endif %}
{%- if is_fallback_only %}from {{ cookiecutter.library_name }}.sinks import FallbackSink
{%- elif not is_fallback_only %}from {{ cookiecutter.library_name }}.sinks import {% for s in sinks_csv.split(',') if s.strip() -%}
{{- s.strip().split('|')[0].strip() }}Sink{% if not loop.last %}, {% endif %}
{%- endfor %}
{% endif %}

class Target{{ cookiecutter.destination_name }}(TargetHotglue):
    """Target for {{ cookiecutter.destination_name }}."""

    name = "{{ cookiecutter.target_id }}"
    SINK_TYPES = [{% if not is_fallback_only %}{% for sink in sinks_csv.split(',') if sink.strip() %}{{ sink.strip().split('|')[0].strip() }}Sink{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}]

    config_jsonschema = th.PropertiesList(
        {%- if auth_m == "OAuth2" %}
        th.Property(
            "client_id",
            th.StringType(),
            required=True,
            description="Client identifier for the token endpoint",
        ),
        th.Property(
            "client_secret",
            th.StringType(),
            required=True,
            description="Client secret for the token endpoint",
        ),
        th.Property(
            "refresh_token",
            th.StringType,
            required=True,
            description="Refresh token used to obtain new access tokens",
        ),
        th.Property(
            "access_token",
            th.StringType,
            required=False,
            description="Current access token (usually populated after refresh)",
        ),
        th.Property(
            "expires_in",
            th.IntegerType,
            required=False,
            description="Epoch seconds when the access token expires (updated on refresh)",
        ),
        {%- elif auth_m == "Basic Auth" %}
        th.Property(
            "username",
            th.StringType(),
            required=True,
            description="Username for HTTP Basic authentication",
        ),
        th.Property(
            "password",
            th.StringType(),
            required=True,
            description="Password for HTTP Basic authentication",
        ),
        {%- elif auth_m == "API Key" %}
        th.Property(
            "access_key",
            th.StringType(),
            required=True,
            description="Secret value sent as the API key (see access_key_header_name)",
        ),
        th.Property(
            "access_key_header_name",
            th.StringType,
            required=False,
            description="HTTP header name for the API key (default: x-api-key)",
        ),
        th.Property(
            "access_key_prefix",
            th.StringType,
            required=False,
            description="Optional prefix before the key value in the header (e.g. 'Bearer ')",
        ),
        {%- elif auth_m == "Bearer Token" %}
        th.Property(
            "access_key",
            th.StringType,
            required=True,
            description="Bearer token sent with API requests",
        ),
        {%- endif %}
    ).to_dict(){% if is_fallback_only %}

    default_sink_class = FallbackSink{% endif %}{% if auth_m == "OAuth2" %}

    @classmethod
    def access_token_support(cls, connector=None):
        return (
            {{ cookiecutter.destination_name }}Authenticator,
            "https://example.com/oauth2/token"  # TODO: Add the actual token endpoint URL
        ){% endif %}

if __name__ == "__main__":
    Target{{ cookiecutter.destination_name }}.cli()
