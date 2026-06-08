# Hotglue Singer Target Cookiecutter

Cookiecutter template for a [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK) HTTP target (`TargetHotglue`, record/batch sinks, SDK authenticators).

It renders `{{cookiecutter.target_id}}/` into a full Python package: `target.py`, `client.py`, `sinks.py`, optional `auth.py`, tests, uv-based packaging, and ruff linting.

## Quick start

```bash
# Install cookiecutter (uv shown; pip works too)
uv tool install cookiecutter

# Interactive — from this repo root
cookiecutter .

# Non-interactive example
cookiecutter . --no-input \
  destination_name=Acme \
  admin_name="Jane Doe" \
  admin_email=jane@example.com \
  target_id=target-acme \
  library_name=target_acme \
  include_agent_instructions=AGENTS.md \
  license=MIT \
  base_url=https://api.example.com/v1 \
  auth_method="Basic Auth" \
  sinks="Contacts | record, Orders | batch"
```

Output directory: `target-acme/` (or whatever you set for `target_id`).

## Prompts

| Variable | Default | What it controls |
|----------|---------|------------------|
| `destination_name` | `MyDestinationName` | CamelCase Python identifier used in class names (`TargetAcme`, `AcmeRecordSink`, …). |
| `admin_name` / `admin_email` | — | `pyproject.toml` authors metadata. |
| `target_id` | `target-{destination lower}` | Package / CLI name (kebab-case), e.g. `target-acme`. |
| `library_name` | `target_id` with `-` → `_` | Import path, e.g. `target_acme`. |
| `include_agent_instructions` | `AGENTS.md` / `CLAUDE.md` / `None` | Keeps `AGENTS.md`, renames it to `CLAUDE.md`, or deletes it. |
| `license` | Apache-2.0 / MIT / None | Picks one `LICENSE-*` stub or removes both. |
| `base_url` | `https://myapi.com/api/v1` | Sets `{{ destination }}Sink.base_url` in `client.py` when non-empty. |
| `auth_method` | Bearer / Basic / API Key / OAuth2 | `config_jsonschema`, `.secrets/config.json`, authenticator in `client.py`, and whether `auth.py` survives the post-gen hook. |
| `sinks` | `Fallback \| record` | Stream sink classes in `sinks.py` and `SINK_TYPES` / `default_sink_class` in `target.py`. |

## How generation works

### 1. Jinja templates

Files under `{{cookiecutter.target_id}}/` are rendered with your answers. Logic is duplicated in a few places via shared Jinja variables:

- `sinks_csv` — trimmed `sinks` prompt, or `Fallback | record` when empty.
- `is_fallback_only` — `sinks_csv == 'Fallback | record'`.
- `ns.has_record` / `ns.has_batch` — derived by scanning each `Name | record|batch` entry.

### 2. `post_gen_project` hook

After files are written, `hooks/post_gen_project.py`:

- Renames or deletes license files per `license`.
- Removes `.vscode/` when `ide` is not `VSCode` (if `ide` is added to `cookiecutter.json`).
- **Deletes `auth.py`** unless `auth_method` is `OAuth2`.
- Renames `AGENTS.md` → `CLAUDE.md` or deletes agent instructions per `include_agent_instructions`.

### 3. Generated layout

```
target-{name}/
├── {library_name}/
│   ├── target.py      # TargetHotglue subclass, config_jsonschema, SINK_TYPES
│   ├── client.py      # Base sink + RecordSink and/or BatchSink
│   ├── sinks.py       # One class per stream (FallbackSink or named sinks)
│   └── auth.py        # OAuth2 only (removed by hook otherwise)
├── tests/
├── .secrets/config.json
└── pyproject.toml
```

## Authentication (`auth_method`)

| Method | `config_jsonschema` / `.secrets/config.json` | Code |
|--------|-----------------------------------------------|------|
| **Basic Auth** | `username`, `password` | `BasicAuthenticator` in `client.py` |
| **Bearer Token** | `access_key` | `BearerTokenAuthenticator` |
| **API Key** | `access_key`, optional header name/prefix | `ApiAuthenticator` |
| **OAuth2** | `client_id`, `client_secret`, `refresh_token`, optional token fields | `auth.py` + `Target.access_token_support()` in `target.py` |

## Sinks (`sinks`)

Format: comma-separated entries, each `StreamName | record` or `StreamName | batch`.

- `StreamName` must be a valid Python identifier (letters, digits, underscores).
- Invalid or empty input resolves to the default: `Fallback | record`.

### Fallback only (`Fallback | record` or empty)

- `sinks.py` defines `FallbackSink` extending `RecordSink` with dynamic `stream_name`, `name`, and `endpoint = f"/{stream_name}"`.
- `target.py`: `SINK_TYPES = []`, `default_sink_class = FallbackSink`, imports `FallbackSink` from `sinks.py` (not `RecordSink` from `client.py`).

### Named sinks (e.g. `Contacts | record, Orders | batch`)

- `sinks.py` emits `ContactsSink`, `OrdersSink`, each with fixed `name` and a TODO `endpoint`.
- `target.py`: `SINK_TYPES` lists those classes; imports them from `sinks.py` and the matching record/batch bases from `client.py`.
- No `default_sink_class`.

`client.py` only defines `RecordSink` / `BatchSink` base classes that are actually needed for the chosen modes.

## Development

```bash
# Lint this template repo
ruff check .

# CI-style matrix for rendered output (see cookiecutter.tests.yml)
# Run cookiecutter with each test context, then tox in the output project.
```

## Links

- [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK)
- [Cookiecutter docs](https://cookiecutter.readthedocs.io/)
