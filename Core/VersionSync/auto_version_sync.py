import configparser
import logging
import os
from typing import Any, Dict, Optional, Tuple

try:
    from PyQt6.QtCore import QTimer
except ImportError:
    from PyQt5.QtCore import QTimer


_logger = logging.getLogger("MO2Tools.VersionSync")
_logger.setLevel(logging.DEBUG)


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

        self._setup_timer()

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
        interval_minutes = self._get_int("autoVersionFixIntervalMinutes", 10)
        self._timer = QTimer()
        self._timer.setInterval(max(1, interval_minutes) * 60 * 1000)
        self._timer.timeout.connect(self.run_once)
        self._timer.start()

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
