# Changelog

All notable changes to this project are documented in this file.

## [1.0.16] - 2026-10-28

### Added
- **Outlet** setting for devices with more than one output. Defaults to **Automatic**; the outlets of the selected device are listed after clicking **Test Connection / Get Devices** (based on [#2](https://github.com/chrismin13/OctoPrint-PSUControl-eWeLink/pull/2) by @fleury08).
- `get_devices` API now returns each device's `outlets`.

### Fixed
- Switching and state sensing for devices that report their state as a `switches` list instead of a single `switch` value, such as the SONOFF BASICR4 and S60TPF ([#3](https://github.com/chrismin13/OctoPrint-PSUControl-eWeLink/issues/3), [#5](https://github.com/chrismin13/OctoPrint-PSUControl-eWeLink/issues/5)). These devices previously failed with error `4002` and always showed as OFF. Devices using the single `switch` value (e.g. BASIC R2) behave as before.
- Errors while polling the device state are now logged at debug level instead of being discarded.

## [1.0.15] - 2026-05-08

### Fixed
- Declared `SimpleApiPlugin.is_api_protected()` to require authenticated API access and avoid OctoPrint 1.11.2+ warnings.
- Enabled `TemplatePlugin.is_template_autoescaped()` for safer Jinja rendering and OctoPrint 2.0 readiness.

## [1.0.14] - 2026-01-21

### Changed
- Refactored plugin initialization to use `__init__` with `super().__init__()` instead of `initialize()`, following Python best practices.

## [1.0.13] - 2026-01-18

### Fixed
- **Critical**: Re-bundled all translations (Greek & French) to ensure they are included in the release zip.
- Updated `TRANSLATIONS.md` with explicit release instructions to prevent future missing file issues.

## [1.0.12] - 2026-01-18

### Added
- French (`fr`) translation.

### Fixed
- Updated Greek (`el`) translation.

## [1.0.11] - 2026-01-18

### Fixed
- Fixed incomplete release 1.0.10 (missed committing modified source files).
- Ensuring all translation source files and compilation artifacts are included.

## [1.0.10] - 2026-01-18

### Fixed
- Fixed missing Greek translations in the packaged plugin by including compiled `.mo` files.

## [1.0.9] - 2026-01-18

### Fixed
- Migrated plugin initialization from `__init__` to `initialize` to correct inheritance issues with `TranslationPlugin`.
- Fixed "Plugin disappeared" issue caused by overridden constructor.

> **Note:** `TranslationPlugin` does not exist in OctoPrint—this was an AI hallucination. These changes did not fix the underlying issue.

## [1.0.8] - 2026-01-18

### Fixed
- Fixed missing `TranslationPlugin` inheritance, which prevented translations from loading.

> **Note:** `TranslationPlugin` does not exist in OctoPrint—this was an AI hallucination. This change did not fix anything.

## [1.0.7] - 2026-01-18

### Added
- **Internationalization (i18n)** infrastructure:
    - Added `babel.cfg` and `Taskfile.yml` for translation management.
    - Marked all user-facing strings for translation in Python, JavaScript, and Jinja2 files.
    - Added Greek (`el`) translation.
- **Documentation**:
    - Added comprehensive [Translation Guide](TRANSLATIONS.md).
    - Standardized documentation footers and cross-linking.
    - Added "Translations" to README and DEVELOPMENT guides.

### Changed
- Improved context comments in source code to aid future translators.
- Updated `MANIFEST.in` to include translation files and documentation.

### Fixed
- Fixed duplicate legend tag in settings template.

## [1.0.6] - 2026-01-18

### Added
- **EditorConfig** - Added `.editorconfig` for consistent code style across editors
- **MANIFEST.in** - Added manifest file for proper PyPI source distribution packaging
- **GitHub Issue Templates** - Added structured bug report and feature request forms
- **Modern Packaging** - Migrated from `setup.py` to `pyproject.toml` (PEP 517/518)

### Changed
- **Version Location** - Version now in `pyproject.toml` (line 7) instead of `setup.py`

### Maintenance
- **Code Style** - Fixed all files for editorconfig compliance (trailing whitespace, tabs→spaces, indentation)
- **Documentation** - Updated README and project-context workflow to reflect pyproject.toml migration

## [1.0.4] - 2026-01-16

### Security
- **API Protection** - Added `is_api_adminonly()` to restrict API access to admin users only
- **XSS Prevention** - Added `text_escape: true` to all PNotify notifications to prevent XSS from untrusted cloud data (device names, error messages)

### Changed
- **Terminology** - Rebranded "encryption" to "obfuscation" throughout documentation to honestly describe XOR-based password protection

### Documentation
- **README** - Added release process instructions
- **SECURITY.md** - Clarified that storage protection prevents casual exposure, not targeted attacks

## [1.0.3] - 2026-01-07

### Maintenance
- **Repository** - Prepared for official plugin repository submission.
- **Metadata** - Added privacy policy links and screenshots to registration data.
- **Packaging** - Cleaned up `setup.py` and `MANIFEST.in`.

## [1.0.1] - 2026-01-06

### Fixed
- **Configuration** - Added a prominent error message when the required `OctoPrint-PSUControl` plugin is missing.
- **Documentation** - Updated troubleshooting guide with "Missing Requirement" error.

## [1.0.0] - 2026-01-06

Initial public release.

### Features
- **eWeLink Cloud Integration** - Control any eWeLink-compatible smart switch (Sonoff Basic, S26, etc.)
- **Device Discovery** - Test connection and browse devices directly in OctoPrint settings
- **State Sensing** - Real-time feedback on switch state through PSU Control
- **Secure Credentials** - Passwords obfuscated locally using XOR with unique salt
- **Region Auto-Detection** - No manual region configuration needed; API automatically detects correct region
- **Password Masking** - UI shows `********` instead of real password
- **Configuration Warnings** - Alerts if PSU Control not properly configured to use this plugin

### Technical
- Asyncio bridge for eWeLink library
- Background thread for event loop
- POST-based API for secure credential handling
- Software update support via OctoPrint's update mechanism

### Documentation
- Complete documentation suite: README, SECURITY, TROUBLESHOOTING, API, ARCHITECTURE, DEVELOPMENT

---

📚 **More docs:** [README](../README.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Security](SECURITY.md) · [API](API.md) · [Architecture](ARCHITECTURE.md) · [Development](DEVELOPMENT.md) · [Translations](TRANSLATIONS.md)
- Privacy Policy for cloud service usage
