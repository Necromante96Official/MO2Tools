import configparser
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

try:
    from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
    from PyQt6.QtGui import QKeySequence
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PyQt5.QtCore import QEvent, QObject, Qt, QTimer
    from PyQt5.QtGui import QKeySequence
    from PyQt5.QtWidgets import QApplication


_logger = logging.getLogger("MO2Tools.VersionSync")
_logger.setLevel(logging.DEBUG)


def _qkeysequence_portable_text() -> int:
    try:
        return int(QKeySequence.SequenceFormat.PortableText)
    except Exception:
        return int(QKeySequence.PortableText)


def _qt_keypress_type() -> int:
    try:
        return int(QEvent.Type.KeyPress)
    except Exception:
        return int(QEvent.KeyPress)


def _enum_to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(value.value)
        except Exception:
            return 0


class _VersionFixShortcutFilter(QObject):
    def __init__(self, owner: "AutoVersionSync") -> None:
        super().__init__()
        self._owner = owner

    def eventFilter(self, _obj: Any, event: Any) -> bool:  # noqa: N802 (assinatura Qt)
        if event is None:
            return False

        if _enum_to_int(event.type()) != _qt_keypress_type():
            return False

        return self._owner._handle_shortcut_keypress(event)


def _parse_numeric_version(version_str: str) -> Optional[Tuple[int, ...]]:
    parts = str(version_str).split(".")
    numbers = []
    for part in parts:
        token = part.strip()
        if not token:
            return None
        try:
            numbers.append(int(token))
        except ValueError:
            return None

    while len(numbers) > 1 and numbers[-1] == 0:
        numbers.pop()

    return tuple(numbers)


