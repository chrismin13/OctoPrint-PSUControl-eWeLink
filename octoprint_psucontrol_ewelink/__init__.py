# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import asyncio
import threading
import flask
import os
import binascii

import select
from ewelink import EWeLink
from ewelink.types import AppCredentials, EmailUserCredentials
from flask_babel import gettext

__plugin_name__ = "PSU Control - eWeLink"
__plugin_pythoncompat__ = ">=3.9,<4"
__plugin_privacypolicy__ = "https://github.com/chrismin13/OctoPrint-PSUControl-eWeLink/blob/main/PRIVACY.md"

# Known working App ID and Secret (extracted from SonoffLAN)
APP_ID = "R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv"
APP_SECRET = "1ve5Qk9GXfUhKAn1svnKwpAlxXkMarru"

class PSUControlEWeLinkPlugin(
        octoprint.plugin.StartupPlugin,
        octoprint.plugin.ShutdownPlugin,
        octoprint.plugin.TemplatePlugin,
        octoprint.plugin.SettingsPlugin,
        octoprint.plugin.SimpleApiPlugin,
        octoprint.plugin.AssetPlugin,
        octoprint.plugin.RestartNeedingPlugin):
    """
    Main Plugin Class.

    Integrates eWeLink cloud devices with OctoPrint's PSU Control plugin.

    Architecture:
    - Inherits from multiple OctoPrint mixins to handle settings, assets, and APIs.
    - Manages a separate background thread with an `asyncio` event loop.
    - Uses the `ewelink` Python library (async) to communicate with the cloud.
    - Bridges synchronous OctoPrint calls (from PSU Control) to the async loop.
    """

    def __init__(self):
        self._ewelink_app = None
        self._loop = None
        self._loop_thread = None
        self._salt = None

        # Call parent constructors for all mixins
        super().__init__()

    ##~~ Obfuscation Helpers

    def _get_salt(self):
        """
        Retrieves or generates a unique 32-byte salt for this installation.
        The salt is stored in `~/.octoprint/data/psucontrol_ewelink/salt`.
        """
        if self._salt:
            return self._salt

        salt_path = os.path.join(self.get_plugin_data_folder(), "salt")
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                self._salt = f.read()
        else:
            self._salt = os.urandom(32)
            if not os.path.exists(self.get_plugin_data_folder()):
                os.makedirs(self.get_plugin_data_folder())
            with open(salt_path, "wb") as f:
                f.write(self._salt)
        return self._salt

    def _xor(self, data, salt):
        return bytes([b ^ salt[i % len(salt)] for i, b in enumerate(data)])

    def _encrypt_password(self, plaintext):
        """
        Obfuscates the password using XOR with a local salt.
        Returns a string prefixed with "ENC:" to identify it as encrypted.
        Note: This is not "secure" encryption (key is on disk), but prevents
        accidental exposure in logs or the UI.
        """
        if not plaintext or plaintext.startswith("ENC:"):
            return plaintext
        try:
            salt = self._get_salt()
            encrypted = self._xor(plaintext.encode('utf-8'), salt)
            return "ENC:" + binascii.hexlify(encrypted).decode('ascii')
        except Exception as e:
            self._logger.error(f"Encryption failed: {e}")
            return plaintext

    def _decrypt_password(self, ciphertext):
        """
        Reverses the XOR obfuscation to retrieve the plaintext password.
        """
        if not ciphertext or not ciphertext.startswith("ENC:"):
            return ciphertext
        try:
            salt = self._get_salt()
            hex_str = ciphertext[4:]
            encrypted = binascii.unhexlify(hex_str)
            decrypted = self._xor(encrypted, salt)
            return decrypted.decode('utf-8')
        except Exception as e:
            self._logger.error(f"Decryption failed: {e}")
            return ciphertext

    ##~~ AssetPlugin mixin

    def get_assets(self):
        return dict(
            js=["js/psucontrol_ewelink.js"]
        )


    def get_settings_defaults(self):
        return dict(
            email="",
            password="",
            device_id="",
            selected_switch=-1
        )



    def on_after_startup(self):
        """
        Called by OctoPrint after the server has started.
        1. Migrates any legacy plaintext passwords to encrypted format.
        2. Starts the asyncio background thread.
        3. Initializes the eWeLink connection.
        4. Registers with the parent PSU Control plugin.
        """
        self._logger.info("PSUControl-eWeLink loaded!")

        # Migration: Encrypt existing plaintext password
        stored_password = self._settings.get(["password"])
        if stored_password and not stored_password.startswith("ENC:"):
            self._logger.info("Migrating plaintext password to encrypted storage...")
            encrypted = self._encrypt_password(stored_password)
            self._settings.set(["password"], encrypted)
            self._settings.save()

        self._start_loop()
        self._init_ewelink()

        # Register with PSU Control
        helpers = self._plugin_manager.get_helpers("psucontrol")
        if helpers and "register_plugin" in helpers:
            helpers["register_plugin"](self)
            self._logger.info("Registered with PSUControl.")
        else:
            self._logger.warning("PSUControl not found or incompatible.")

    def _start_loop(self):
        """
        Starts the dedicated asyncio event loop in a daemon thread.
        This is required because the `ewelink` library uses aiohttp, which needs
        a persistent event loop that doesn't conflict with OctoPrint's main thread.
        """
        if self._loop and self._loop.is_running():
            return
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._loop.run_forever)
        self._loop_thread.daemon = True
        self._loop_thread.start()
        self._logger.info("Asyncio loop started.")

    def on_shutdown(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._logger.info("Stopping asyncio loop...")
            try:
                self._loop_thread.join(timeout=2)
            except:
                pass
            self._logger.info("Asyncio loop stopped.")

    def _run_coro(self, coro):
        """
        Helper to run an async coroutine from a synchronous context (OctoPrint).
        It submits the coroutine to the background loop and waits for the result (up to 10s).
        """
        if not self._loop:
            self._start_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=10) # 10s timeout for operations
        except Exception as e:
            self._logger.error(f"Async operation failed: {e}")
            raise

    def _init_ewelink(self):
        """
        Initializes the eWeLink app connection using stored credentials.
        """
        email = self._settings.get(["email"])
        password = self._decrypt_password(self._settings.get(["password"]))
        device_id = self._settings.get(["device_id"])

        if not email or not password or not device_id:
            self._logger.warning("eWeLink credentials or Device ID not configured.")
            return

        try:
            # Region is auto-detected by the API
            self._run_coro(self._async_connect(email, password, device_id))
        except Exception as e:
            self._logger.error(f"Failed to connect to eWeLink: {e}")
            self._ewelink_app = None

    async def _async_connect(self, email, password, device_id):
        self._logger.info(f"Connecting to eWeLink with device: {device_id}...")

        user_cred = EmailUserCredentials(email=email, password=password)
        app_cred = AppCredentials(id=APP_ID, secret=APP_SECRET)

        self._ewelink_app = EWeLink(app_cred=app_cred, user_cred=user_cred)
        login = await self._ewelink_app.login()
        self._logger.info(f"eWeLink Logged in. Region: {login.region}")
        # We don't store device object because we interact via raw requests to support all devices

    def turn_psu_on(self):
        """
        Method called by PSU Control to turn the device ON.
        """
        device_id = self._settings.get(["device_id"])
        selected_switch = int(self._settings.get(["selected_switch"]))
        if not self._ewelink_app:
            self._logger.warning("eWeLink app not connected.")
            return
        try:
            self._logger.info("Turning PSU ON via eWeLink...")
            self._run_coro(self._toggle_device(device_id, 'on', selected_switch))
        except Exception as e:
            self._logger.error(f"Error turning ON: {e}")

    def turn_psu_off(self):
        """
        Method called by PSU Control to turn the device OFF.
        """
        device_id = self._settings.get(["device_id"])
        selected_switch = int(self._settings.get(["selected_switch"]))
        if not self._ewelink_app:
            self._logger.warning("eWeLink app not connected.")
            return
        try:
            self._logger.info("Turning PSU OFF via eWeLink...")
            self._run_coro(self._toggle_device(device_id, 'off', selected_switch))
        except Exception as e:
            self._logger.error(f"Error turning OFF: {e}")

    # SimpleApiPlugin

    def is_api_adminonly(self):
        """Restrict API access to admin users only for security."""
        return True

    def is_api_protected(self):
        """Require an authenticated OctoPrint user for API access."""
        return True

    def get_api_commands(self):
        return dict(
            get_devices=["email", "password"]
        )

    def on_settings_save(self, data):
        # Prevent overwriting password with mask
        if data.get("password") == "********":
            data.pop("password", None)
        elif data.get("password"):
            # Encrypt new password
            data["password"] = self._encrypt_password(data["password"])

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._logger.info("Settings saved. Re-initializing eWeLink connection...")
        # Re-init connection in a separate thread to avoid blocking
        threading.Thread(target=self._init_ewelink).start()

    def on_api_command(self, command, data):
        """
        Handles requests from the Javascript frontend.
        Command: `get_devices`
        - Authenticates with provided or stored credentials.
        - Fetches list of devices for the user to select.
        """
        if command == "get_devices":
            email = data.get("email")
            password = data.get("password")

            # Fallback to stored credentials if not provided (e.g. from masked UI)
            if not email:
                email = self._settings.get(["email"])
            if not password:
                # Retrieve and decrypt stored password
                stored_encrypted = self._settings.get(["password"])
                password = self._decrypt_password(stored_encrypted)

            try:
                # Region is auto-detected by the API
                result = self._run_coro(self._async_fetch_devices(email, password))
                if isinstance(result, str):  # Error message
                    return flask.jsonify(dict(error=result))
                return flask.jsonify(dict(devices=result))
            except Exception as e:
                return flask.jsonify(dict(error=str(e)))

        # NOTE: Error message when API command is not recognized
        return flask.make_response(gettext("Unknown command"), 400)

    async def _async_fetch_devices(self, email, password):
        try:
            user_cred = EmailUserCredentials(email=email, password=password)
            app_cred = AppCredentials(id=APP_ID, secret=APP_SECRET)
            app = EWeLink(app_cred=app_cred, user_cred=user_cred)
            await app.login()

            resp = await app._auth_request("GET", "v2/device/thing")
            devices = []
            if "thingList" in resp:
                for thing in resp["thingList"]:
                    item = thing.get("itemData", {})
                    devices.append({
                        "name": item.get("name", "Unknown"),
                        "deviceid": item.get("deviceid"),
                        "online": item.get("online", False)
                    })
            return devices
        except Exception as e:
            # NOTE: Error message showing the specific exception error
            return gettext("Connection failed: %(error)s") % {'error': str(e)}

    def get_psu_state(self):
        """
        Method called by PSU Control to poll the current device state.
        Returns:
            True if ON
            False if OFF
        """
        device_id = self._settings.get(["device_id"])
        selected_switch = int(self._settings.get(["selected_switch"]))
        if not self._ewelink_app:
            return False
        try:
            # run_coro returns the result of the coro
            return self._run_coro(self._get_device_state(device_id,selected_switch))
        except Exception as e:
            # Suppress verbose error logging for polling
            # self._logger.debug(f"Error getting state: {e}")
            return False

    async def _toggle_device(self, device_id, state, selected_switch):

        params = {"switch": state} if selected_switch < 0 else {
            "switches":[{"outlet": selected_switch, "switch": state}]
        }
        self._logger.info(f"Sending request to eWeLink: {params}, device_id: {device_id}, selected_switch: {selected_switch}")
        await self._ewelink_app._auth_request(
            "POST",
            "v2/device/thing/status",
            json={
                "type": 1,
                "id": device_id,
                "params": params,
            },
        )

    async def _get_device_state(self, device_id, selected_switch):
        resp = await self._ewelink_app._auth_request("GET", "v2/device/thing")
        things = resp["thingList"]
        for thing in things:
            item_data = thing.get("itemData", {})
            if item_data.get("deviceid") == device_id:
                params = item_data.get("params", {})
                multi_switches = params.get("switches",[])
                if multi_switches:
                    for s in multi_switches:
                        if s.get("outlet") == int(selected_switch):
                            return s.get("switch") == "on"

                return params.get("switch") == "on"

        return False

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True)
        ]

    def is_template_autoescaped(self):
        """Enable Jinja autoescaping for plugin templates."""
        return True

    def get_update_information(self):
        return dict(
            psucontrol_ewelink=dict(
                displayName="OctoPrint-PSUControl-eWeLink",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="chrismin13",
                repo="OctoPrint-PSUControl-eWeLink",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/chrismin13/OctoPrint-PSUControl-eWeLink/archive/{target_version}.zip"
            )
        )



def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PSUControlEWeLinkPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
