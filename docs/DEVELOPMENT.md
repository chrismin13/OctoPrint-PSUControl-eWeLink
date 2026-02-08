# Developer Notes & Contribution Guide

This document captures key technical decisions and learnings discovered during the development of the OctoPrint-PSUControl-eWeLink plugin.

## 1. Asynchronous Architecture
The `ewelink` Python library is completely asynchronous (`asyncio`/`aiohttp`). OctoPrint's plugin system is primarily synchronous.
*   **Problem**: Simply calling `asyncio.run()` inside OctoPrint hooks creates a new event loop for every call, which kills the persistent `aiohttp` session needed by the library.
*   **Solution**: We spawn a dedicated background thread (`self._loop_thread`) that runs a persistent `asyncio` event loop. All `ewelink` library calls are dispatched to this loop using `asyncio.run_coroutine_threadsafe`.

## 2. eWeLink App Credentials
*   **Critical**: The standard user email/password is NOT enough. The library also requires an "App ID" and "App Secret" to sign requests.
*   **Finding**: Generic or default credentials often fail with "invalid appid" or signature errors.
*   **Fix**: We successfully tested and hardcoded a known working set of credentials (extracted from the `SonoffLAN` Home Assistant integration).
    *   **App ID**: `R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv`
    *   **Secret**: `1ve5Qk9GXfUhKAn1svnKwpAlxXkMarru` (Do not change these unless confirmed broken).

## 3. Library Limitations & Workarounds
The `ewelink` Python library has some incomplete implementations.
*   `app.get_thing_list()` raises `NotImplementedError`.
*   Solution: We manually call `app._auth_request("GET", "v2/device/thing")` to get the raw device list.
*   Device object methods (`device.on()`, `device.off()`) were also unreliable.
*   Solution: We implemented `_toggle_device` helper to send raw `POST` requests to `v2/device/thing/status`.

## 4. OctoPrint Metadata & Syntax
*   **Pitfall**: OctoPrint reads `__init__.py` (AST parsing) to determine plugin metadata like `__plugin_pythoncompat__`.
*   **Warning**: If `__init__.py` contains **ANY** syntax error (even deep inside a method like an `IndentationError`), the AST parser may fail silently or partially, causing OctoPrint to default to generic values (e.g., claiming the plugin is "Python 2.7" compatible only).
*   **Best Practice**:
    1.  Keep metadata (`__plugin_name__`, `__plugin_pythoncompat__`) at the very top of `__init__.py`.
    2.  Ensure strict syntax correctness before packaging.
    3.  Avoid complex top-level imports that might fail in environments with missing dependencies, although standard imports are fine if the environment is correct.

## 5. Region Auto-Detection

The eWeLink API automatically redirects to the correct region:

```python
# Login without specifying a region:
login = await app.login()  # No region parameter needed

# If account is on EU but library defaults to US:
# → API returns error 301 with correct region
# → Library auto-retries with correct region
# → Final result: login.region == "eu"
```

This allows us to remove the region dropdown entirely and just hardcode "us" as the initial attempt.

## 6. Password Security Flow

```
User enters password
    ↓
on_settings_save()
    ↓
_encrypt_password(plaintext)
    ↓
XOR with unique salt + hex encode
    ↓
Store as "ENC:abc123..." in config.yaml
    ↓
On load: _decrypt_password() reverses the process
```

Salt is stored in: `~/.octoprint/data/psucontrol_ewelink/salt`

## 7. PSU Control Integration Points

PSU Control discovers sub-plugins via a helper registration system:

```python
# On startup
helpers = self._plugin_manager.get_helpers("psucontrol")
helpers["register_plugin"](self)
```

PSU Control then calls these methods based on configuration:

| PSU Control Setting | Our Method Called |
|---------------------|-------------------|
| `switchingMethod = PLUGIN, switchingPlugin = psucontrol_ewelink` | `turn_psu_on()`, `turn_psu_off()` |
| `sensingMethod = PLUGIN, sensingPlugin = psucontrol_ewelink` | `get_psu_state()` |

## 8. Development Setup

> **Quickstart (recommended)**
>
> Use a virtual environment (venv) to isolate dependencies and avoid conflicts with your system Python or other OctoPrint plugins. The venv will contain this plugin in editable mode plus dev tooling (Babel/go-task).
>
> ```bash
> python3 -m venv .venv
> source .venv/bin/activate
> python -m pip install -e .[develop]
> ```
>
> This keeps installs reproducible, makes cleanup as simple as deleting `.venv`, and ensures you are testing against the plugin's declared dependencies.

