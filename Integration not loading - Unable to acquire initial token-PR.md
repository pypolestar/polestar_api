# Integration not loading - Unable to acquire initial token

## Summary

Polestar changed the Polestar ID login flow. The login endpoint now redirects to
a Keycloak page. `pypolestar==1.12.7` does not support this page. The integration
cannot get an initial token. This PR adds Keycloak support to the integration.

## Problem

- The integration fails during setup and in the config flow.
- The log shows `Unable to acquire initial token`.
- The cause is `PolestarAuthException: Error getting resume path` in
  `pypolestar.auth._get_resume_path`.
- The problem is not related to a user password.

## Cause

1. Since 26 November 2026, the Polestar ID authorization endpoint redirects to a
   Keycloak realm on `auth.polestar.com`.
2. The old code reads a PingFederate resume path from the login page.
3. The Keycloak page does not contain this path.
4. The login stops before the token exchange.

`pypolestar` 1.12.7 is the latest release on PyPI. No release contains a
Keycloak fix. For this reason, the fix is in this integration.

## Solution

Add a small authentication shim. The shim does these steps:

1. Load the authorization page.
2. Follow the redirect to Keycloak.
3. Read `loginAction` from the Keycloak `kcContext`.
4. Post `username`, `password`, and `credentialId` to `loginAction`.
5. Follow the Keycloak, PingFederate, and callback redirects.
6. Read the authorization code only at the final application callback.
7. Exchange the code for a token. This step does not change.

If the page is not a Keycloak page, the shim uses the old PingFederate flow.
The shim also reports a one-time code page as a separate error.

Each credential validation uses a new HTTP client. The client closes after the
attempt. A Keycloak session from one account cannot validate another account.

## Changes

### New file

`custom_components/polestar_api/keycloak_auth.py`

- Adds `KeycloakPolestarAuth`.
- Adds `PolestarMfaRequiredException`.
- Adds `create_polestar_api()`.

### Changed files

`custom_components/polestar_api/__init__.py`

- Uses `create_polestar_api()`.
- Handles `PolestarAuthFailedException` during setup.
- Keeps the one-time-code message in the setup error.

`custom_components/polestar_api/config_flow.py`

- Uses `create_polestar_api()`.
- Validates each account on a dedicated HTTP client and closes it.
- Maps authentication errors to these config flow errors:
  - `auth_failed`: the username or password is not correct.
  - `mfa_required`: Polestar asks for an additional step, for example a
    one-time code.
- Maps other authentication errors to `auth_failed`.

`custom_components/polestar_api/strings.json`

`custom_components/polestar_api/translations/en.json`

- Add the `mfa_required` message. The message tells the user to sign in once at
  `polestar.com`.

### Test files

`tests/test_keycloak_auth.py`

- Tests a full Keycloak login.
- Tests a wrong password.
- Tests a one-time code page.
- Tests the old PingFederate flow.
- Tests URL unescaping.

`tests/test_setup_entry.py`

- Tests that the setup error keeps the one-time-code message.
- Tests other authentication errors during setup.
- Tests that a successful authentication continues setup.
- Tests that a second account cannot reuse the first account's Keycloak session.

## User action for one-time code

The integration cannot accept a one-time code in Home Assistant. If Polestar
asks for a code, the user must sign in once at `polestar.com` with the same
account. Then the user can retry the integration.

## Test results

Run these commands:

```bash
pytest -q tests
ruff check custom_components/polestar_api/__init__.py \
  custom_components/polestar_api/config_flow.py \
  custom_components/polestar_api/keycloak_auth.py tests
ruff format --check custom_components/polestar_api/__init__.py \
  custom_components/polestar_api/config_flow.py \
  custom_components/polestar_api/keycloak_auth.py tests
python scripts/translation_utils.py --test
```

Results:

- `pytest -q tests`: 10 passed.
- `ruff check`: all changed files pass.
- `ruff format --check`: all changed files pass.
- `translation_utils.py --test`: exit code 0.

The tests use `httpx.MockTransport`. The tests do not use the live Polestar
service. A live login was not tested because no test account was available.

## Compatibility and risks

- The manifest still uses `pypolestar==1.12.7`.
- This PR does not change a dependency.
- The old PingFederate flow is still available as a fallback.
- Remove `keycloak_auth.py` when a `pypolestar` release supports Keycloak.
- The shim depends on the current `pypolestar` private methods. The manifest
  pins the library version, so this risk is limited.
- Repo-wide `ruff check` still reports one existing `UP017` error in
  `coordinator.py`. This PR does not change that file.

## Related links

- Issue: https://github.com/pypolestar/polestar_api/issues/456
- Reference PR: https://github.com/kildahldev/unofficial-polestar-api/pull/47
- Upstream issue: https://github.com/kildahldev/unofficial-polestar-api/issues/46
