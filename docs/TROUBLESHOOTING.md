# Troubleshooting Guide

This document covers common issues and their solutions.

## Quick Diagnosis

Before diving into specific issues, check:

1. **OctoPrint logs**: `~/.octoprint/logs/octoprint.log`
2. **Browser console**: F12 → Console tab
3. **Plugin version**: Settings → Plugins → PSU Control - eWeLink

---

## Error: "Missing Requirement: PSU Control plugin is not installed!"

**Symptom:** Red warning banner appears in plugin settings.

**Cause:** The required dependency **OctoPrint-PSUControl** is not installed.

**Solution:**
1. Open **OctoPrint Settings** → **Plugin Manager** → **Get More**
2. Search for `PSU Control`
3. Click **Install**
4. Restart OctoPrint

---

## Error: "PSU Control is not configured to use this plugin"

**Symptom:** Yellow warning banner appears in plugin settings.

**Cause:** PSU Control's switching method isn't set to use this plugin.

**Solution:**
1. Go to OctoPrint Settings → PSU Control
2. Set **Switching Method** to `Plugin`
3. Set **Switching Plugin** to `PSU Control - eWeLink`
4. Click Save

---

## Error: "Connection failed: Invalid credentials"

**Symptom:** Test Connection button shows error.

**Possible Causes:**

| Cause | Solution |
|-------|----------|
| Wrong email/password | Double-check credentials in eWeLink app |
| Account locked | Try logging into eWeLink app directly |
| Two-factor authentication | Disable 2FA or use app-specific password |

**Debugging:**
```bash
# Check OctoPrint logs for more details
tail -f ~/.octoprint/logs/octoprint.log | grep ewelink
```

---

## Device Not Switching

**Symptom:** PSU Control shows "Turning on..." but device doesn't respond.

**Checklist:**

- [ ] Device shows "Online" in eWeLink app
- [ ] Correct Device ID is configured
- [ ] Device firmware is up to date
- [ ] WiFi connection is stable

**Check logs:**
```bash
grep "eWeLink" ~/.octoprint/logs/octoprint.log
```

Look for:
- `Turning PSU ON via eWeLink...`
- `Failed to connect to eWeLink:`
- Any error messages

---

## Error 4002 ("控制失败") or Wrong Outlet Switching

**Symptom:** Log shows `Error (4002): 控制失败` ("control failed"), or a multi-output device switches the wrong output.

**Possible Causes:**

| Cause | Solution |
|-------|----------|
| Device is offline | Check the device is "Online" in the eWeLink app |
| Wrong outlet selected | Set **Outlet** to **Automatic**, or click **Test Connection / Get Devices** and pick the right outlet |
| Plugin version 1.0.15 or older | Update the plugin. Older versions only supported devices that report a single `switch` value (not BASICR4, S60TPF, etc.) |

If an outlet is selected that the device doesn't report, the log shows `Device ... has no outlet ...` and the plugin falls back to **Automatic**.

---

## State Not Updating

**Symptom:** Navbar icon doesn't reflect actual switch state.

**Cause:** Sensing not configured.

**Solution:**
1. Go to OctoPrint Settings → PSU Control
2. Set **Sensing Method** to `Plugin`
3. Set **Sensing Plugin** to `PSU Control - eWeLink`
4. Save and refresh page

**Note:** State polling occurs every 5 seconds (PSU Control default).

---

## Plugin Not Loading / Python Error

**Symptom:** Plugin doesn't appear in OctoPrint, or shows Python compatibility error.

**Common Causes:**

1. **Missing dependency:**
   ```bash
   pip install ewelink
   ```

2. **Syntax error in `__init__.py`:**
   Check for IndentationError or SyntaxError in logs.

3. **Python version:**
   Plugin requires Python 3.9+. Check:
   ```bash
   python --version
   ```

---

## Device List Empty

**Symptom:** Test Connection succeeds but no devices appear.

**Possible Causes:**

| Cause | Solution |
|-------|----------|
| No devices in account | Add device via eWeLink app first |
| Devices offline | Check device WiFi connection |
| Wrong account | Verify email matches eWeLink app |

---

## "eWeLink app not connected" Warning

**Symptom:** Log shows `eWeLink app not connected` when trying to switch.

**Cause:** Initial connection failed at startup.

**Solution:**
1. Verify credentials are correct
2. Restart OctoPrint: `sudo service octoprint restart`
3. Check logs for connection errors

---

## Slow Response / Timeout

**Symptom:** Commands take long time or timeout after 10 seconds.

**Possible Causes:**

- eWeLink cloud servers slow
- Network issues on Pi
- Rate limiting (too many requests)

**Solution:**
- Wait a few minutes and retry
- Check Pi internet connection: `ping google.com`
- Reduce PSU Control polling interval if needed

---

## Browser Console Errors

### `TypeError: Cannot read properties of undefined`

**Cause:** ViewModel not properly initialized.

**Solution:** Update to latest version. If persists, hard refresh (Ctrl+Shift+R).

### `ko.bindingHandlers...`

**Cause:** Knockout.js binding conflict.

**Solution:** Plugin uses `custom_bindings=True`. Ensure no other plugins conflict.

---

## Collecting Debug Information

When reporting issues, include:

1. **OctoPrint version:** Settings → About
2. **Plugin version:** Settings → Plugins
3. **Python version:** `python --version`
4. **Relevant logs:**
   ```bash
   grep -i "psucontrol\|ewelink" ~/.octoprint/logs/octoprint.log | tail -100
   ```
5. **Browser console errors** (F12 → Console)
6. **Steps to reproduce** the issue

---

## Still Stuck?

1. Check [GitHub Issues](https://github.com/chrismin13/OctoPrint-PSUControl-eWeLink/issues) for similar problems
2. Open a new issue with debug information above
3. Include screenshots if relevant

---

📚 **More docs:** [README](../README.md) · [Security](SECURITY.md) · [API](API.md) · [Architecture](ARCHITECTURE.md) · [Development](DEVELOPMENT.md) · [Changelog](CHANGELOG.md) · [Translations](TRANSLATIONS.md)
