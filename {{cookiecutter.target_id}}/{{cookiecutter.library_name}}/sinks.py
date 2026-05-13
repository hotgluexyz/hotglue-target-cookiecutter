"""{{ cookiecutter.destination_name }} target sink class, which handles writing streams."""
{# Resolved sink list (empty prompt → single fallback). Scan once for record vs batch imports. #}
{% set DEFAULT_FALLBACK_SINKS = 'Fallback | record' -%}
{%- set sinks_csv = ((cookiecutter.sinks | default('', true)) | trim) or DEFAULT_FALLBACK_SINKS -%}
{%- set is_fallback_only = (sinks_csv == DEFAULT_FALLBACK_SINKS) -%}
{%- set ns = namespace(has_record=false, has_batch=false) -%}
{%- for s in sinks_csv.split(',') if s.strip() -%}
{%- set p = s.strip().split('|') -%}
{%- set m = (p[1].strip() | lower) if (p | length) > 1 else 'record' -%}
{%- if m == 'batch' -%}{%- set ns.has_batch = true -%}{%- else -%}{%- set ns.has_record = true -%}{%- endif -%}
{%- endfor -%}

from __future__ import annotations

{% if ns.has_record and ns.has_batch %}
from {{ cookiecutter.library_name }}.client import {{ cookiecutter.destination_name }}RecordSink, {{ cookiecutter.destination_name }}BatchSink
{%- elif ns.has_record %}
from {{ cookiecutter.library_name }}.client import {{ cookiecutter.destination_name }}RecordSink
{%- elif ns.has_batch %}
from {{ cookiecutter.library_name }}.client import {{ cookiecutter.destination_name }}BatchSink
{%- endif %}

{% for sink in sinks_csv.split(',') if sink.strip() %}
{%- set parts = sink.strip().split('|') -%}
{%- set stream = parts[0].strip() -%}
{%- set mode = (parts[1].strip() | lower) if (parts | length) > 1 else 'record' -%}
class {{ stream }}Sink({{ cookiecutter.destination_name }}{{ 'Batch' if mode == 'batch' else 'Record' }}Sink):
    """{{ stream }} sink implementation."""
{%- if is_fallback_only %}
    stream_name = "{{ stream }}"

    @property
    def name(self) -> str:
        return self.stream_name

    @property
    def endpoint(self) -> str:
        {% raw %}return f"/{self.stream_name}"{% endraw %}
{%- else %}
    name = "{{ stream }}"
    endpoint = "/endpoint" # TODO: Add the actual endpoint for the sink

{%- endif %}
{% endfor %}