```bash
# Clone and install in editable mode
cd /path/to/OctoPrint-PSUControl-eWeLink
pip install -e .

# Restart OctoPrint
sudo service octoprint restart

# Watch logs
tail -f ~/.octoprint/logs/octoprint.log | grep -i ewelink
```

### Optional: Taskfile shortcuts

If you use [go-task](https://taskfile.dev), `Taskfile.yml` provides shortcuts for common actions (e.g., `task install`). This is optional and not required for development.

## 9. Testing eWeLink API Locally

Create a test script:

```python
import asyncio
from ewelink import EWeLink
from ewelink.types import AppCredentials, EmailUserCredentials

async def test():
    app_cred = AppCredentials(
        id="R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv",
        secret="1ve5Qk9GXfUhKAn1svnKwpAlxXkMarru"
    )
    user_cred = EmailUserCredentials(email="your@email.com", password="yourpass")
    app = EWeLink(app_cred=app_cred, user_cred=user_cred)

    login = await app.login(region="us")
    print(f"Logged in! Region: {login.region}")

    resp = await app._auth_request("GET", "v2/device/thing")
    for thing in resp["thingList"]:
        item = thing.get("itemData", {})
        print(f"Device: {item.get('name')} ({item.get('deviceid')}) - {'Online' if item.get('online') else 'Offline'}")

    await app.close()

asyncio.run(test())
```

## 10. Running Tests

The plugin includes a unit test suite in `tests/test_plugin.py`. These tests mock OctoPrint and eWeLink dependencies, so they can be run on any machine without needing a full OctoPrint server or real device connection.

To run the tests:

```bash
python3 -m unittest tests/test_plugin.py
```

This is highly recommended before verifying changes to ensure no regressions in core logic (encryption, fallback, etc).

## 11. Manual Integration Testing (OctoPrint WebUI + Device)

Unit tests cover internal logic, but they do not validate the full UI → OctoPrint → eWeLink → device path. Use this short manual checklist when you want to verify end-to-end behavior with a real device:

1. **Install or update the plugin** in your OctoPrint instance (restart OctoPrint afterward).
2. **Open** **Settings → PSU Control - eWeLink** and:
   - Enter email + password.
   - Click **Test Connection / Get Devices** and confirm the device list appears.
   - Select your device and **Save**.
3. **Open** **Settings → PSU Control** and:
   - Set **Switching Method** to **Plugin**.
   - Select **OctoPrint-PSUControl-eWeLink**.
4. **Verify actions**:
   - Use **PSU Control** on/off from the UI and confirm the device toggles.
   - Refresh the PSU state and confirm it matches the actual device.
5. **Check logs** for errors or warnings:
   ```bash
   tail -f ~/.octoprint/logs/octoprint.log | grep -i ewelink
   ```

This keeps manual testing explicit and fast while still validating the real hardware path.

## 12. Development Guidelines

Follow these rules to maintain the stability of the plugin:

1.  **Testing First**: Always run the unit tests (`python3 -m unittest tests/test_plugin.py`) before committing.
2.  **Async Discipline**:
    *   OctoPrint is **Synchronous**.
    *   eWeLink is **Asynchronous**.
    *   **Rule**: Never call `asyncio.run()` directly in the main thread. Always use `self._run_coro()` or spawn a separate thread.
3.  **Credential Safety**: Never log the raw password. Use `_encrypt_password` immediately upon save, and `_decrypt_password` only when needed for the API connection.
4.  **PNotify XSS Safety**: OctoPrint ships PNotify v3, which renders HTML by default. Always use `text_escape: true` when displaying untrusted data (device names, error messages).
5.  **Plugin Registry Sync**: The file `extras/psucontrol_ewelink.md` should match `plugins.octoprint.org/_plugins/psucontrol_ewelink.md`. Update both when changing description, features, or compatibility.
6.  **Documentation**: If you add a feature, update `API.md` and add a test case.

## 13. Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md) - Component diagram, data flow
- [SECURITY.md](SECURITY.md) - Password obfuscation details
- [API.md](API.md) - Endpoint reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [TRANSLATIONS.md](TRANSLATIONS.md) - Translation guide
