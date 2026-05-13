# AGENTS.md - AI Agent Development Guide for {{ cookiecutter.target_id }}

{% set DEFAULT_FALLBACK_SINKS = 'Fallback | record' %}
{% set sinks_csv = ((cookiecutter.sinks | default('', true)) | trim) or DEFAULT_FALLBACK_SINKS %}
{% set auth_m = cookiecutter.auth_method | default('Basic Auth', true) %}
{% set base_u = cookiecutter.base_url | default('https://myapi.com/api/v1', true) %}

This document provides guidance for AI coding agents and developers working on this Singer target.

## Project Overview

- **Project Type**: Singer Target (Hotglue Singer SDK / `TargetHotglue`)
- **Destination**: {{ cookiecutter.destination_name }}
- **Sinks**: {{ sinks_csv }} (each entry: `SinkName | record` or `SinkName | batch`)
- **Auth (at scaffold time)**: {{ auth_m }}
- **Base URL default**: {{ base_u }}
- **Framework**: [Hotglue Singer SDK](https://github.com/hotgluexyz/hotglue-singer-sdk)

## Architecture

This target follows the Singer specification and loads data into **{{ cookiecutter.destination_name }}** using **`TargetHotglue`** and HTTP sink classes from **`hotglue_singer_sdk.target_sdk`**.

### Key components

1. **`{{ cookiecutter.library_name }}/target.py`** — `Target{{ cookiecutter.destination_name }}`: `name`, `SINK_TYPES`, `config_jsonschema`, `default_sink_class`{% if auth_m == "OAuth2" %}, and `access_token_support` for OAuth2{% endif %}.
1. **`{{ cookiecutter.library_name }}/client.py`** — `{{ cookiecutter.destination_name }}Sink` (shared `base_url`, `authenticator`), plus record/batch sink bases used by `sinks.py`.
1. **`{{ cookiecutter.library_name }}/sinks.py`** — One sink class per stream from the scaffolded `sinks` list.
1. **`{{ cookiecutter.library_name }}/auth.py`** — Present **only when `auth_method` is OAuth2** (otherwise removed by `hooks/post_gen_project.py` after generation). Defines `{{ cookiecutter.destination_name }}Authenticator`.
1. **`hooks/post_gen_project.py`** (in the **cookiecutter template repo**, not always copied into generated projects as source) — Normalizes license files, optional `.vscode` removal, `auth.py` deletion for non-OAuth2, and renames or drops `AGENTS.md` per `include_agent_instructions`.

### Authentication (`{{ auth_m }}`)

| `auth_method` | Where it lives |
|---------------|----------------|
| **OAuth2** | `auth.py`: `{{ cookiecutter.destination_name }}Authenticator` (refresh token). `target.py`: `access_token_support` returns that class and the token endpoint (replace the TODO URL). `client.py`: builds the authenticator via `access_token_support`. |
| **Bearer Token** | `client.py`: `BearerTokenAuthenticator`. |
| **Basic Auth** | `client.py`: `BasicAuthenticator` with `username` / `password` from config — keep `config_jsonschema` and `.secrets/config.json` aligned with real keys. |
| **API Key** | `client.py`: `ApiAuthenticator` (`access_key`, optional `access_key_header_name`, `access_key_prefix`). |

Sample secrets for local runs: **`.secrets/config.json`** (keys align with `auth_method` and `config_jsonschema` in `target.py`: OAuth2, Basic Auth, Bearer `access_token`, or API key fields).

## Development Guidelines for AI Agents

### Understanding Singer Target Concepts

Before making changes, ensure you understand these concepts:

- **Records**: Individual data items received from taps
- **Schemas**: JSON Schema definitions describing record structure
- **State**: Bookmark information passed through from taps
- **Batching**: Grouping records for efficient loading
- **MAX_SIZE**: Maximum records per batch

### Sinks and serialization

Sink list (same as in **Project overview**): **{{ sinks_csv }}**. Implement stream-specific classes in `sinks.py`; shared HTTP and `authenticator` live in `client.py`.

### Implementing a Sink

{% if "record" in sinks_csv %}
#### Record sinks (`| record`)

Records are handled one at a time through `{{ cookiecutter.destination_name }}RecordSink` in `client.py`. Stream-specific subclasses in `sinks.py` inherit that base and override hooks as needed.

**Flow:**

```mermaid
flowchart LR
    A[Singer RECORD] --> B[preprocess_record]
    B --> C[upsert_record]
    C --> D[Destination API]
```

**Transformation vs. load:** Do **not** reshape the payload inside `upsert_record`. `preprocess_record` is defined on the parent record sink class — override it in your **sink subclass** in `sinks.py` to transform the record (field renames, types, nesting) before `upsert_record` runs.

`upsert_record` should only perform the HTTP write using the already-transformed `record` (method, endpoint, request body). The scaffold in `client.py` shows a typical POST/PATCH pattern; override in a stream sink only when that stream’s API contract differs.

```python
# {{ cookiecutter.library_name }}/sinks.py
class ContactsSink({{ cookiecutter.destination_name }}RecordSink):
  name = "Contacts"

  def preprocess_record(self, record: dict, context: dict) -> dict:
    # Shape payload for the destination API before upsert_record runs.
    return {
      "first_name": record.get("firstName"),
      "last_name": record.get("lastName"),
      "email": record.get("email"),
    }

  # Optional: override upsert_record only for stream-specific HTTP behavior.
  # def upsert_record(self, record: dict, context: dict) -> None:
  #     ...
```

**Error handling and retries:** Raise SDK retryable errors for transient failures (timeouts, 429, 5xx). Use fatal errors for auth or schema issues. Let the SDK handle backoff where configured.

{% endif %}
{% if "batch" in sinks_csv %}
#### Batch sinks (`| batch`)

Batch sinks group records (up to `max_size`) before a single API call. Per-record transformation uses **`process_batch_record`**, not `preprocess_record` (that hook is for record sinks only). See **Batching Logic** below.

{% endif %}

### Batching Logic

{% if "batch" in sinks_csv %}
Batch sinks extend `{{ cookiecutter.destination_name }}BatchSink` in `client.py`. Records accumulate until `max_size` (default often 10000) or the stream ends, then `process_batch` runs.

**`max_size` guidance:**

- Too small: excess API calls and lower throughput.
- Too large: memory pressure, timeouts, and harder partial-failure handling.
- Start around 1000–5000 and tune from record size and API limits.

**Flow:**

```mermaid
flowchart LR
    A[context records] --> B[process_batch_record per index]
    B --> C[make_batch_request]
    C --> D[Destination API]
    D --> E[handle_batch_response]
    E --> F[update_state per record]
```

1. Each raw row is passed through **`process_batch_record(record, index)`** in your sink subclass — override this to map Singer fields to the bulk payload shape.
2. **`make_batch_request(records)`** sends the batch (override when the endpoint or envelope differs).
3. **`handle_batch_response(response)`** is **required** on every batch sink. It parses the API response and returns `{"state_updates": [...]}` — one state dict per input record indicating success or failure (and optional `id`, `error`, `is_updated`, etc.). The base stub in `client.py` returns an empty list; **you must implement this** for real syncs.

**Per-record transformation (`process_batch_record`):**

```python
# {{ cookiecutter.library_name }}/sinks.py
class OrdersSink({{ cookiecutter.destination_name }}BatchSink):
  name = "Orders"

  def process_batch_record(self, record: dict, index: int) -> dict:
    return {
      "line_id": record.get("id"),
      "qty": record.get("quantity"),
      "sku": record.get("sku"),
    }
```

**`handle_batch_response` — required; shape depends on the API**

Return format (SDK contract):

```python
{"state_updates": [
    {"externalId": "...", "success": True, "id": "dest-id"},
    {"externalId": "...", "success": False, "error": "reason"},
]}
```

**Pattern 1 — API returns a parallel `results` list (same order as request):**

```python
def handle_batch_response(self, response) -> dict:
    body = response.json()
    states = []
    for item, result in zip(self._current_batch_external_ids, body["results"]):
        states.append({
            "externalId": item,
            "success": result.get("status") == "ok",
            "id": result.get("id"),
            "error": result.get("message"),
        })
    return {"state_updates": states}
```

**Pattern 2 — API returns only created IDs in order (implicit success):**

```python
def handle_batch_response(self, response) -> dict:
    ids = response.json().get("created_ids", [])
    states = []
    for external_id, dest_id in zip(self._current_batch_external_ids, ids):
        states.append({"externalId": external_id, "success": True, "id": dest_id})
    # Mark any trailing records without a matching id as failed
    for external_id in self._current_batch_external_ids[len(ids):]:
        states.append({"externalId": external_id, "success": False, "error": "No id returned"})
    return {"state_updates": states}
```

**Pattern 3 — API returns error indices or a partial summary:**

```python
def handle_batch_response(self, response) -> dict:
    body = response.json()
    failed_indexes = {e["index"] for e in body.get("errors", [])}
    states = []
    for index, external_id in enumerate(self._current_batch_external_ids):
        if index in failed_indexes:
            err = next(e for e in body["errors"] if e["index"] == index)
            states.append({"externalId": external_id, "success": False, "error": err["message"]})
        else:
            states.append({"externalId": external_id, "success": True})
    return {"state_updates": states}
```

Store correlation data (e.g. `externalId` per row) in `make_batch_request` or `process_batch` if the response does not echo source keys.

**Error handling and retries:** Treat the whole batch request as retryable on transient HTTP failures. Use `handle_batch_response` to mark per-record failures when the API returns 200 with partial errors. Do not swallow per-record errors — every row needs a `state_updates` entry.

{% else %}
This project was generated without batch sinks. To add batching, extend the cookiecutter `sinks` prompt with entries such as `Orders | batch` and implement `{{ cookiecutter.destination_name }}BatchSink` subclasses in `sinks.py`.
{% endif %}

### Cookiecutter context (this repo)

These values were set at scaffold time. In the **cookiecutter template** they appear as Jinja placeholders such as {% raw %}{{ cookiecutter.destination_name }}{% endraw %} (one per key in `cookiecutter.json`). In this generated document, file paths mostly show the resolved values.

- **`destination_name`** / **`target_id`** / **`library_name`** — Names and import path for the Python package.
- **`sinks`** — Comma-separated `Name | record` or `Name | batch` list; drives generated sink classes, `SINK_TYPES` (sink class objects), and `sinks.py`.
- **`auth_method`** — One of: Bearer Token, Basic Auth, API Key, OAuth2.
- **`base_url`** — Default API base URL in `client.py` (or override with the property stub when empty).
- **`license`** / **`include_agent_instructions`** — Handled in `post_gen_project.py` (license filenames, `AGENTS.md` vs `CLAUDE.md` vs none).

When editing the **template** upstream, mirror changes in `cookiecutter.json`, `hooks/post_gen_project.py`, and the Jinja under `{{cookiecutter.target_id}}/`.

### Common Tasks

#### Modifying Data Loading Logic

1. Override sink methods in `{{ cookiecutter.library_name }}/sinks.py`
1. Record sinks: transform in `preprocess_record`; batch sinks: transform in `process_batch_record`
1. Handle destination-specific formatting
1. Implement error handling and retries

#### Adding Configuration Options

Define new config properties in target class:

```python
from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

class Target{{ cookiecutter.destination_name }}(TargetHotglue):
    config_jsonschema = th.PropertiesList(
        th.Property("api_url", th.StringType, required=True),
        th.Property("api_key", th.StringType, required=True),
        th.Property("timeout", th.IntegerType, default=300),
    ).to_dict()
```

Configuration best practices:

- Provide sensible defaults
- Validate in `__init__`
- Document all options in README

#### Connection Management

For API/HTTP targets:

```python
# Use requests.Session for connection reuse
import requests

self.session = requests.Session()
self.session.headers.update({"Authorization": f"Bearer {api_key}"})
```

Implement retry logic for transient failures.

#### Error Handling

Implement robust error handling:

```python
try:
    # Load data
    result = self.load_data(records)
except RetryableError as e:
    # SDK will retry
    raise e
except FatalError as e:
    # Log and fail the sync
    self.logger.error(f"Fatal error: {e}")
    raise e
```

Types of errors:

- **Retryable**: Network issues, rate limits, temporary failures
- **Fatal**: Authentication errors, invalid data, configuration issues

#### Type Mapping



```python
def preprocess_record(self, record: dict, context: dict) -> dict:
    """Convert types for destination (record sinks only)."""
    if "timestamp" in record:
        record = {**record, "timestamp": parse_datetime(record["timestamp"])}
    return record
```


### Testing

Test your target implementation:

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Test with sample data
cat sample_data.singer | {{ cookiecutter.target_id }} --config config.json

# Test with a tap
tap-something --config tap_config.json | {{ cookiecutter.target_id }} --config config.json
```

Create test fixtures:

```python
# tests/test_core.py
def test_target_loads_data():
    with open("tests/fixtures/input.singer") as f:
        lines = f.readlines()

    # Process lines
    # Verify data loaded correctly
```

### Performance Optimization

1. **Batching**: Use appropriate batch sizes

   - Too small: Many API calls, slow
   - Too large: Memory issues, timeouts
   - Start with 1000-5000, adjust based on record size

1. **Parallel Processing**: For multi-table targets

   - SDK handles streams in sequence by default
   - Consider async operations within batches

1. **Connection Pooling**: Reuse connections

   - Use `requests.Session` for HTTP
   - Connection pools for databases

1. **Memory Management**:

   - Don't accumulate records beyond batch size
   - Stream large files rather than loading into memory
   - Use generators where possible

### Schema Handling

For schema-aware targets:

- Validate records against schema
- Handle schema evolution
- Map nested objects appropriately
- Consider denormalization for flat destinations

### State Management

Targets receive and forward state:

- Don't modify state in targets
- Emit state messages as received
- State used for tap bookmarking

```python
def process_state_message(self, message_dict: dict) -> None:
    """Handle state message."""
    super().process_state_message(message_dict)
    # Optional: Checkpoint or log state
```

### Keeping configuration in sync

`config_jsonschema` in `target.py` is the source of truth for target settings. Keep related files aligned so local runs and documentation stay accurate.

**When to sync:**

- Adding new configuration properties to the target
- Removing or renaming existing properties
- Changing property types, defaults, or descriptions
- Marking properties as required or secret

**How to sync:**

1. Update `config_jsonschema` in `{{ cookiecutter.library_name }}/target.py`
1. Update `.secrets/config.json` with example values for the chosen `auth_method`
1. Update `.env.example` if you use environment-variable overrides

Example - adding a new `batch_size` setting:

```python
# {{ cookiecutter.library_name }}/target.py
config_jsonschema = th.PropertiesList(
    th.Property("api_url", th.StringType, required=True),
    th.Property("api_key", th.StringType, required=True, secret=True),
    th.Property("batch_size", th.IntegerType, default=1000),  # New setting
).to_dict()
```

```json
// .secrets/config.json (add matching keys)
{
  "api_url": "https://api.example.com",
  "api_key": "your_api_key_here",
  "batch_size": 1000
}
```

```bash
# .env.example uses the target_id-derived prefix (see that file for the exact prefix)
{{ cookiecutter.target_id.upper().replace('-', '_') }}_API_URL=https://api.example.com
{{ cookiecutter.target_id.upper().replace('-', '_') }}_API_KEY=your_api_key_here
{{ cookiecutter.target_id.upper().replace('-', '_') }}_BATCH_SIZE=1000  # New setting
```

**Best practices:**

- Update `target.py`, `.secrets/config.json`, and `.env.example` in the same commit when config changes
- Use the same default values in all locations
- Keep descriptions consistent between `config_jsonschema` and README

### Common Pitfalls

1. **Memory Leaks**: Clear batch data after processing
1. **Connection Limits**: Close connections properly
1. **Partial Failures**: Handle failed records in batch
1. **Schema Changes**: Handle additive schema changes
1. **Rate Limiting**: Implement backoff and retry
1. **Authentication**: Refresh tokens before expiry
1. **Timezone Issues**: Use UTC consistently

### SDK resources

- [Hotglue Singer SDK](https://github.com/hotgluexyz/hotglue-singer-sdk) (this target’s runtime)
- [Singer specification](https://github.com/singer-io/getting-started/blob/master/SPEC.md)

### Best Practices

1. **Logging**: Use structured logging with `self.logger`
1. **Idempotency**: Handle duplicate records gracefully
1. **Transactions**: Use transactions for consistency
1. **Validation**: Validate data before loading
1. **Documentation**: Update README with config options
1. **Type Safety**: Use type hints
1. **Testing**: Test with various data types and edge cases
1. **Error Messages**: Provide actionable error information

## File Structure

```
{{ cookiecutter.target_id }}/
├── {{ cookiecutter.library_name }}/
│   ├── __init__.py
│   ├── __main__.py
│   ├── target.py          # TargetHotglue subclass, config_jsonschema{% if auth_m == "OAuth2" %}, access_token_support{% endif %}
│   ├── client.py          # Base sink, authenticator, record/batch bases
│   ├── sinks.py           # Stream-specific sinks
{% if auth_m == "OAuth2" %}
│   ├── auth.py            # OAuth2 refresh-token authenticator
{% endif %}
│   └── ...
├── .secrets/
│   └── config.json        # Example secrets (shape depends on auth_method)
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── pyproject.toml
├── .env.example
└── README.md
```

## Additional Resources

- Project README: See `README.md` for setup and usage
- [Hotglue Singer SDK](https://github.com/hotgluexyz/hotglue-singer-sdk)
- [Singer specification](https://github.com/singer-io/getting-started/blob/master/SPEC.md)

## Making Changes

When implementing changes:

1. Understand the data flow: records → processing → destination
1. Follow Singer and SDK patterns
1. Test with real data from various taps
1. Handle edge cases (nulls, large records, schema changes)
1. Update documentation
1. Ensure backward compatibility
1. Run linting and type checking

## Questions?

If you're uncertain about an implementation:

- Check SDK documentation for sink examples
- Review other Singer targets for patterns
- Test incrementally with sample data
- Validate against the Singer specification
- Consider data consistency and idempotency

## Bumping the Hotglue Singer SDK version

When upgrading **`hotglue-singer-sdk`** in `pyproject.toml`, follow these steps to avoid breaking changes:

1. **Check the Hotglue Singer SDK changelog and release notes** before upgrading.

1. **Update the dependency** in `pyproject.toml`:

   ```toml
   [project]
   dependencies = [
       "hotglue-singer-sdk>=X.Y.Z",
   ]
   ```

1. **Re-sync your environment** and run the full test suite:

   ```bash
   uv sync
   uv run pytest
   ```

1. **Address deprecation warnings**: Run with warnings enabled to catch anything that will become an error in a future release:

   ```bash
   uv run pytest -W error::DeprecationWarning
   ```

1. **Check the changelog** for any behavioral changes that affect your target, even if not surfaced by warnings (e.g. batching, sink processing, schema handling).

## Reporting SDK issues

If you encounter a bug in **Hotglue Singer SDK** behavior used by this target (`hotglue_singer_sdk`, `TargetHotglue`, target SDK helpers), report it where that package is maintained. Include SDK and Python versions plus a minimal reproduction case.
