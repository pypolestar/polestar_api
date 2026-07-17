# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (HACS) for Polestar electric vehicles, backed by the
[`pypolestar`](https://github.com/pypolestar/pypolestar) library, which talks to Polestar's cloud API
(GraphQL for most data, gRPC for charger connection status / target SoC). Domain: `polestar_api`.

## Commands

```bash
make lint          # ruff check custom_components
make reformat      # ruff check --select I --fix + ruff format (imports + formatting)
make test          # PYTHONPATH=. pytest -vv tests
```

- `scripts/lint` runs `ruff format .` + `ruff check . --fix` (broader than `make lint`, fixes in place).
- `scripts/setup` installs `requirements.txt`.
- `scripts/develop` runs a real Home Assistant instance against this integration: it creates a `config/`
  dir (via `hass --script ensure_config`) if missing, puts `custom_components` on `PYTHONPATH`, and starts
  `hass --config ./config --debug`. Use this to manually exercise config flow / entities end-to-end.
- No `tests/` directory currently exists in this repo despite `make test` and `requirements.txt` (pytest)
  referencing it — there is no automated test suite to run yet.
- Ruff config lives in `pyproject.toml`: line length 88, `E501` ignored, isort with `combine-as-imports`.
- Pre-commit hooks (`.pre-commit-config.yaml`) run the standard hygiene checks plus `ruff-check`/`ruff-format`.

### CI (`.github/workflows/`)
- `test.yml`: ruff check + format check, and `python scripts/translation_utils.py --test` (validates
  translation strings are consistent/sorted).
- `hassfest.yml`: Home Assistant's `hassfest` manifest/integration validator.
- `validate.yml`: HACS validation action.

## Architecture

Standard HA integration layout under `custom_components/polestar_api/`:

- **`__init__.py`** — `async_setup_entry` creates one shared `PolestarApi` client (from `pypolestar`) per
  config entry, then spins up **one `PolestarCoordinator` per VIN** (a config entry can cover multiple
  cars, or be scoped to a single VIN via `CONF_VIN`). Platforms (`image`, `sensor`, `binary_sensor`) are
  then forwarded. `entry.runtime_data` (typed via `PolestarData` in `data.py`) holds the api client and the
  list of coordinators — that's how platform files reach the coordinators (`entry.runtime_data.coordinators`).
- **`coordinator.py`** — `PolestarCoordinator(DataUpdateCoordinator)`, one per VIN, polls every 60s
  (`DEFAULT_SCAN_INTERVAL`). Each refresh pulls: car telematics (odometer/battery/health) every cycle, car
  information/images only every hour (`CAR_INFORMATION_UPDATE_INTERVAL`, tracked via
  `need_car_information_refresh`), and gRPC data (charger connection, target SoC) — the latter is
  best-effort/non-fatal by design (pypolestar returns `None` rather than raising). Auth failures raise
  `ConfigEntryAuthFailed`; other API errors raise `UpdateFailed`. Diagnostic state (`api_connected`,
  token expiry, last HTTP status codes for data/auth calls) is stuffed into the coordinator's `data` dict
  in the `finally` block and surfaced as diagnostic sensors.
- **`entity.py`** — `PolestarEntity(CoordinatorEntity)` is the shared base for all platforms. Entities are
  declarative: a `PolestarEntityDescription` (extends HA's `EntityDescription`) specifies a
  `data_source` (`PolestarEntityDataSource` enum: which coordinator attribute holds the data — e.g.
  `car_battery_data`, `grpc_battery_data`) plus `data_state_attribute` (attribute name to read off that
  data object), an optional `data_state_fn` to transform the raw value, and optional
  `data_extra_state_attributes` for extra attrs. `get_native_value()` / `get_extra_state_attributes()` do
  the generic lookup + logging of missing sources/attributes so platform code rarely needs custom logic —
  see how small `PolestarSensor.native_value` in `sensor.py` is as a result.
- **`sensor.py` / `binary_sensor.py` / `image.py`** — each defines tuples of `*EntityDescription` constants
  (grouped by data source, e.g. `INFORMATION_ENTITY_DESCRIPTIONS`, `BATTERY_ENTITY_DESCRIPTIONS`,
  `GRPC_TARGET_SOC_ENTITY_DESCRIPTIONS`) concatenated into one `ENTITY_DESCRIPTIONS` tuple, and a generic
  `async_setup_entry` that fans this tuple out across `entry.runtime_data.coordinators` (i.e. across cars).
  Adding a new entity is almost always: add one description entry to the right tuple, not new class code.
- **`config_flow.py`** — single-step user flow (username/password/optional VIN), validates credentials by
  calling `PolestarApi.async_init()` / `get_available_vins()` against the real Polestar API before creating
  the entry, then always logs out the throwaway client in `finally`.
- **`data.py`** — typed `PolestarConfigEntry = ConfigEntry[PolestarData]` and the `PolestarData` dataclass
  (`api_client`, `coordinators`, `integration`) stored as `entry.runtime_data`.
- **`diagnostics.py`** / **`system_health.py`** — HA integration diagnostics/system-health hooks.

## Translation infrastructure

- `strings.json` is the source of truth for all entity/config-flow strings; `translations/*.json` are
  per-language translated copies (`en.json` is a direct copy of `strings.json`).
- Translations are managed via [Crowdin](https://crowdin.com/project/polestar-home-assistant) — contributors
  translate there, not by hand-editing `translations/*.json` in this repo.
- `scripts/translation_utils.py` cross-checks every `translations/*.json` against `strings.json` (reports
  missing/superfluous entity string keys per language) and enforces that `strings.json` and all translation
  files have alphabetically sorted keys. Run `python scripts/translation_utils.py --sort` to fix sorting
  locally, or `--test` to check-only (this is what CI runs).
- `scripts/fetch_translations.py` pulls a finished build from the Crowdin API (`CROWDIN_TOKEN` /
  `CROWDIN_PROJECT_ID` env vars) and unzips it in place; `crowdin.sh` is the wrapper that sets those env
  vars, runs the fetch, and then re-copies `strings.json` over `translations/en.json`.
