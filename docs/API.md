# API Reference

This document describes the internal APIs used by the OctoPrint-PSUControl-eWeLink plugin.

## OctoPrint SimpleApi

The plugin exposes one API command via OctoPrint's SimpleApi system.

### `get_devices`

Fetches the list of devices associated with the eWeLink account.

**Endpoint:** `POST /api/plugin/psucontrol_ewelink`

**Request:**
```json
{
    "command": "get_devices",
    "email": "user@example.com",
    "password": "password123"
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Optional | eWeLink account email. Falls back to stored setting if empty. |
| `password` | string | Optional | eWeLink password. Falls back to stored (decrypted) setting if empty. |

**Response (Success):**
```json
{
    "devices": [
        {
            "name": "3D Printer",
            "deviceid": "10011e0b86",
            "online": true,
            "outlets": []
        },
        {
            "name": "Desk Lamp",
            "deviceid": "10012abc12",
            "online": false,
            "outlets": [0, 1, 2, 3]
        }
    ]
}
```

`outlets` lists the outlet numbers (0-based) a device reports in its `switches` params. It is empty for devices that report a single `switch` value. Some single-relay devices (e.g. BASICR4) still report several outlets.

**Response (Error):**
```json
{
    "error": "Connection failed: Invalid credentials"
}
```

**Usage from JavaScript:**
```javascript
OctoPrint.simpleApiCommand("psucontrol_ewelink", "get_devices", {
    email: "user@example.com",
    password: ""  // Empty = use stored password
}).done(function(response) {
    if (response.error) {
        console.error(response.error);
    } else {
        console.log("Found devices:", response.devices);
    }
});
```

---

## PSU Control Integration API

These methods are called by the PSU Control parent plugin.

### `turn_psu_on()`

Turns the configured eWeLink device ON.

- Called when: User clicks power icon in navbar (to turn ON)
- Implementation: Sends `{"params": {"switch": "on"}}` to eWeLink API
- Returns: None

### `turn_psu_off()`

Turns the configured eWeLink device OFF.

- Called when: User clicks power icon in navbar (to turn OFF)
- Implementation: Sends `{"params": {"switch": "off"}}` to eWeLink API
- Returns: None

### `get_psu_state()`

Returns the current power state of the device.

- Called when: PSU Control polls state (default: every 5 seconds)
- Implementation: Fetches device list, finds matching device, checks `params.switch`
- Returns: `True` if device is ON, `False` otherwise

**Note:** This method is only called if PSU Control is configured with:
- `sensingMethod = "PLUGIN"`
- `sensingPlugin = "psucontrol_ewelink"`

---

## eWeLink Cloud API

The plugin communicates with eWeLink's cloud API. These are the endpoints used:

### Authentication

**Endpoint:** `POST https://{region}-apia.coolkit.cc/v2/user/login`

Regions: `us`, `eu`, `cn`, `as`

The library handles authentication automatically, including:
- Request signing (HMAC with App Secret)
- Region auto-redirect (error 301 → correct region)

### Get Device List

**Endpoint:** `GET https://{region}-apia.coolkit.cc/v2/device/thing`

Returns all devices and their current state.

**Response Structure:**
```json
{
    "thingList": [
        {
            "itemType": 1,
            "itemData": {
                "name": "3D Printer",
                "deviceid": "10011e0b86",
                "online": true,
                "params": {
                    "switch": "on",
                    "power": 45.2,
                    "voltage": 230
                }
            }
        }
    ]
}
```

### Set Device Status

**Endpoint:** `POST https://{region}-apia.coolkit.cc/v2/device/thing/status`

**Request:**
```json
{
    "type": 1,
    "id": "10011e0b86",
    "params": {
        "switch": "on"
    }
}
```

---

## Internal Python Methods

### `_run_coro(coro)`

Bridges synchronous OctoPrint calls to async eWeLink library.

```python
def _run_coro(self, coro):
    future = asyncio.run_coroutine_threadsafe(coro, self._loop)
    return future.result(timeout=10)
```

### `_init_ewelink()`

Initializes or re-initializes the eWeLink connection using stored settings. Called on startup and after settings are saved.

### `_async_connect(email, password, device_id)`

Establishes connection to eWeLink cloud. Region is auto-detected by the API.

### `_async_fetch_devices(email, password)`

Fetches device list for "Test Connection" feature. Region is auto-detected by the API.

### `_toggle_device(device_id, state)`

Sends ON/OFF command to specific device.

### `_get_device_state(device_id)`

Fetches current switch state for specific device.

### `_encrypt_password(plaintext)` / `_decrypt_password(ciphertext)`

Handles XOR obfuscation of passwords for storage.

---

## Settings Schema

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `email` | string | `""` | eWeLink account email |
| `password` | string | `""` | Encrypted password (`ENC:...`) |
| `device_id` | string | `""` | Target device ID |

Note: Region is auto-detected by the eWeLink API.

---

📚 **More docs:** [README](../README.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Security](SECURITY.md) · [Architecture](ARCHITECTURE.md) · [Development](DEVELOPMENT.md) · [Changelog](CHANGELOG.md) · [Translations](TRANSLATIONS.md)
