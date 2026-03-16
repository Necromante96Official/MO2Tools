# UI Module Master
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QVBoxLayout,
    )
except ImportError:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QCheckBox,
        QDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QVBoxLayout,
    )


class MO2ToolsDialog(QDialog):
    def __init__(self, plugin=None, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self._status_label = None
        self._toggle_items = []

        self.setWindowTitle("MO2Tools v0.1.6 - Premium Control Center")
        self.setMinimumSize(860, 560)
        self.setStyleSheet(
            "QDialog {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0a1020, stop:0.4 #0f1b33, stop:1 #13233f);"
            "}"
            "QLabel { color: #dce7f5; font-size: 12px; }"
            "QLabel#title { font-size: 32px; font-weight: 900; color: #8fd3ff; }"
            "QLabel#subtitle { color: #aac6e3; font-size: 13px; }"
            "QLabel#badge { background: #173f68; color: #9cd8ff; border: 1px solid #2e6ca8; border-radius: 10px; padding: 4px 12px; font-weight: 700; }"
            "QLabel#sectionTitle { color: #9fd7ff; font-size: 13px; font-weight: 700; }"
            "QLabel#pillOn { background: #123927; color: #7ef0ae; border: 1px solid #2a8f55; border-radius: 9px; padding: 2px 8px; font-weight: 700; }"
            "QLabel#pillOff { background: #3a1717; color: #ff9c9c; border: 1px solid #8f3333; border-radius: 9px; padding: 2px 8px; font-weight: 700; }"
            "QPushButton { background: #2f81f7; color: white; border: 1px solid #5aa2ff; padding: 9px 14px; border-radius: 8px; font-weight: 600; }"
            "QPushButton:hover { background: #4b91f2; }"
            "QFrame#card { background: rgba(10, 20, 34, 0.94); border: 1px solid #2f4666; border-radius: 14px; }"
            "QCheckBox { color: #dce8f5; spacing: 10px; font-size: 12px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; border-radius: 7px; border: 1px solid #3f6ca0; background: #0c1a2f; }"
            "QCheckBox::indicator:checked { background: #28a745; border: 1px solid #66d18a; }"
            "QSpinBox { background: #0f1a2e; color: #e6edf3; border: 1px solid #355275; border-radius: 6px; padding: 4px 8px; min-width: 72px; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self._build_header(root)
        self._build_body(root)
        self._build_footer(root)

        self._load_values()
        self._refresh_live_status()

    def _build_header(self, root_layout):
        title = QLabel("MO2Tools")
        title.setObjectName("title")
        root_layout.addWidget(title)

        subtitle = QLabel("Control Center de automação para Mod Organizer 2")
        subtitle.setObjectName("subtitle")
        root_layout.addWidget(subtitle)

        badge_row = QHBoxLayout()
        badge = QLabel("v0.1.6")
        badge.setObjectName("badge")
        badge_row.addWidget(badge)
        badge_row.addStretch()
        root_layout.addLayout(badge_row)

    def _build_body(self, root_layout):
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        root_layout.addLayout(grid)

        overview_card = QFrame()
        overview_card.setObjectName("card")
        overview_layout = QVBoxLayout(overview_card)
        overview_layout.setContentsMargins(12, 12, 12, 12)
        overview_layout.setSpacing(8)
        overview_layout.addWidget(self._section_title("Resumo"))
        overview_layout.addWidget(QLabel("Versão: 0.1.6"))
        overview_layout.addWidget(
            QLabel("Desenvolvido por: Necromante96Official"))
        overview_layout.addWidget(QLabel("Plugin: MO2Tools"))
        overview_layout.addWidget(
            QLabel("Escopo: Auto Install + Version Fix + limpeza pós-instalação"))
        overview_layout.addWidget(
            QLabel(
                "Pacote de melhorias:\n"
                "- Layout premium reorganizado\n"
                "- Toggling dinâmico com feedback ON/OFF\n"
                "- Reconfiguração do Version Fix em runtime\n"
                "- Ações rápidas para execução imediata"
            )
        )
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #7fc8ff; font-weight: 600;")
        overview_layout.addWidget(self._status_label)
        grid.addWidget(overview_card, 0, 0)

        install_card = QFrame()
        install_card.setObjectName("card")
        install_layout = QVBoxLayout(install_card)
        install_layout.setContentsMargins(12, 12, 12, 12)
        install_layout.setSpacing(7)
        install_layout.addWidget(self._section_title("Auto Install"))

        self.cb_enabled, self.lb_enabled = self._add_toggle(
            install_layout, "Habilitar MO2Tools", "enabled", True)
        self.cb_auto_install, self.lb_auto_install = self._add_toggle(
            install_layout, "Ativar Auto Install", "autoInstall", True)
        self.cb_fast_install, self.lb_fast_install = self._add_toggle(
            install_layout, "Ativar Fast Install", "fastInstall", True)
        self.cb_auto_replace, self.lb_auto_replace = self._add_toggle(
            install_layout, "Ativar Auto Replace", "autoReplace", True)
        self.cb_sanitize_name, self.lb_sanitize_name = self._add_toggle(
            install_layout, "Limpar nome do mod", "sanitizeModName", True)
        self.cb_title_case, self.lb_title_case = self._add_toggle(
            install_layout, "Capitalizar nome do mod", "titleCaseModName", True)
        self.cb_strict_archive, self.lb_strict_archive = self._add_toggle(
            install_layout, "Restringir tipos de arquivo", "strictArchiveCheck", True)
        self.cb_delete_after, self.lb_delete_after = self._add_toggle(
            install_layout, "Excluir download após instalar", "deleteDownloadAfterInstall", True)
        self.cb_delete_sidecars, self.lb_delete_sidecars = self._add_toggle(
            install_layout, "Excluir sidecars do download", "deleteDownloadSidecars", True)

        install_layout.addStretch()
        grid.addWidget(install_card, 0, 1)

        version_card = QFrame()
        version_card.setObjectName("card")
        version_layout = QVBoxLayout(version_card)
        version_layout.setContentsMargins(12, 12, 12, 12)
        version_layout.setSpacing(7)
        version_layout.addWidget(self._section_title("Version Fix Automático"))

        self.cb_auto_version_fix, self.lb_auto_version_fix = self._add_toggle(
            version_layout, "Ativar Version Fix", "autoVersionFixEnabled", True)
        self.cb_run_on_startup, self.lb_run_on_startup = self._add_toggle(
            version_layout, "Rodar Version Fix no startup", "autoVersionFixRunOnStartup", True)
        self.cb_refresh_after_fix, self.lb_refresh_after_fix = self._add_toggle(
            version_layout, "Refresh após Version Fix", "autoVersionFixRefreshAfterRun", True)
        self.cb_backup_meta, self.lb_backup_meta = self._add_toggle(
            version_layout, "Criar backup .bak", "autoVersionFixCreateBackup", True)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Intervalo (minutos):"))
        self.spin_interval_minutes = QSpinBox()
        self.spin_interval_minutes.setMinimum(1)
        self.spin_interval_minutes.setMaximum(120)
        self.spin_interval_minutes.valueChanged.connect(
            self._refresh_live_status)
        interval_row.addWidget(self.spin_interval_minutes)
        interval_row.addStretch()
        version_layout.addLayout(interval_row)

        action_row = QHBoxLayout()
        self.btn_run_fix_now = QPushButton("Executar Version Fix Agora")
        self.btn_run_fix_now.clicked.connect(self._run_version_fix_now)
        action_row.addWidget(self.btn_run_fix_now)
        action_row.addStretch()
        version_layout.addLayout(action_row)

        version_layout.addStretch()
        grid.addWidget(version_card, 1, 0, 1, 2)

    def _build_footer(self, root_layout):
        footer = QHBoxLayout()
        footer.addStretch()

        btn_default = QPushButton("Restaurar Padrões")
        btn_default.clicked.connect(self._restore_defaults)
        footer.addWidget(btn_default)

        btn_save = QPushButton("Salvar Configurações")
        btn_save.clicked.connect(self._save_values)
        footer.addWidget(btn_save)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.close)
        footer.addWidget(btn_close)

        root_layout.addLayout(footer)

    def _section_title(self, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _add_toggle(self, layout, label_text, setting_key, default_value):
        row = QHBoxLayout()
        checkbox = QCheckBox(label_text)
        checkbox.setChecked(self._read_bool(setting_key, default_value))

        pill = QLabel("")
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(
            Qt, "AlignmentFlag") else Qt.AlignCenter)
        pill.setMinimumWidth(54)
        self._update_toggle_pill(pill, checkbox.isChecked())

        checkbox.stateChanged.connect(
            lambda _state, cb=checkbox, lb=pill: self._on_toggle_changed(cb, lb))

        row.addWidget(checkbox)
        row.addStretch()
        row.addWidget(pill)

        layout.addLayout(row)
        self._toggle_items.append((setting_key, checkbox, pill, default_value))
        return checkbox, pill

    def _on_toggle_changed(self, checkbox, pill_label):
        self._update_toggle_pill(pill_label, checkbox.isChecked())
        self._refresh_live_status()

    def _update_toggle_pill(self, label, is_active):
        if is_active:
            label.setObjectName("pillOn")
            label.setText("ATIVO")
        else:
            label.setObjectName("pillOff")
            label.setText("DESATIV")
        label.style().unpolish(label)
        label.style().polish(label)

    def _read_bool(self, setting_key, default=True):
        if not self._plugin or not getattr(self._plugin, "_organizer", None):
            return default

        organizer = self._plugin._organizer
        plugin_name = self._plugin.name()
        try:
            raw = organizer.pluginSetting(plugin_name, setting_key)
        except Exception:
            raw = default

        if raw is None:
            return default
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, int):
            return raw != 0
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on", "sim"}
        return default

    def _read_int(self, setting_key, default=10):
        if not self._plugin or not getattr(self._plugin, "_organizer", None):
            return default

        organizer = self._plugin._organizer
        plugin_name = self._plugin.name()
        try:
            raw = organizer.pluginSetting(plugin_name, setting_key)
        except Exception:
            raw = default

        try:
            parsed = int(raw)
            return parsed if parsed > 0 else default
        except Exception:
            return default

    def _set_setting(self, setting_key, value):
        if not self._plugin or not getattr(self._plugin, "_organizer", None):
            return
        try:
            self._plugin._organizer.setPluginSetting(
                self._plugin.name(), setting_key, value)
        except Exception:
            pass

    def _load_values(self):
        for setting_key, checkbox, pill, default_value in self._toggle_items:
            checkbox.setChecked(self._read_bool(setting_key, default_value))
            self._update_toggle_pill(pill, checkbox.isChecked())

        self.spin_interval_minutes.setValue(
            self._read_int("autoVersionFixIntervalMinutes", 10))

    def _restore_defaults(self):
        defaults = {
            "enabled": True,
            "autoInstall": True,
            "fastInstall": True,
            "autoReplace": True,
            "sanitizeModName": True,
            "titleCaseModName": True,
            "strictArchiveCheck": True,
            "deleteDownloadAfterInstall": True,
            "deleteDownloadSidecars": True,
            "autoVersionFixEnabled": True,
            "autoVersionFixRunOnStartup": True,
            "autoVersionFixRefreshAfterRun": True,
            "autoVersionFixCreateBackup": True,
        }

        for setting_key, checkbox, pill, default_value in self._toggle_items:
            target = defaults.get(setting_key, default_value)
            checkbox.setChecked(target)
            self._update_toggle_pill(pill, target)

        self.spin_interval_minutes.setValue(10)
        self._refresh_live_status()

    def _save_values(self):
        for setting_key, checkbox, _pill, _default_value in self._toggle_items:
            self._set_setting(setting_key, checkbox.isChecked())

        self._set_setting("autoVersionFixIntervalMinutes",
                          int(self.spin_interval_minutes.value()))

        self._apply_runtime_updates()
        self._refresh_live_status()

        QMessageBox.information(
            self,
            "MO2Tools",
            "Configurações aplicadas com sucesso.",
        )

    def _apply_runtime_updates(self):
        if not self._plugin:
            return

        core = getattr(self._plugin, "core", None)
        version_sync = getattr(core, "version_sync",
                               None) if core is not None else None
        if version_sync is None:
            return

        try:
            version_sync.reload_from_settings()
        except Exception:
            pass

    def _run_version_fix_now(self):
        if not self._plugin:
            return

        core = getattr(self._plugin, "core", None)
        version_sync = getattr(core, "version_sync",
                               None) if core is not None else None
        if version_sync is None:
            QMessageBox.warning(
                self, "MO2Tools", "Módulo de Version Fix não disponível.")
            return

        try:
            version_sync.trigger_now()
            QMessageBox.information(
                self, "MO2Tools", "Version Fix executado manualmente.")
        except Exception as exc:
            QMessageBox.warning(
                self, "MO2Tools", f"Falha ao executar Version Fix: {exc}")

    def _refresh_live_status(self):
        if self._status_label is None:
            return

        state = {
            setting_key: checkbox.isChecked()
            for setting_key, checkbox, _pill, _default in self._toggle_items
        }

        self._status_label.setText(
            "Status Live: "
            f"enabled={state.get('enabled')} | autoInstall={state.get('autoInstall')} | "
            f"fastInstall={state.get('fastInstall')} | autoReplace={state.get('autoReplace')} | "
            f"sanitize={state.get('sanitizeModName')} | titleCase={state.get('titleCaseModName')} | "
            f"strictArchive={state.get('strictArchiveCheck')} | deleteDownload={state.get('deleteDownloadAfterInstall')} | "
            f"deleteSidecars={state.get('deleteDownloadSidecars')} | autoVersionFix={state.get('autoVersionFixEnabled')} | "
            f"runOnStartup={state.get('autoVersionFixRunOnStartup')} | refreshAfterFix={state.get('autoVersionFixRefreshAfterRun')} | "
            f"backupMeta={state.get('autoVersionFixCreateBackup')} | interval={int(self.spin_interval_minutes.value())}min"
        )
