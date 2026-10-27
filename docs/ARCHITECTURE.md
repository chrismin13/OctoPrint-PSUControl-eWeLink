# Architecture Overview

This document describes the internal architecture of the OctoPrint-PSUControl-eWeLink plugin.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        OctoPrint Server                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │   PSU Control   │◄───│  PSUControl-eWeLink Plugin          │ │
│  │   (Parent)      │    │                                     │ │
│  │                 │    │  ┌─────────────┐  ┌───────────────┐ │ │
│  │  - Navbar Icon  │    │  │ Settings UI │  │ Backend Logic │ │ │
│  │  - Polling Loop │◄───│  │ (Jinja2/JS) │  │ (__init__.py) │ │ │
│  │  - API Endpoints│    │  └─────────────┘  └───────┬───────┘ │ │
│  └─────────────────┘    │                           │         │ │
│                         │  ┌────────────────────────▼───────┐ │ │
│                         │  │     Asyncio Event Loop         │ │ │
│                         │  │     (Background Thread)        │ │ │
│                         │  └────────────────────────┬───────┘ │ │
│                         └───────────────────────────┼─────────┘ │
└─────────────────────────────────────────────────────┼───────────┘
                                                      │
                                                      ▼
                                        ┌─────────────────────────┐
                                        │   eWeLink Cloud API     │
                                        │   (HTTPS/REST)          │
                                        │                         │
                                        │   - Authentication      │
                                        │   - Device Control      │
                                        │   - Status Polling      │
                                        └─────────────────────────┘
```

## Key Components

### 1. Backend (`__init__.py`)

The main plugin class `PSUControlEWeLinkPlugin` inherits from multiple OctoPrint mixins:

| Mixin | Purpose |
|-------|---------|
| `StartupPlugin` | Initialize asyncio loop and eWeLink connection on startup |
| `ShutdownPlugin` | Clean shutdown of asyncio loop |
| `TemplatePlugin` | Provide settings UI template |
| `SettingsPlugin` | Manage plugin settings (email, password, device_id, selected_switch) |
| `SimpleApiPlugin` | Expose `get_devices` API for frontend |
| `AssetPlugin` | Serve JavaScript assets |
| `RestartNeedingPlugin` | Flag that restart is needed after settings change |

### 2. Asyncio Bridge

The eWeLink Python library (`ewelink`) is fully asynchronous. OctoPrint is synchronous.

**Solution**: A dedicated background thread runs a persistent `asyncio` event loop:

```python
self._loop = asyncio.new_event_loop()
self._loop_thread = threading.Thread(target=self._loop.run_forever)
self._loop_thread.daemon = True
self._loop_thread.start()
```

All async operations are dispatched via:

```python
future = asyncio.run_coroutine_threadsafe(coro, self._loop)
return future.result(timeout=10)
```

### 3. PSU Control Integration

PSU Control discovers sub-plugins via `register_plugin` helper:

```python
helpers = self._plugin_manager.get_helpers("psucontrol")
if helpers and "register_plugin" in helpers:
    helpers["register_plugin"](self)
```

PSU Control then calls these methods on our plugin:
- `turn_psu_on()` - Turn eWeLink device ON
- `turn_psu_off()` - Turn eWeLink device OFF
- `get_psu_state()` - Get current switch state (True/False)

### 4. Frontend (`psucontrol_ewelink.js`)

Knockout.js ViewModel providing:
- **Settings binding** to OctoPrint's settings system
- **Password masking** to hide credentials in UI
- **Test Connection** button to validate credentials
- **Device dropdown** for easy device selection
- **Outlet dropdown** ("Automatic" plus the selected device's outlets)
- **Configuration banners** warning if PSU Control isn't configured

### 5. Settings Template (`psucontrol_ewelink_settings.jinja2`)

HTML form with data-bindings to the ViewModel:
- Email input
- Password input (type="password")
- Device ID input + dropdown selector
- Outlet selector
- Test Connection button
- Warning banners for configuration issues

## Data Flow

### 1. Login Flow

```
User enters credentials → Settings saved → on_settings_save()
    → _init_ewelink() → _async_connect() → eWeLink API login
    → Token stored in memory (not persisted)
```

### 2. Device Control Flow

```
PSU Control calls turn_psu_on() → _run_coro(_toggle_device())
    → eWeLink API GET /v2/device/thing (read the device's params)
    → _resolve_outlet() picks the switch format
    → eWeLink API POST /v2/device/thing/status
    → Device switched
```

### 3. State Sensing Flow

```
PSU Control polls get_psu_state() every 5 seconds
    → _run_coro(_get_device_state())
    → eWeLink API GET /v2/device/thing
    → _resolve_outlet() picks the switch format
    → Parse params.switch or params.switches[outlet] → Return True/False
```

### Switch Formats

eWeLink devices report their relay state in one of two formats:

| Format | Params | Example devices |
|--------|--------|-----------------|
| Single | `{"switch": "on"}` | BASIC R2, MINI R2, S26 |
| Multi | `{"switches": [{"outlet": 0, "switch": "on"}, ...]}` | BASICR4, S60TPF, 4CH |

The format is detected from the params the device reports, not from its model:

1. If **Outlet** is set and the device reports that outlet, it is used.
2. Otherwise (**Automatic**), devices reporting `switch` use the single format, exactly as in earlier versions.
3. Devices reporting only `switches` use outlet 0.

## Region Auto-Detection

The eWeLink API automatically redirects to the correct region:

1. Plugin always sends initial request to `us` region
2. If account is on different region (e.g., `eu`), API returns the correct region
3. Library automatically re-authenticates to correct region
4. User doesn't need to manually select region

---

📚 **More docs:** [README](../README.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Security](SECURITY.md) · [API](API.md) · [Development](DEVELOPMENT.md) · [Changelog](CHANGELOG.md) · [Translations](TRANSLATIONS.md)
