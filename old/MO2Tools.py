import os
import json
import time
import queue
import logging
import configparser
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import mobase

try:
    from PyQt6.QtCore import QCoreApplication, Qt, QTimer
    from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QCheckBox,
        QPushButton,
        QMessageBox,
        QProgressDialog,
        QGroupBox,
        QDialogButtonBox,
        QComboBox,
        QRadioButton,
        QAbstractButton,
    )
    _QT6 = True
except ImportError:
    from PyQt5.QtCore import QCoreApplication, Qt, QTimer
    from PyQt5.QtGui import QIcon, QKeySequence
    from PyQt5.QtWidgets import (
        QApplication,
        QWidget,
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QCheckBox,
        QPushButton,
        QMessageBox,
        QProgressDialog,
        QGroupBox,
        QDialogButtonBox,
        QComboBox,
        QRadioButton,
        QAbstractButton,
        QShortcut,
    )
    _QT6 = False


_logger = logging.getLogger("MO2Tools")
_logger.setLevel(logging.DEBUG)


def _parse_numeric_version(v_str: str) -> Optional[tuple]:
    parts = str(v_str).split(".")
    numbers: List[int] = []
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


def _norm_path(path_value: str) -> str:
    return os.path.normcase(os.path.normpath(str(path_value).strip()))


class ActionCache:
    def __init__(self, cache_path: str) -> None:
        self.cache_path = cache_path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as file_obj:
                    raw = json.load(file_obj)
                    if isinstance(raw, dict):
                        raw.setdefault("endorsed_mods", {})
                        raw.setdefault("tracked_mods", {})
                        raw.setdefault("stats", {"endorse": 0, "track": 0})
                        raw.setdefault("last_action", None)
                        return raw
        except Exception as exc:
            _logger.warning(f"Falha ao carregar cache de ações: {exc}")

        return {
            "endorsed_mods": {},
            "tracked_mods": {},
            "stats": {"endorse": 0, "track": 0},
            "last_action": None,
        }

    def _save(self) -> None:
        try:
            parent = os.path.dirname(self.cache_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as file_obj:
                json.dump(self.data, file_obj, indent=2, ensure_ascii=False)
        except Exception as exc:
            _logger.error(f"Falha ao salvar cache de ações: {exc}")

    def is_done(self, action: str, mod_id: int) -> bool:
        key = str(int(mod_id))
        if action == "endorse":
            return key in self.data.get("endorsed_mods", {})
        if action == "track":
            return key in self.data.get("tracked_mods", {})
        return False

    def mark_done(self, action: str, mod_id: int, mod_name: str) -> None:
        payload = {
            "name": str(mod_name),
            "timestamp": datetime.now().isoformat(),
        }

        key = str(int(mod_id))
        if action == "endorse":
            self.data.setdefault("endorsed_mods", {})[key] = payload
        elif action == "track":
            self.data.setdefault("tracked_mods", {})[key] = payload
        else:
            return

        stats = self.data.setdefault("stats", {"endorse": 0, "track": 0})
        stats[action] = int(stats.get(action, 0)) + 1
        self.data["last_action"] = datetime.now().isoformat()
        self._save()


class MO2ToolsDialog(QDialog):
    def __init__(self, plugin: "MO2Tools", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle("MO2Tools - Painel")
        self.setMinimumWidth(640)

        if _QT6:
            self.setWindowFlag(Qt.WindowType.Tool, True)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.Tool)

        root = QVBoxLayout(self)

        title = QLabel("MO2Tools")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        subtitle = QLabel("Central unificada para automação estável no MO2.")
        root.addWidget(title)
        root.addWidget(subtitle)

        group_auto = QGroupBox("Automações")
        group_auto_layout = QVBoxLayout(group_auto)

        self.cb_plugin_enabled = QCheckBox("Habilitar MO2Tools")
        self.cb_auto_activate = QCheckBox("Ativação automática de mod instalado")
        self.cb_auto_install = QCheckBox("Instalação automática ao concluir download")
        self.cb_fast_install = QCheckBox("Instalação rápida automática")
        self.cb_auto_replace = QCheckBox("Repor automaticamente se o mod já existir")
        self.cb_version_sync = QCheckBox("Sincronizar versão automaticamente no pós-instalação")
        self.cb_endorse = QCheckBox("Habilitar apoio em lote")
        self.cb_track = QCheckBox("Habilitar seguir mods em lote")
        self.cb_cache = QCheckBox("Usar cache para evitar ações repetidas")
        self.cb_progress = QCheckBox("Exibir progresso nas ações em lote")

        for checkbox in [
            self.cb_plugin_enabled,
            self.cb_auto_activate,
            self.cb_auto_install,
            self.cb_fast_install,
            self.cb_auto_replace,
            self.cb_version_sync,
            self.cb_endorse,
            self.cb_track,
            self.cb_cache,
            self.cb_progress,
        ]:
            group_auto_layout.addWidget(checkbox)

        root.addWidget(group_auto)

        group_shortcuts = QGroupBox("Atalhos")
        group_shortcuts_layout = QVBoxLayout(group_shortcuts)

        self.shortcut_open = self._shortcut_line("Abrir painel", group_shortcuts_layout)
        self.shortcut_fix = self._shortcut_line("Sincronizar versões", group_shortcuts_layout)
        self.shortcut_endorse = self._shortcut_line("Apoiar todos", group_shortcuts_layout)
        self.shortcut_track = self._shortcut_line("Seguir todos", group_shortcuts_layout)

        root.addWidget(group_shortcuts)

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("Salvar")
        self.btn_fix_now = QPushButton("Sincronizar versões agora")
        self.btn_endorse_now = QPushButton("Apoiar todos agora")
        self.btn_track_now = QPushButton("Seguir todos agora")
        self.btn_close = QPushButton("Fechar")

        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_fix_now)
        buttons.addWidget(self.btn_endorse_now)
        buttons.addWidget(self.btn_track_now)
        buttons.addWidget(self.btn_close)

        root.addLayout(buttons)

        self.btn_save.clicked.connect(self._on_save)
        self.btn_fix_now.clicked.connect(self.plugin.run_version_fix_all)
        self.btn_endorse_now.clicked.connect(self.plugin.endorse_all)
        self.btn_track_now.clicked.connect(self.plugin.track_all)
        self.btn_close.clicked.connect(self.close)

        self._load_values()

    def _shortcut_line(self, label: str, layout: QVBoxLayout) -> QLineEdit:
        row = QHBoxLayout()
        row_label = QLabel(label)
        row_edit = QLineEdit()
        row_edit.setPlaceholderText("Ex.: Ctrl+Alt+V")
        row.addWidget(row_label)
        row.addWidget(row_edit)
        layout.addLayout(row)
        return row_edit

    def _load_values(self) -> None:
        self.cb_plugin_enabled.setChecked(self.plugin._get_bool("pluginEnabled", True))
        self.cb_auto_activate.setChecked(self.plugin._get_bool("autoActivatorEnabled", True))
        self.cb_auto_install.setChecked(self.plugin._get_bool("autoInstallerEnabled", True))
        self.cb_fast_install.setChecked(self.plugin._get_bool("fastInstallEnabled", True))
        self.cb_auto_replace.setChecked(self.plugin._get_bool("autoReplaceEnabled", True))
        self.cb_version_sync.setChecked(self.plugin._get_bool("versionFixOnInstall", True))
        self.cb_endorse.setChecked(self.plugin._get_bool("endorseFeatureEnabled", True))
        self.cb_track.setChecked(self.plugin._get_bool("trackFeatureEnabled", True))
        self.cb_cache.setChecked(self.plugin._get_bool("useActionCache", True))
        self.cb_progress.setChecked(self.plugin._get_bool("showProgressDialogs", True))

        self.shortcut_open.setText(self.plugin._get_str("shortcutOpenPanel", "Ctrl+Alt+M"))
        self.shortcut_fix.setText(self.plugin._get_str("shortcutFixVersion", "Ctrl+Alt+V"))
        self.shortcut_endorse.setText(self.plugin._get_str("shortcutEndorseAll", "Ctrl+Alt+E"))
        self.shortcut_track.setText(self.plugin._get_str("shortcutTrackAll", "Ctrl+Alt+T"))

    def _on_save(self) -> None:
        self.plugin._set_setting("pluginEnabled", self.cb_plugin_enabled.isChecked())
        self.plugin._set_setting("autoActivatorEnabled", self.cb_auto_activate.isChecked())
        self.plugin._set_setting("autoInstallerEnabled", self.cb_auto_install.isChecked())
        self.plugin._set_setting("fastInstallEnabled", self.cb_fast_install.isChecked())
        self.plugin._set_setting("autoReplaceEnabled", self.cb_auto_replace.isChecked())
        self.plugin._set_setting("versionFixOnInstall", self.cb_version_sync.isChecked())
        self.plugin._set_setting("endorseFeatureEnabled", self.cb_endorse.isChecked())
        self.plugin._set_setting("trackFeatureEnabled", self.cb_track.isChecked())
        self.plugin._set_setting("useActionCache", self.cb_cache.isChecked())
        self.plugin._set_setting("showProgressDialogs", self.cb_progress.isChecked())

        self.plugin._set_setting("shortcutOpenPanel", self.shortcut_open.text().strip())
        self.plugin._set_setting("shortcutFixVersion", self.shortcut_fix.text().strip())
        self.plugin._set_setting("shortcutEndorseAll", self.shortcut_endorse.text().strip())
        self.plugin._set_setting("shortcutTrackAll", self.shortcut_track.text().strip())

        self.plugin.rebind_shortcuts()
        QMessageBox.information(self, "MO2Tools", "Configurações salvas com sucesso.")


