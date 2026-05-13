# {{ cookiecutter.target_id }}

`{{ cookiecutter.target_id }}` is a Singer target for **{{ cookiecutter.destination_name }}**, built with the [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK) (`TargetHotglue`, HTTP sinks, SDK authenticators).

This project was generated from the Hotglue target cookiecutter with:

| Option | Value |
|--------|--------|
| `auth_method` | `{{ cookiecutter.auth_method | default('Basic Auth', true) }}` |
| `sinks` | `{{ cookiecutter.sinks | default('Fallback | record', true) }}` |
| `base_url` | `{{ cookiecutter.base_url | default('https://myapi.com/api/v1', true) }}` |

## Project layout

| Path | Role |
|------|------|
| `{{ cookiecutter.library_name }}/target.py` | `Target{{ cookiecutter.destination_name }}` — config schema, `SINK_TYPES`, optional `default_sink_class` and `access_token_support` |
| `{{ cookiecutter.library_name }}/client.py` | `{{ cookiecutter.destination_name }}Sink` base class, `RecordSink` / `BatchSink` stubs, `authenticator` |
| `{{ cookiecutter.library_name }}/sinks.py` | Per-stream sink classes (`FallbackSink` or named `*Sink` classes) |
| `{{ cookiecutter.library_name }}/auth.py` | Present only when generated with **OAuth2** (removed by cookiecutter hook otherwise) |
| `.secrets/config.json` | Sample config matching your `auth_method` |

## Configuration

Settings are defined in `config_jsonschema` on `Target{{ cookiecutter.destination_name }}` in `{{ cookiecutter.library_name }}/target.py`.

{%- set auth_m = cookiecutter.auth_method | default('Basic Auth', true) %}
{%- if auth_m == "OAuth2" %}
For this project (**OAuth2**), config includes: `client_id`, `client_secret`, `refresh_token`, and optional `access_token` / `expires_in`.
{%- elif auth_m == "Basic Auth" %}
For this project (**Basic Auth**), config includes: `username`, `password`.
{%- elif auth_m == "Bearer Token" %}
For this project (**Bearer Token**), config includes: `access_key` (bearer token).
{%- elif auth_m == "API Key" %}
For this project (**API Key**), config includes: `access_key`, optional `access_key_header_name`, `access_key_prefix`.
{%- endif %}

Inspect the live schema:

```bash
{{ cookiecutter.target_id }} --about
{{ cookiecutter.target_id }} --about --format=markdown
```

Local secrets: edit `.secrets/config.json` (shape matches `auth_method` above).

## Authentication

| `auth_method` | Implementation |
|---------------|----------------|
| **OAuth2** | `{{ cookiecutter.destination_name }}Authenticator` in `auth.py`; `Target{{ cookiecutter.destination_name }}.access_token_support()` returns the authenticator class and token URL (replace the TODO endpoint in `target.py`). |
| **Bearer Token** | `BearerTokenAuthenticator` in `client.py` |
| **Basic Auth** | `BasicAuthenticator` with `username` / `password` |
| **API Key** | `ApiAuthenticator` with configurable header name/prefix |

HTTP calls use `base_url` on `{{ cookiecutter.destination_name }}Sink` (`{{ cookiecutter.base_url | default('https://myapi.com/api/v1', true) }}` unless you change it in `client.py`).

## Sinks

Sinks are declared at scaffold time as `StreamName | record` or `StreamName | batch`, comma-separated.

Generated with: `{{ cookiecutter.sinks | default('Fallback | record', true) }}`

{%- set DEFAULT_FALLBACK_SINKS = 'Fallback | record' -%}
{%- set sinks_csv = ((cookiecutter.sinks | default('', true)) | trim) or DEFAULT_FALLBACK_SINKS -%}
{%- if sinks_csv == DEFAULT_FALLBACK_SINKS %}
**Fallback mode:** `FallbackSink` in `sinks.py` handles any stream dynamically (`name` / `endpoint` from `stream_name`). `target.py` sets `default_sink_class = FallbackSink` and leaves `SINK_TYPES` empty.
{%- else %}
**Named sinks:** `sinks.py` defines one class per stream; `target.py` registers them in `SINK_TYPES`. Implement `endpoint` (and request logic) per sink in `sinks.py` / overrides on `client.py` bases.
{%- endif %}

Shared HTTP behavior lives in `client.py` (`{{ cookiecutter.destination_name }}RecordSink` / `{{ cookiecutter.destination_name }}BatchSink` as generated).

## Usage

```bash
{{ cookiecutter.target_id }} --version
{{ cookiecutter.target_id }} --help
tap-smoke-test | {{ cookiecutter.target_id }} --config /path/to/config.json
```

## Developer setup

Prerequisites: Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run {{ cookiecutter.target_id }} --help
tox -e lint    # ruff check + format
```

For implementation notes and conventions, see `AGENTS.md` (or `CLAUDE.md` if that was selected at generation).

## References

- [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK)
