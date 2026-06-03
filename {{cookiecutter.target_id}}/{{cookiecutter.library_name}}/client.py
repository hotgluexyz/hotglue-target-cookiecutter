"""HTTP client and sink base classes for {{ cookiecutter.destination_name }}."""
{% set DEFAULT_FALLBACK_SINKS = 'Fallback | record' -%}
{%- set sinks_csv = ((cookiecutter.sinks | default('', true)) | trim) or DEFAULT_FALLBACK_SINKS -%}
{%- set ns = namespace(has_record=false, has_batch=false) -%}
{%- for s in sinks_csv.split(',') if s.strip() -%}
{%- set p = s.strip().split('|') -%}
{%- set m = (p[1].strip() | lower) if (p | length) > 1 else 'record' -%}
{%- if m == 'batch' -%}{%- set ns.has_batch = true -%}{%- else -%}{%- set ns.has_record = true -%}{%- endif -%}
{%- endfor -%}

{% set auth_m = cookiecutter.auth_method | default('Basic Auth', true) %}

from __future__ import annotations

{%- if ns.has_batch %}
from abc import abstractmethod
{%- endif %}
from typing import Any

{% if auth_m == "API Key" %}
from hotglue_singer_sdk.target_sdk.auth import ApiAuthenticator
{%- elif auth_m == "Bearer Token" %}
from hotglue_singer_sdk.target_sdk.auth import BearerTokenAuthenticator
{%- elif auth_m == "Basic Auth" %}
from hotglue_singer_sdk.target_sdk.auth import BasicAuthenticator
{%- endif %}
{%- if ns.has_record and ns.has_batch %}
from hotglue_singer_sdk.target_sdk.client import HotglueBaseSink, HotglueBatchSink, HotglueSink
{%- elif ns.has_record %}
from hotglue_singer_sdk.target_sdk.client import HotglueBaseSink, HotglueSink
{%- elif ns.has_batch %}
from hotglue_singer_sdk.target_sdk.client import HotglueBaseSink, HotglueBatchSink
{%- endif %}


class {{ cookiecutter.destination_name }}Sink(HotglueBaseSink):
    """{{ cookiecutter.destination_name }} Base target sink class for sinks."""

    {%- if cookiecutter.base_url | default('', true) %}
    base_url = "{{ cookiecutter.base_url }}"
    {%- else %}
    @property
    def base_url(self) -> str:
        # TODO: set base_url here when it is dynamic or not configured above.
        return "https://example.com/api/v1"
    {%- endif %}

    {%- if auth_m in ["OAuth2", "API Key"] %}
    auth_state = {}
    {%- endif %}

    @property
    def authenticator(self) -> Any:
        {%- if auth_m == "OAuth2" %}
        authenticator, auth_endpoint = self._target.access_token_support(self._target)
        return authenticator(self._target, self.auth_state, auth_endpoint)
        {%- elif auth_m == "Basic Auth" %}
        return BasicAuthenticator(
            self._target,
            username=self.config.get("username"),
            password=self.config.get("password"),
        )
        {%- elif auth_m == "API Key" %}
        return ApiAuthenticator(
            self._target,
            self.auth_state,
            header_name=self.config.get("access_key_header_name", "x-api-key"),
            header_value_prefix=self.config.get("access_key_prefix", ""),
            config_key="access_key",
        )
        {%- elif auth_m == "Bearer Token" %}
        return BearerTokenAuthenticator(
            self._target,
        )
        {%- endif %}

{% if ns.has_record %}
class {{ cookiecutter.destination_name }}RecordSink({{ cookiecutter.destination_name }}Sink, HotglueSink):
    """{{ cookiecutter.destination_name }} Record target sink class for record sinks."""

    name = "{{ cookiecutter.destination_name }}RecordSink"

    def preprocess_record(self, record: dict, context: dict) -> dict:
        # TODO: preprocess each record if needed (SDK calls this for every record).
        return record

    def upsert_record(self, record: dict, context: dict) -> None:
        # Called for each record on all sinks unless overridden.
        state_updates = {}
        pk_field = self.key_properties[0] if self.key_properties else "id"
        pk = record.get(pk_field)
        method = "POST"
        endpoint = self.endpoint

        if pk:
            method = "PATCH"
            endpoint = f"{endpoint}{pk}"
            state_updates["updated"] = True

        response = self.request_api(method, endpoint, request_data=record)
        record_id = pk or response.json().get("id")
        return record_id, True, state_updates
{% endif %}

{% if ns.has_batch %}


class {{ cookiecutter.destination_name }}BatchSink({{ cookiecutter.destination_name }}Sink, HotglueBatchSink):
    """{{ cookiecutter.destination_name }} Batch target sink class for batch sinks."""

    name = "{{ cookiecutter.destination_name }}BatchSink"

    def process_batch_record(self, record: dict, _index: int) -> dict:
        return record

    @abstractmethod
    def make_batch_request(self, records: list[dict]) -> Any:
        # TODO: build the batch API request (SDK calls this per batch).
        method = "POST"
        endpoint = self.endpoint
        response = self.request_api(method, endpoint, request_data=records)
        return response

    def handle_batch_response(self, _response: Any) -> dict:
        """
        This method should return a dict with a key named "state_updates".
        This key should be an array of all state updates per record.
        Created ids and errors can be fetched from the response.

        e.g. succesful creation, unsucessful request, successful update
        {
            "state_updates": [
                {
                    "record_id": "123",
                    "externalId": "Source-data-id-1",
                    "success": True
                },
                {
                    "externalId": "Source-data-id-2",
                    "success": False,
                    "error": "Error message"
                },
                {
                    "id": "1234",
                    "externalId": "Source-data-id-3",
                    "success": True,
                    "is_updated": True
                }
            ]
        }

        """
        return {"state_updates": []}

    def process_batch(self, context: dict) -> None:
        # TODO: adjust batch processing or use the SDK default behavior.
        if not self.latest_state:
            self.init_state()

        raw_records = context["records"]

        records = list(
            map(lambda e: self.process_batch_record(e[1], e[0]), enumerate(raw_records))
        )

        response = self.make_batch_request(records)

        result = self.handle_batch_response(response)

        for state in result.get("state_updates", list()):
            self.update_state(state)
{% endif %}