class MO2Tools(mobase.IPluginTool):
    def __init__(self) -> None:
        super().__init__()
        self._organizer: Optional[mobase.IOrganizer] = None
        self._parent_widget: Optional[QWidget] = None

        self._plugin_path = os.path.dirname(os.path.realpath(__file__))
        self._icons = {
            "on": os.path.join(self._plugin_path, "green.ico"),
            "off": os.path.join(self._plugin_path, "red.ico"),
        }

        self._dialog: Optional[MO2ToolsDialog] = None
        self._shortcuts: List[QShortcut] = []

        self._download_manager: Optional[mobase.IDownloadManager] = None
        self._download_hook_registered = False

        self._install_queue: "queue.Queue[str]" = queue.Queue()
        self._installing = False

        self._pending_install_paths: set[str] = set()
        self._inflight_install_paths: set[str] = set()
        self._recent_install_paths: Dict[str, float] = {}
        self._recent_download_ids: Dict[int, float] = {}

        self._installed_events_by_path: Dict[str, float] = {}
        self._installed_events_by_name: Dict[str, float] = {}

        self._install_dedupe_ttl_seconds = 240.0
        self._download_dedupe_ttl_seconds = 360.0
        self._installed_event_ttl_seconds = 600.0

        self._active_dialog_timers: List[QTimer] = []
        self._manual_install_items: List[Dict[str, str]] = []

        self._cache = ActionCache(os.path.join(self._plugin_path, "actions_cache.json"))

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer

        try:
            self._download_manager = organizer.downloadManager()
            if self._download_manager and not self._download_hook_registered:
                self._download_manager.onDownloadComplete(self._on_download_complete)
                self._download_hook_registered = True
        except Exception as exc:
            _logger.warning(f"Falha ao conectar onDownloadComplete: {exc}")

        try:
            organizer.modList().onModInstalled(self._on_mod_installed)
        except Exception as exc:
            _logger.warning(f"Falha ao conectar onModInstalled: {exc}")

        return True

    def name(self) -> str:
        return "MO2Tools"

    def localizedName(self) -> str:
        return self.tr("MO2Tools")

    def displayName(self) -> str:
        return self.tr("MO2Tools")

    def author(self) -> str:
        return "MO2Tools Team"

    def description(self) -> str:
        return self.tr(
            "Central robusta de automação: instalação, ativação, sincronização de versões, apoio e seguimento em lote."
        )

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def isActive(self) -> bool:
        return True

    def settings(self) -> List[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("pluginEnabled", "Habilita o MO2Tools", True),
            mobase.PluginSetting("autoActivatorEnabled", "Ativação automática ao instalar mod", True),
            mobase.PluginSetting("autoInstallerEnabled", "Instalação automática após download", True),
            mobase.PluginSetting("fastInstallEnabled", "Instalação rápida automática", True),
            mobase.PluginSetting("autoReplaceEnabled", "Repor automaticamente em conflito de mod existente", True),
            mobase.PluginSetting("versionFixOnInstall", "Sincroniza versão após instalar", True),
            mobase.PluginSetting("endorseFeatureEnabled", "Habilita apoio em lote", True),
            mobase.PluginSetting("trackFeatureEnabled", "Habilita seguir mods em lote", True),
            mobase.PluginSetting("useActionCache", "Usa cache para evitar repetir ações", True),
            mobase.PluginSetting("showProgressDialogs", "Mostra barra de progresso", True),

            mobase.PluginSetting("shortcutOpenPanel", "Atalho para abrir painel", "Ctrl+Alt+M"),
            mobase.PluginSetting("shortcutFixVersion", "Atalho para sincronizar versões", "Ctrl+Alt+V"),
            mobase.PluginSetting("shortcutEndorseAll", "Atalho para apoiar todos", "Ctrl+Alt+E"),
            mobase.PluginSetting("shortcutTrackAll", "Atalho para seguir todos", "Ctrl+Alt+T"),
        ]

    def tooltip(self) -> str:
        return self.tr("Abrir painel do MO2Tools")

    def icon(self) -> QIcon:
        enabled = self._get_bool("pluginEnabled", True)
        icon_path = self._icons["on"] if enabled else self._icons["off"]
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()

    def setParentWidget(self, widget: QWidget) -> None:
        self._parent_widget = widget
        self.rebind_shortcuts()

    def display(self) -> None:
        self._open_panel()

    def tr(self, text: str) -> str:
        return QCoreApplication.translate("MO2Tools", text)

    def _open_panel(self) -> None:
        parent = self._parent_widget if self._parent_widget else None

        if self._dialog is None:
            self._dialog = MO2ToolsDialog(plugin=self, parent=parent)

        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    def _get_setting(self, key: str, default: Any) -> Any:
        if not self._organizer:
            return default
        try:
            value = self._organizer.pluginSetting(self.name(), key)
            return default if value is None else value
        except Exception:
            return default

    def _set_setting(self, key: str, value: Union[str, int, bool]) -> None:
        if not self._organizer:
            return
        try:
            self._organizer.setPluginSetting(self.name(), key, value)
        except Exception as exc:
            _logger.error(f"Erro ao salvar configuração {key}: {exc}")

    def _get_bool(self, key: str, default: bool) -> bool:
        value = self._get_setting(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "sim"}
        return default

    def _get_str(self, key: str, default: str) -> str:
        value = self._get_setting(key, default)
        return value if isinstance(value, str) else str(value)

    def rebind_shortcuts(self) -> None:
        for shortcut in self._shortcuts:
            try:
                shortcut.setParent(None)
                shortcut.deleteLater()
            except Exception:
                pass
        self._shortcuts = []

        if not self._parent_widget:
            return

        self._bind_shortcut(self._get_str("shortcutOpenPanel", "Ctrl+Alt+M"), self._open_panel)

        if self._get_bool("pluginEnabled", True):
            self._bind_shortcut(self._get_str("shortcutFixVersion", "Ctrl+Alt+V"), self.run_version_fix_all)
            if self._get_bool("endorseFeatureEnabled", True):
                self._bind_shortcut(self._get_str("shortcutEndorseAll", "Ctrl+Alt+E"), self.endorse_all)
            if self._get_bool("trackFeatureEnabled", True):
                self._bind_shortcut(self._get_str("shortcutTrackAll", "Ctrl+Alt+T"), self.track_all)

    def _bind_shortcut(self, sequence_text: str, callback: Any) -> None:
        sequence = sequence_text.strip()
        if not sequence:
            return

        key_sequence = QKeySequence(sequence)
        if key_sequence.isEmpty():
            _logger.warning(f"Atalho inválido ignorado: '{sequence_text}'")
            return

        shortcut = QShortcut(key_sequence, self._parent_widget)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)

    def _on_mod_installed(self, mod: mobase.IModInterface) -> None:
        self._record_install_event(mod)

        if not self._get_bool("pluginEnabled", True):
            return

        if self._get_bool("autoActivatorEnabled", True):
            self._auto_activate_mod(mod)

        if self._get_bool("versionFixOnInstall", True):
            self._fix_version_with_fallback(mod)

    def _record_install_event(self, mod: mobase.IModInterface) -> None:
        now = time.time()
        self._prune_recent_map(self._installed_events_by_path, now, self._installed_event_ttl_seconds)
        self._prune_recent_map(self._installed_events_by_name, now, self._installed_event_ttl_seconds)

        try:
            install_file = str(mod.installationFile() or "").strip()
            if install_file:
                normalized = _norm_path(install_file)
                self._installed_events_by_path[normalized] = now

                name_only = os.path.basename(normalized)
                if name_only:
                    self._installed_events_by_name[name_only] = now
        except Exception:
            pass

    def _auto_activate_mod(self, mod: mobase.IModInterface) -> None:
        if not self._organizer:
            return
        try:
            self._organizer.modList().setActive(name=mod.name(), active=True)
        except Exception as exc:
            _logger.warning(f"Falha ao auto ativar '{mod.name()}': {exc}")

    def _on_download_complete(self, download_id: int) -> None:
        if not self._get_bool("pluginEnabled", True):
            return
        if not self._get_bool("autoInstallerEnabled", True):
            return
        if not self._download_manager:
            return

        if self._is_duplicate_download_event(download_id):
            return

        try:
            archive_path = self._download_manager.downloadPath(download_id)
        except Exception as exc:
            _logger.warning(f"Falha ao obter caminho do download {download_id}: {exc}")
            return

        if not archive_path:
            return

        if not self._enqueue_install_path(str(archive_path)):
            return

        self._process_install_queue()

    def _is_duplicate_download_event(self, download_id: int) -> bool:
        now = time.time()
        self._prune_recent_map(self._recent_download_ids, now, self._download_dedupe_ttl_seconds)

        if download_id in self._recent_download_ids:
            return True

        self._recent_download_ids[download_id] = now
        return False

    def _enqueue_install_path(self, archive_path: str) -> bool:
        normalized = _norm_path(archive_path)
        now = time.time()

        self._prune_recent_map(self._recent_install_paths, now, self._install_dedupe_ttl_seconds)

        if normalized in self._pending_install_paths:
            return False

        if normalized in self._inflight_install_paths:
            return False

        last_seen = self._recent_install_paths.get(normalized)
        if last_seen is not None and (now - last_seen) < self._install_dedupe_ttl_seconds:
            return False

        self._pending_install_paths.add(normalized)
        self._install_queue.put(normalized)
        return True

    def _mark_recent_install(self, archive_path: str) -> None:
        self._recent_install_paths[_norm_path(archive_path)] = time.time()

    def _prune_recent_map(self, cache: Dict[Any, float], now: float, ttl_seconds: float) -> None:
        expired = [key for key, timestamp in cache.items() if (now - timestamp) >= ttl_seconds]
        for key in expired:
            cache.pop(key, None)

    def _process_install_queue(self) -> None:
        if self._installing:
            return
        if not self._organizer:
            return

        self._installing = True
        try:
            while not self._install_queue.empty():
                archive_path = self._install_queue.get()
                normalized = _norm_path(archive_path)

                if normalized in self._inflight_install_paths:
                    continue

                self._pending_install_paths.discard(normalized)
                self._inflight_install_paths.add(normalized)
                try:
                    success = self._install_archive(archive_path)
                    if not success:
                        self._queue_manual_install(
                            archive_path,
                            "Falha no fluxo automático; necessário confirmar manualmente.",
                        )
                except Exception as exc:
                    _logger.error(f"Falha ao instalar '{archive_path}': {exc}")
                    self._queue_manual_install(archive_path, f"Erro interno durante instalação: {exc}")
                finally:
                    self._mark_recent_install(archive_path)
                    self._inflight_install_paths.discard(normalized)
        finally:
            self._installing = False
            self._flush_manual_install_notice()

    def _install_archive(self, archive_path: str) -> bool:
        if not self._organizer:
            return False

        fast_install = self._get_bool("fastInstallEnabled", True)
        auto_replace = self._get_bool("autoReplaceEnabled", True)

        first_try = self._run_install_attempt(
            archive_path,
            enable_fast_mode=fast_install,
            enable_auto_replace=auto_replace,
            timeout_seconds=6.0,
        )
        if first_try:
            return True

        second_try = self._run_install_attempt(
            archive_path,
            enable_fast_mode=True,
            enable_auto_replace=auto_replace,
            timeout_seconds=8.0,
        )
        return second_try

    def _run_install_attempt(
        self,
        archive_path: str,
        enable_fast_mode: bool,
        enable_auto_replace: bool,
        timeout_seconds: float,
    ) -> bool:
        if not self._organizer:
            return False

        started_at = time.time()
        timer = self._start_install_assistant(
            timeout_seconds=timeout_seconds,
            enable_fast_mode=enable_fast_mode,
            enable_auto_replace=enable_auto_replace,
        )

        installed_mod = None
        try:
            try:
                installed_mod = self._organizer.installMod(archive_path, "")
            except TypeError:
                installed_mod = self._organizer.installMod(archive_path)

            self._auto_confirm_install_dialog(
                timeout_seconds=1.4,
                enable_fast_mode=enable_fast_mode,
                enable_auto_replace=enable_auto_replace,
            )
        except Exception as exc:
            _logger.debug(f"Tentativa de instalação falhou para '{archive_path}': {exc}")
        finally:
            self._stop_install_assistant(timer)

        if installed_mod is not None:
            return True

        return self._was_archive_installed_recently(archive_path, started_at - 0.5)

    def _was_archive_installed_recently(self, archive_path: str, since_ts: float) -> bool:
        now = time.time()
        self._prune_recent_map(self._installed_events_by_path, now, self._installed_event_ttl_seconds)
        self._prune_recent_map(self._installed_events_by_name, now, self._installed_event_ttl_seconds)

        normalized = _norm_path(archive_path)
        by_path = self._installed_events_by_path.get(normalized)
        if by_path is not None and by_path >= since_ts:
            return True

        base_name = os.path.basename(normalized)
        by_name = self._installed_events_by_name.get(base_name)
        if by_name is not None and by_name >= since_ts:
            return True

        return False

    def _start_install_assistant(
        self,
        timeout_seconds: float,
        enable_fast_mode: bool,
        enable_auto_replace: bool,
    ) -> QTimer:
        timer = QTimer(self._parent_widget)
        timer.setInterval(90)
        started_at = time.time()

        def _on_tick() -> None:
            self._scan_install_dialogs(enable_fast_mode=enable_fast_mode, enable_auto_replace=enable_auto_replace)
            if (time.time() - started_at) >= max(0.8, timeout_seconds):
                self._stop_install_assistant(timer)

        timer.timeout.connect(_on_tick)
        self._active_dialog_timers.append(timer)
        timer.start()
        return timer

    def _stop_install_assistant(self, timer: Optional[QTimer]) -> None:
        if timer is None:
            return
        try:
            timer.stop()
            timer.deleteLater()
        except Exception:
            pass
        if timer in self._active_dialog_timers:
            self._active_dialog_timers.remove(timer)

    def _auto_confirm_install_dialog(
        self,
        timeout_seconds: float,
        enable_fast_mode: bool,
        enable_auto_replace: bool,
    ) -> bool:
        deadline = time.time() + max(0.08, timeout_seconds)
        action_taken = False

        while time.time() < deadline:
            if self._scan_install_dialogs(enable_fast_mode=enable_fast_mode, enable_auto_replace=enable_auto_replace):
                action_taken = True
                QApplication.processEvents()
                return True
            time.sleep(0.05)

        return action_taken

    def _scan_install_dialogs(self, enable_fast_mode: bool, enable_auto_replace: bool) -> bool:
        QApplication.processEvents()
        try:
            top_levels = QApplication.topLevelWidgets()
        except Exception:
            return False

        acted = False
        for widget in top_levels:
            if self._handle_install_dialog(
                widget,
                enable_fast_mode=enable_fast_mode,
                enable_auto_replace=enable_auto_replace,
            ):
                acted = True
        return acted

    def _handle_install_dialog(self, widget: Any, enable_fast_mode: bool, enable_auto_replace: bool) -> bool:
        try:
            if widget is None or not widget.isVisible():
                return False
        except Exception:
            return False

        title = ""
        try:
            title = str(widget.windowTitle() or "").strip().lower()
        except Exception:
            pass

        conflict_markers = ["mod existe", "já está instalado", "ja esta instalado", "already installed"]
        install_markers = ["instalação", "instalacao", "instalar", "quick install", "installation", "install"]

        is_conflict = any(marker in title for marker in conflict_markers)
        is_install = any(marker in title for marker in install_markers)

        if not is_conflict and not is_install:
            return False

        if is_conflict and enable_auto_replace:
            if self._click_by_markers(widget, ["repor", "replace", "substituir", "reinstalar", "overwrite"]):
                return True

        if is_install and enable_fast_mode:
            self._select_fast_install_mode(widget)

        if self._click_by_markers(widget, ["ok", "instalar", "install", "confirmar", "continuar", "aceitar"]):
            return True

        return False

    def _click_by_markers(self, widget: Any, markers: List[str]) -> bool:
        lowered_markers = [m.strip().lower() for m in markers if m.strip()]

        def _match(text_value: str) -> bool:
            normalized = str(text_value or "").strip().lower()
            return any(marker in normalized for marker in lowered_markers)

        try:
            if hasattr(widget, "findChildren"):
                for button in widget.findChildren(QPushButton):
                    if button.isEnabled() and _match(button.text()):
                        button.click()
                        QApplication.processEvents()
                        return True
        except Exception:
            pass

        try:
            if hasattr(widget, "findChildren"):
                for box in widget.findChildren(QDialogButtonBox):
                    try:
                        for button in box.buttons():
                            if button.isEnabled() and _match(button.text()):
                                button.click()
                                QApplication.processEvents()
                                return True
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            if hasattr(widget, "findChildren"):
                for button in widget.findChildren(QAbstractButton):
                    if button.isEnabled() and _match(button.text()):
                        button.click()
                        QApplication.processEvents()
                        return True
        except Exception:
            pass

        return False

    def _select_fast_install_mode(self, widget: Any) -> None:
        fast_markers = ["rápida", "rapida", "quick", "express", "automática", "automatica", "simple", "simples", "default"]
        manual_markers = ["manual"]

        try:
            if hasattr(widget, "findChildren"):
                for combo in widget.findChildren(QComboBox):
                    try:
                        current_index = combo.currentIndex()
                        current_text = str(combo.currentText() or "").strip().lower()
                        target_index = -1

                        for index in range(combo.count()):
                            text = str(combo.itemText(index) or "").strip().lower()
                            if any(marker in text for marker in fast_markers):
                                target_index = index
                                break

                        if target_index < 0 and any(marker in current_text for marker in manual_markers):
                            for index in range(combo.count()):
                                if index == current_index:
                                    continue
                                text = str(combo.itemText(index) or "").strip().lower()
                                if not any(marker in text for marker in manual_markers):
                                    target_index = index
                                    break

                        if target_index >= 0 and target_index != current_index:
                            combo.setCurrentIndex(target_index)
                            QApplication.processEvents()
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            if hasattr(widget, "findChildren"):
                for radio in widget.findChildren(QRadioButton):
                    text = str(radio.text() or "").strip().lower()
                    if radio.isEnabled() and any(marker in text for marker in fast_markers):
                        radio.setChecked(True)
                        QApplication.processEvents()
                        break
        except Exception:
            pass

    def _queue_manual_install(self, archive_path: str, reason: str) -> None:
        self._manual_install_items.append(
            {
                "archive": os.path.basename(archive_path),
                "reason": reason,
            }
        )

    def _flush_manual_install_notice(self) -> None:
        if not self._manual_install_items:
            return

        lines: List[str] = []
        for item in self._manual_install_items[:8]:
            lines.append(f"- {item['archive']}: {item['reason']}")

        extra = len(self._manual_install_items) - len(lines)
        if extra > 0:
            lines.append(f"- ... e mais {extra} item(ns).")

        message = (
            "Alguns downloads exigiram confirmação manual para finalizar corretamente.\n\n"
            + "\n".join(lines)
        )
        self._manual_install_items.clear()
        self._notify("MO2Tools - Atenção na Instalação", message)

    def _resolve_mod_path(self, mod_data: mobase.IModInterface) -> Optional[str]:
        if not self._organizer:
            return None

        paths: List[str] = []

        try:
            if hasattr(mod_data, "absolutePath"):
                attr = getattr(mod_data, "absolutePath")
                value = attr() if callable(attr) else attr
                if isinstance(value, str) and value.strip():
                    paths.append(value)
        except Exception:
            pass

        try:
            mod_name = mod_data.name()
            mods_root = self._organizer.modsPath()
            if mod_name and mods_root:
                paths.append(os.path.join(mods_root, mod_name))
        except Exception:
            pass

        for item in paths:
            if os.path.isdir(item):
                return item

        return None

    def _fix_version_with_fallback(self, mod_data: mobase.IModInterface) -> Dict[str, bool]:
        result = {"primary": False, "fallback": False}

        try:
            result["primary"] = self._fix_version_from_download_meta(mod_data)
        except Exception as exc:
            _logger.debug(f"Erro em sincronização primária: {exc}")

        if not result["primary"]:
            try:
                result["fallback"] = self._fix_version_from_meta_ini(mod_data)
            except Exception as exc:
                _logger.debug(f"Erro em sincronização fallback: {exc}")

        return result

    def _fix_version_from_download_meta(self, mod_data: mobase.IModInterface) -> bool:
        if not self._organizer:
            return False

        try:
            install_file = mod_data.installationFile()
            if not install_file:
                return False

            meta_path = os.path.join(self._organizer.downloadsPath(), f"{install_file}.meta")
            if not os.path.exists(meta_path):
                return False

            parser = configparser.ConfigParser()
            parser.read(meta_path, encoding="utf-8")
            if "General" not in parser:
                return False

            version_text = parser["General"].get("version", "").strip()
            if not version_text:
                return False

            mod_data.setVersion(mobase.VersionInfo(version_text))
            return True
        except Exception:
            return False

    def _fix_version_from_meta_ini(self, mod_data: mobase.IModInterface) -> bool:
        mod_path = self._resolve_mod_path(mod_data)
        if not mod_path:
            return False

        meta_ini = os.path.join(mod_path, "meta.ini")
        if not os.path.exists(meta_ini):
            return False

        parser = configparser.ConfigParser()
        try:
            parser.read(meta_ini, encoding="utf-8")
        except Exception:
            return False

        if "General" not in parser:
            return False

        general = parser["General"]
        current = general.get("version", "").strip() or "0.0.0"
        newest = general.get("newestVersion", "").strip()
        if not newest:
            return False

        current_tuple = _parse_numeric_version(current)
        newest_tuple = _parse_numeric_version(newest)

        if current_tuple is None or newest_tuple is None:
            mismatch = current != newest
        else:
            mismatch = current_tuple != newest_tuple

        if not mismatch:
            return False

        general["version"] = newest
        try:
            with open(meta_ini, "w", encoding="utf-8") as file_obj:
                parser.write(file_obj)
        except Exception:
            return False

        try:
            mod_data.setVersion(mobase.VersionInfo(newest))
        except Exception:
            pass

        return True

    def run_version_fix_all(self) -> None:
        if not self._organizer:
            return
        if not self._get_bool("pluginEnabled", True):
            return

        try:
            mod_list = self._organizer.modList()
            mod_names = list(mod_list.allMods())
        except Exception as exc:
            self._notify("MO2Tools", f"Não foi possível ler a lista de mods: {exc}", True)
            return

        processed = 0
        fixed_primary = 0
        fixed_fallback = 0
        unchanged = 0
        errors = 0

        progress = self._create_progress("Sincronizando versões...", len(mod_names))

        for idx, mod_name in enumerate(mod_names):
            if self._update_progress(progress, idx, f"Processando: {mod_name}"):
                break

            try:
                mod_data = mod_list.getMod(mod_name)
                if mod_data is None:
                    continue

                processed += 1
                result = self._fix_version_with_fallback(mod_data)
                if result["primary"]:
                    fixed_primary += 1
                elif result["fallback"]:
                    fixed_fallback += 1
                else:
                    unchanged += 1
            except Exception:
                errors += 1

        self._finish_progress(progress)
        self._refresh_modlist()

        summary = (
            f"Processados: {processed}\n"
            f"Corrigidos (primário): {fixed_primary}\n"
            f"Corrigidos (fallback): {fixed_fallback}\n"
            f"Sem alteração: {unchanged}\n"
            f"Erros: {errors}"
        )
        self._notify("MO2Tools - Versionamento", summary)

    def endorse_all(self) -> None:
        self._run_bulk_action("endorse")

    def track_all(self) -> None:
        self._run_bulk_action("track")

    def _run_bulk_action(self, action: str) -> None:
        if not self._organizer:
            return
        if not self._get_bool("pluginEnabled", True):
            return

        if action == "endorse" and not self._get_bool("endorseFeatureEnabled", True):
            return
        if action == "track" and not self._get_bool("trackFeatureEnabled", True):
            return

        use_cache = self._get_bool("useActionCache", True)

        try:
            mod_list = self._organizer.modList()
            mod_names = list(mod_list.allMods())
        except Exception as exc:
            self._notify("MO2Tools", f"Falha ao ler mods: {exc}", True)
            return

        try:
            nexus_bridge = self._organizer.createNexusBridge()
        except Exception:
            nexus_bridge = None

        done = 0
        local_only = 0
        skipped = 0
        errors = 0

        action_title = "Apoiar todos" if action == "endorse" else "Seguir todos"
        progress = self._create_progress(f"Executando {action_title}...", len(mod_names))

        for idx, mod_name in enumerate(mod_names):
            if self._update_progress(progress, idx, f"Processando: {mod_name}"):
                break

            try:
                mod_data = mod_list.getMod(mod_name)
                if mod_data is None:
                    continue

                mod_id = self._get_mod_nexus_id(mod_data)
                if mod_id <= 0:
                    skipped += 1
                    continue

                if use_cache and self._cache.is_done(action, mod_id):
                    skipped += 1
                    continue

                if action == "endorse" and self._is_already_endorsed(mod_data):
                    if use_cache:
                        self._cache.mark_done(action, mod_id, mod_name)
                    skipped += 1
                    continue

                if action == "track" and self._is_already_tracked(mod_data):
                    if use_cache:
                        self._cache.mark_done(action, mod_id, mod_name)
                    skipped += 1
                    continue

                local_ok = self._apply_local_action(action, mod_data)
                remote_ok = self._send_remote_action(action, nexus_bridge, mod_data, mod_id)

                if not remote_ok and not local_ok:
                    if action == "track":
                        skipped += 1
                    else:
                        errors += 1
                    continue

                if local_ok and not remote_ok:
                    local_only += 1

                if use_cache:
                    self._cache.mark_done(action, mod_id, mod_name)

                done += 1
            except Exception:
                errors += 1

        self._finish_progress(progress)

        summary = (
            f"Ação: {action_title}\n"
            f"Concluídos: {done}\n"
            f"Concluídos localmente: {local_only}\n"
            f"Ignorados: {skipped}\n"
            f"Erros: {errors}"
        )
        self._notify("MO2Tools", summary)

    def _get_mod_nexus_id(self, mod_data: mobase.IModInterface) -> int:
        try:
            if hasattr(mod_data, "nexusId"):
                attr = getattr(mod_data, "nexusId")
                value = attr() if callable(attr) else attr
                if value:
                    return int(value)
        except Exception:
            pass

        fields = ["url", "repository", "repositoryUrl", "nexusUrl"]
        for field_name in fields:
            text = self._read_mod_attr_text(mod_data, field_name)
            extracted = self._extract_mod_id_from_text(text)
            if extracted > 0:
                return extracted

        return 0

    def _read_mod_attr_text(self, mod_data: mobase.IModInterface, attr_name: str) -> str:
        try:
            if hasattr(mod_data, attr_name):
                attr = getattr(mod_data, attr_name)
                raw = attr() if callable(attr) else attr
                if raw is not None:
                    return str(raw)
        except Exception:
            pass
        return ""

    def _extract_mod_id_from_text(self, raw_text: str) -> int:
        text = str(raw_text or "")
        if not text:
            return 0

        patterns = [
            r"/mods/(\d+)",
            r"mod[_-]?id[=:/\s](\d+)",
            r"\bmods?[=:/\s](\d+)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    continue
        return 0

    def _is_already_endorsed(self, mod_data: mobase.IModInterface) -> bool:
        try:
            return mod_data.endorsedState() == mobase.EndorsedState.ENDORSED_TRUE
        except Exception:
            return False

    def _is_already_tracked(self, mod_data: mobase.IModInterface) -> bool:
        try:
            if hasattr(mod_data, "trackedState") and hasattr(mobase, "TrackedState"):
                return mod_data.trackedState() == mobase.TrackedState.TRACKED_TRUE
        except Exception:
            pass

        try:
            if hasattr(mod_data, "isTracked"):
                return bool(mod_data.isTracked())
        except Exception:
            pass

        return False

    def _apply_local_action(self, action: str, mod_data: mobase.IModInterface) -> bool:
        try:
            if action == "endorse" and hasattr(mod_data, "setIsEndorsed"):
                mod_data.setIsEndorsed(True)
                return True
            if action == "track":
                for method_name in ["setIsTracked", "setTracked", "setIsTracking", "setTracking"]:
                    if not hasattr(mod_data, method_name):
                        continue
                    method = getattr(mod_data, method_name)
                    try:
                        method(True)
                        return True
                    except TypeError:
                        method()
                        return True
                    except Exception:
                        continue
        except Exception:
            pass

        return False

    def _send_remote_action(self, action: str, bridge: Any, mod_data: mobase.IModInterface, mod_id: int) -> bool:
        if bridge is None:
            return False

        game_candidates = self._get_game_candidates(mod_data)
        if not game_candidates:
            game_candidates = [""]

        version_text = ""
        try:
            version_text = str(mod_data.version())
        except Exception:
            pass

        for game_name in game_candidates:
            if action == "endorse":
                if self._call_endorse(bridge, game_name, mod_id, version_text):
                    return True
            else:
                if self._call_track(bridge, game_name, mod_id, version_text):
                    return True

        return False

    def _get_game_candidates(self, mod_data: mobase.IModInterface) -> List[str]:
        candidates: List[str] = []

        for attr_name in ["gameName", "gameShortName", "nexusGameName", "gameId", "nexusGameId"]:
            value = self._read_mod_attr_text(mod_data, attr_name)
            if value:
                candidates.append(value)

        if self._organizer and hasattr(self._organizer, "managedGame"):
            try:
                game = self._organizer.managedGame()
                if game is not None:
                    for attr_name in ["gameName", "shortName", "gameShortName", "nexusGameName", "name"]:
                        try:
                            if hasattr(game, attr_name):
                                attr = getattr(game, attr_name)
                                value = attr() if callable(attr) else attr
                                if value:
                                    candidates.append(str(value))
                        except Exception:
                            continue
            except Exception:
                pass

        dedup: List[str] = []
        seen = set()
        for item in candidates:
            normalized = str(item).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            dedup.append(normalized)

        return dedup

    def _call_endorse(self, bridge: Any, game_name: str, mod_id: int, version_text: str) -> bool:
        if not hasattr(bridge, "requestToggleEndorsement"):
            return False

        attempts = [
            (game_name, mod_id, version_text, True, None),
            (game_name, mod_id, version_text, True),
            (game_name, mod_id, True),
            (game_name, mod_id),
        ]

        for args in attempts:
            try:
                bridge.requestToggleEndorsement(*args)
                return True
            except TypeError:
                continue
            except Exception:
                continue

        return False

    def _call_track(self, bridge: Any, game_name: str, mod_id: int, version_text: str) -> bool:
        method_names = [
            "requestToggleTracking",
            "requestToggleTracked",
            "requestToggleModTracking",
            "requestSetTracked",
            "requestTrackMod",
            "requestFollowMod",
            "requestSetTracking",
        ]

        try:
            dynamic_names = [
                name for name in dir(bridge)
                if "track" in name.lower() and callable(getattr(bridge, name, None))
            ]
            for name in dynamic_names:
                if name not in method_names:
                    method_names.append(name)
        except Exception:
            pass

        for method_name in method_names:
            if not hasattr(bridge, method_name):
                continue

            method = getattr(bridge, method_name)
            attempts = [
                (game_name, mod_id, True, None),
                (game_name, mod_id, True),
                (game_name, mod_id, version_text, True, None),
                (game_name, mod_id, version_text, True),
                (game_name, mod_id),
                (mod_id, True),
                (mod_id,),
            ]

            for args in attempts:
                try:
                    method(*args)
                    return True
                except TypeError:
                    continue
                except Exception:
                    continue

        return False

    def _create_progress(self, text: str, maximum: int) -> Optional[QProgressDialog]:
        if not self._get_bool("showProgressDialogs", True):
            return None

        parent = self._parent_widget if self._parent_widget else None
        progress = QProgressDialog(text, "Cancelar", 0, max(1, maximum), parent)
        progress.setWindowTitle("MO2Tools")
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)

        if _QT6:
            if parent is not None:
                progress.setWindowModality(Qt.WindowModality.WindowModal)
            else:
                progress.setWindowModality(Qt.WindowModality.NonModal)
            progress.setWindowFlag(Qt.WindowType.Tool, True)
        else:
            if parent is not None:
                progress.setWindowModality(Qt.WindowModal)
            else:
                progress.setWindowModality(Qt.NonModal)
            progress.setWindowFlags(progress.windowFlags() | Qt.Tool)

        progress.show()
        progress.repaint()
        QApplication.processEvents()
        return progress

    def _update_progress(self, progress: Optional[QProgressDialog], value: int, label: str) -> bool:
        if progress is None:
            return False

        progress.setValue(value)
        progress.setLabelText(label)
        progress.repaint()
        QApplication.processEvents()
        return progress.wasCanceled()

    def _finish_progress(self, progress: Optional[QProgressDialog]) -> None:
        if progress is None:
            return

        try:
            progress.setValue(progress.maximum())
            progress.repaint()
            QApplication.processEvents()
            progress.close()
            QApplication.processEvents()
        except Exception:
            pass

    def _refresh_modlist(self) -> None:
        if not self._organizer:
            return
        if hasattr(self._organizer, "refresh"):
            try:
                self._organizer.refresh(True)
            except Exception:
                pass

    def _notify(self, title: str, message: str, error: bool = False) -> None:
        parent = self._parent_widget if self._parent_widget else None
        if parent is None:
            if error:
                _logger.error(message)
            else:
                _logger.info(message)
            return

        if error:
            QMessageBox.warning(parent, title, message)
        else:
            QMessageBox.information(parent, title, message)


def createPlugin() -> mobase.IPluginTool:
    return MO2Tools()
