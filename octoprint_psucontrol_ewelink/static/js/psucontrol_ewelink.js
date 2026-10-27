/*
 * View model for OctoPrint-PSUControl-eWeLink
 *
 * Author: Christos Miniotis
 * License: MIT
 */

// This is a Knockout.js ViewModel that handles the Settings UI logic.
// It interacts with:
// 1. OctoPrint's Settings System (to save email, password, device_id)
// 2. The Python Backend (via SimpleApiCommand to fetch devices)
// 3. The Backend's `on_settings_save` hook (to handle password encryption)
$(function () {
    function PSUControlEWeLinkSettingsViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        // Use onBeforeBinding to ensure we receive the settings object after initialization
        // and mask the password
        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings;
            var pluginSettings = self.settings.plugins.psucontrol_ewelink;

            // Initial Masking
            // The backend stores the password in an encrypted format starting with "ENC:".
            // We never want to show this raw string to the user, nor do we want to show the actual password.
            // So, if a value exists, we immediately replace it with "********" (8 stars).
            // This tells the user "a password is set" without revealing it.
            if (pluginSettings.password()) {
                pluginSettings.password("********");
            }

            // Watch for updates (e.g. after save) to re-mask if ENC string comes back
            // When the user clicks "Save", the backend encrypts the password and updates the settings.
            // The updated settings (now containing "ENC:...") are pushed back to the frontend.
            // We catch this change and immediately re-mask it to "********".
            pluginSettings.password.subscribe(function (newValue) {
                if (newValue && newValue.indexOf("ENC:") === 0) {
                    pluginSettings.password("********");
                }
            });
        };

        self.deviceList = ko.observableArray([]);
        self.scanning = ko.observable(false);
        self.scanError = ko.observable("");
        self.scanSuccess = ko.observable("");

        // Check if the parent 'PSU Control' plugin is installed.
        // We need this because we rely on it for the actual UI buttons (navbar) and logic hooks.
        self.isPSUControlInstalled = ko.pureComputed(function () {
            return self.settingsViewModel.settings &&
                self.settingsViewModel.settings.plugins &&
                self.settingsViewModel.settings.plugins.psucontrol;
        });

        // Check if PSU Control is correctly configured to use THIS plugin.
        // The user must manually select 'PSUControl-eWeLink' in the PSU Control settings
        // for 'Switching Method' (and optionally 'Sensing Method').
        // If they haven't done this, our plugin won't actually do anything.
        self.isPSUControlConfigured = ko.pureComputed(function () {
            // Safety check: ensure settings and psucontrol plugin settings exist
            if (!self.isPSUControlInstalled()) {
                return true; // Don't show warning if we can't verify (or if PSUControl missing) -- handled by isPSUControlInstalled warning
            }

            var psu = self.settingsViewModel.settings.plugins.psucontrol;

            // Safety check for observables
            if (!psu.switchingMethod || !psu.switchingPlugin) {
                return true;
            }

            // 1. Verify Switching Method is set to PLUGIN and the plugin is US
            var switchingOk = psu.switchingMethod() === "PLUGIN" && psu.switchingPlugin() === "psucontrol_ewelink";

            // For sensing, also check if configured (optional but recommended)
            var sensingOk = true;
            if (psu.sensingMethod && psu.sensingPlugin) {
                // Only check if sensing is set to PLUGIN
                if (psu.sensingMethod() === "PLUGIN") {
                    sensingOk = psu.sensingPlugin() === "psucontrol_ewelink";
                }
            }

            return switchingOk && sensingOk;
        });

        self.isSensingConfigured = ko.pureComputed(function () {
            if (!self.settingsViewModel.settings ||
                !self.settingsViewModel.settings.plugins ||
                !self.settingsViewModel.settings.plugins.psucontrol) {
                return true;
            }
            var psu = self.settingsViewModel.settings.plugins.psucontrol;
            if (!psu.sensingMethod || !psu.sensingPlugin) {
                return true;
            }
            return psu.sensingMethod() === "PLUGIN" && psu.sensingPlugin() === "psucontrol_ewelink";
        });

        // "Test Connection" button handler.
        // It calls the backend API 'get_devices' to verify credentials and fetch the available devices.
        self.testConnection = function () {
            self.scanning(true);
            self.scanError("");
            self.scanSuccess("");
            self.deviceList([]);

            // safely access settings
            var pluginSettings = self.settingsViewModel.settings.plugins.psucontrol_ewelink;
            var email = pluginSettings.email();
            var password = pluginSettings.password();

            // Handle mask: if password is mask, send empty string to use stored password
            // If the user hasn't changed the password field, it will be "********".
            // We send "" to the backend, which tells it: "Use the password you already have stored/encrypted".
            // If the user *did* type a new password, we send that plaintext (over SSL/TLS) for verification.
            if (password === "********") {
                password = "";
            }

            if (!email) {
                // NOTE: Error message shown when email field is empty
                var err = gettext("Please enter Email.");
                self.scanError(err);
                self.scanning(false);
                new PNotify({ title: 'Error', text: err, type: 'error', text_escape: true });
                return;
            }

            // Call the 'get_devices' command in the 'SimpleApiPlugin' mixin of our __init__.py
            OctoPrint.simpleApiCommand("psucontrol_ewelink", "get_devices", {
                email: email,
                password: password
            })
                .done(function (response) {
                    if (response.error) {
                        self.scanError(response.error);
                        new PNotify({
                            // NOTE: Title of error notification
                            title: gettext('eWeLink Error'),
                            text: response.error,
                            type: 'error',
                            hide: false,
                            text_escape: true
                        });
                    } else if (response.devices) {
                        self.deviceList(response.devices);
                        // NOTE: Status message showing number of devices found
                        var successMsg = _.sprintf(gettext("Found %(count)d devices!"), { count: response.devices.length });
                        self.scanSuccess(successMsg);
                        new PNotify({
                            // NOTE: Title of success notification
                            title: gettext('eWeLink Connected'),
                            text: successMsg,
                            type: 'success',
                            text_escape: true
                        });
                    }
                })
                .fail(function (xhr) {
                    // NOTE: Generic error message when API request fails
                    var msg = gettext("API Request failed");
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        msg = xhr.responseJSON.error;
                    }
                    self.scanError(msg);
                    new PNotify({
                        // NOTE: Title of connection failure notification
                        title: gettext('Connection Failed'),
                        text: msg,
                        type: 'error',
                        hide: false,
                        text_escape: true
                    });
                })
                .always(function () {
                    self.scanning(false);
                });
        };

        // Choices for the "Outlet" dropdown.
        // "Automatic" is always offered. The outlets of the selected device are added once
        // "Test Connection / Get Devices" has listed them. Outlets are 0-based in the API,
        // but shown 1-based to match the eWeLink app.
        self.outletOptions = ko.pureComputed(function () {
            // NOTE: Outlet dropdown option that detects the outlet automatically
            var options = [{ value: -1, label: gettext("Automatic (recommended)") }];
            var pluginSettings = self.settingsViewModel.settings &&
                self.settingsViewModel.settings.plugins &&
                self.settingsViewModel.settings.plugins.psucontrol_ewelink;
            if (!pluginSettings) {
                return options;
            }

            var device = _.find(self.deviceList(), function (d) {
                return d.deviceid === pluginSettings.device_id();
            });
            var outlets = device && device.outlets ? device.outlets.slice() : [];

            // Keep a previously saved outlet selectable before the device list is loaded
            var current = parseInt(pluginSettings.selected_switch(), 10);
            if (current >= 0 && outlets.indexOf(current) === -1) {
                outlets.push(current);
                outlets.sort(function (a, b) { return a - b; });
            }

            _.each(outlets, function (outlet) {
                options.push({
                    value: outlet,
                    // NOTE: Outlet dropdown option, number starts at 1
                    label: _.sprintf(gettext("Outlet %(number)d"), { number: outlet + 1 })
                });
            });
            return options;
        });

        // When a user selects a device from the list, we update the setting immediately.
        self.selectDevice = function (device) {
            var pluginSettings = self.settingsViewModel.settings.plugins.psucontrol_ewelink;
            if (pluginSettings.device_id() !== device.deviceid) {
                // An outlet chosen for the previous device may not exist on this one
                pluginSettings.selected_switch(-1);
            }
            pluginSettings.device_id(device.deviceid);
            // Optionally verify selection
            new PNotify({
                // NOTE: Title of device selection notification
                title: gettext('Device Selected'),
                // NOTE: Notification text confirming device selection
                text: _.sprintf(gettext('Selected %(name)s (%(id)s)'), { name: device.name, id: device.deviceid }),
                type: 'info',
                text_escape: true
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PSUControlEWeLinkSettingsViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_psucontrol_ewelink"]
    });
});