class AutoVersionSync:
    def __init__(self, organizer: Any, plugin_name: str = "MO2Tools") -> None:
        self._organizer = organizer
        self._plugin_name = plugin_name
        self._timer: Optional[QTimer] = None
        self._shortcut_filter: Optional[_VersionFixShortcutFilter] = None
        self._last_shortcut_trigger_at = 0.0

        self._setup_timer()
        self._setup_shortcut_listener()

        if self._get_bool("autoVersionFixRunOnStartup", True):
            # Roda uma vez no startup do MO2 para correção imediata.
            QTimer.singleShot(1500, self.run_once)

    def _read_setting(self, key: str, default: Any) -> Any:
        if not self._organizer:
            return default
        try:
            value = self._organizer.pluginSetting(self._plugin_name, key)
        except Exception:
            return default
        return default if value is None else value

    def _get_bool(self, key: str, default: bool) -> bool:
        value = self._read_setting(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "sim"}
        return default

    def _get_int(self, key: str, default: int) -> int:
        value = self._read_setting(key, default)
        try:
            parsed = int(value)
            return parsed if parsed > 0 else default
        except Exception:
            return default

    def _setup_timer(self) -> None:
        if self._timer is not None:
            try:
                self._timer.stop()
                self._timer.deleteLater()
            except Exception:
                pass

        interval_minutes = self._get_int("autoVersionFixIntervalMinutes", 10)
        self._timer = QTimer()
        self._timer.setInterval(max(1, interval_minutes) * 60 * 1000)
        self._timer.timeout.connect(self.run_once)
        self._timer.start()

    def reload_from_settings(self) -> None:
        self._setup_timer()
        self._setup_shortcut_listener()

    def _read_shortcut(self) -> str:
        value = self._read_setting("versionFixShortcut", "Ctrl+Shift+Z")
        text = str(value or "").strip()
        return text if text else "Ctrl+Shift+Z"

    def _normalize_shortcut_text(self, text: str) -> str:
        shortcut_text = str(text or "").strip()
        if not shortcut_text:
            return ""
        try:
            fmt = _qkeysequence_portable_text()
            return str(QKeySequence.fromString(shortcut_text, fmt).toString(fmt)).strip().lower()
        except Exception:
            try:
                return str(QKeySequence(shortcut_text).toString()).strip().lower()
            except Exception:
                return shortcut_text.lower()

    def _setup_shortcut_listener(self) -> None:
        app = QApplication.instance()
        if app is None:
            _logger.debug(
                "Atalho Version Fix pendente: QApplication ainda não está pronta.")
            QTimer.singleShot(1200, self._setup_shortcut_listener)
            return

        if self._shortcut_filter is not None:
            return

        try:
            self._shortcut_filter = _VersionFixShortcutFilter(self)
            app.installEventFilter(self._shortcut_filter)
            _logger.info("Listener global de atalho do Version Fix ativado.")
        except Exception as exc:
            _logger.warning(
                "Falha ao ativar listener global de atalho: %s", exc)

    def _handle_shortcut_keypress(self, event: Any) -> bool:
        if not self._get_bool("enabled", True):
            return False
        if not self._get_bool("autoVersionFixEnabled", True):
            return False
        if not self._get_bool("versionFixShortcutEnabled", True):
            return False

        key_code = _enum_to_int(event.key())
        try:
            modifier_only = {
                _enum_to_int(Qt.Key.Key_Control),
                _enum_to_int(Qt.Key.Key_Shift),
                _enum_to_int(Qt.Key.Key_Alt),
                _enum_to_int(Qt.Key.Key_Meta),
            }
        except Exception:
            modifier_only = {
                _enum_to_int(Qt.Key_Control),
                _enum_to_int(Qt.Key_Shift),
                _enum_to_int(Qt.Key_Alt),
                _enum_to_int(Qt.Key_Meta),
            }
        if key_code in modifier_only:
            return False

        target_shortcut = self._normalize_shortcut_text(self._read_shortcut())
        if not target_shortcut:
            return False

        combo_value = _enum_to_int(event.modifiers()) | key_code
        try:
            fmt = _qkeysequence_portable_text()
            pressed_shortcut = str(QKeySequence(
                combo_value).toString(fmt)).strip().lower()
        except Exception:
            pressed_shortcut = str(QKeySequence(
                combo_value).toString()).strip().lower()

        if pressed_shortcut != target_shortcut:
            return False

        now = time.time()
        if (now - self._last_shortcut_trigger_at) < 0.55:
            return True
        self._last_shortcut_trigger_at = now

        _logger.info(
            "Atalho do Version Fix acionado | shortcut=%s",
            self._read_shortcut(),
        )
        QTimer.singleShot(0, self.trigger_now)
        return True

    def trigger_now(self) -> None:
        self.run_once()

    def run_once(self) -> None:
        if not self._get_bool("enabled", True):
            return
        if not self._get_bool("autoVersionFixEnabled", True):
            return

        mods_root = ""
        try:
            mods_root = str(self._organizer.modsPath() or "")
        except Exception:
            mods_root = ""

        if not mods_root or not os.path.isdir(mods_root):
            _logger.warning("AutoVersionSync: caminho de mods inválido.")
            return

        stats: Dict[str, int] = {
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "missing_meta": 0,
            "missing_newest": 0,
        }

        create_backup = self._get_bool("autoVersionFixCreateBackup", True)

        for item in os.listdir(mods_root):
            mod_dir = os.path.join(mods_root, item)
            if not os.path.isdir(mod_dir):
                continue

            stats["processed"] += 1
            meta_ini = os.path.join(mod_dir, "meta.ini")
            if not os.path.isfile(meta_ini):
                stats["missing_meta"] += 1
                stats["skipped"] += 1
                continue

            parser = configparser.ConfigParser()
            try:
                parser.read(meta_ini, encoding="utf-8")
            except Exception:
                stats["errors"] += 1
                continue

            if "General" not in parser:
                stats["skipped"] += 1
                continue

            general = parser["General"]
            current_version = (general.get("version", "")
                               or "").strip() or "0.0.0"
            newest_version = (general.get("newestVersion", "") or "").strip()

            if not newest_version:
                stats["missing_newest"] += 1
                stats["skipped"] += 1
                continue

            current_tuple = _parse_numeric_version(current_version)
            newest_tuple = _parse_numeric_version(newest_version)

            if current_tuple is None or newest_tuple is None:
                mismatch = current_version != newest_version
            else:
                mismatch = current_tuple != newest_tuple

            if not mismatch:
                stats["skipped"] += 1
                continue

            general["version"] = newest_version

            if create_backup:
                try:
                    backup_path = meta_ini + ".bak"
                    if not os.path.exists(backup_path):
                        with open(meta_ini, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                            dst.write(src.read())
                except Exception:
                    # Backup é melhor esforço, não deve bloquear a correção.
                    pass

            try:
                with open(meta_ini, "w", encoding="utf-8") as file_obj:
                    parser.write(file_obj)
                stats["updated"] += 1
            except Exception:
                stats["errors"] += 1

        if stats["updated"] > 0 and self._get_bool("autoVersionFixRefreshAfterRun", True):
            try:
                self._organizer.refresh(True)
            except Exception:
                pass

        _logger.info(
            "AutoVersionSync concluído | processed=%s updated=%s skipped=%s errors=%s missing_meta=%s missing_newest=%s",
            stats["processed"],
            stats["updated"],
            stats["skipped"],
            stats["errors"],
            stats["missing_meta"],
            stats["missing_newest"],
        )
