# UI Module Master
try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout
except ImportError:
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout


class MO2ToolsDialog(QDialog):
    def __init__(self, plugin=None, parent=None):
        # UI Module Master
        try:
            from PyQt6.QtWidgets import (
                QCheckBox,
                QDialog,
                QFrame,
                QHBoxLayout,
                QLabel,
                QMessageBox,
                QPushButton,
                QVBoxLayout,
            )
        except ImportError:
            from PyQt5.QtWidgets import (
                QCheckBox,
                QDialog,
                QFrame,
                QHBoxLayout,
                QLabel,
                QMessageBox,
                QPushButton,
                QVBoxLayout,
            )

        class MO2ToolsDialog(QDialog):
            def __init__(self, plugin=None, parent=None):
                super().__init__(parent)
                self._plugin = plugin
                self._status_label = None

                self.setWindowTitle("MO2Tools v0.0.7 - Premium Control Panel")
                self.setMinimumSize(700, 460)
                self.setStyleSheet(
                    "QDialog {"
                    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0e1424, stop:0.55 #0b1220, stop:1 #101826);"
                    "}"
                    "QLabel { color: #e6edf3; font-size: 12px; }"
                    "QLabel#title { font-size: 28px; font-weight: 800; color: #7cc4ff; }"
                    "QLabel#subtitle { color: #9fb3c8; font-size: 13px; }"
                    "QLabel#badge { background: #163356; color: #8ed0ff; border: 1px solid #245a93; border-radius: 10px; padding: 3px 10px; font-weight: 700; }"
                    "QPushButton { background: #2f81f7; color: white; border: 1px solid #5aa2ff; padding: 8px 14px; border-radius: 8px; font-weight: 600; }"
                    "QPushButton:hover { background: #4b91f2; }"
                    "QFrame#card { background: rgba(16, 24, 36, 0.92); border: 1px solid #2f3e55; border-radius: 12px; }"
                    "QCheckBox { color: #dce8f5; spacing: 8px; }"
                )

                root = QVBoxLayout(self)
                root.setContentsMargins(16, 16, 16, 16)
                root.setSpacing(12)

                title = QLabel("MO2Tools")
                title.setObjectName("title")
                root.addWidget(title)

                subtitle = QLabel("Automação premium para Mod Organizer 2")
                subtitle.setObjectName("subtitle")
                root.addWidget(subtitle)

                badge_row = QHBoxLayout()
                badge = QLabel("v0.0.7")
                badge.setObjectName("badge")
                badge_row.addWidget(badge)
                badge_row.addStretch()
                root.addLayout(badge_row)

                content_row = QHBoxLayout()
                content_row.setSpacing(12)
                root.addLayout(content_row)

                info_card = QFrame()
                info_card.setObjectName("card")
                info_layout = QVBoxLayout(info_card)
                info_layout.setContentsMargins(12, 12, 12, 12)
                info_layout.setSpacing(8)
                info_layout.addWidget(QLabel("Versão: 0.0.7"))
                info_layout.addWidget(
                    QLabel("Desenvolvido por: Necromante96Official"))
                info_layout.addWidget(QLabel("Plugin: MO2Tools"))
                info_layout.addWidget(
                    QLabel("Objetivo: instalação automática de mods com precisão profissional"))
                info_layout.addWidget(
                    QLabel(
                        "Recursos:\n"
                        "- Auto Install com fila e deduplicação\n"
                        "- Sanitização e capitalização do nome do mod\n"
                        "- Exclusão definitiva de download pós-instalação\n"
                        "- Compatibilidade PyQt5/PyQt6"
                    )
                )
                self._status_label = QLabel(self._build_status_text())
                self._status_label.setStyleSheet(
                    "color: #79c0ff; font-weight: 600;")
                self._status_label.setWordWrap(True)
                info_layout.addWidget(self._status_label)
                content_row.addWidget(info_card, 1)

                options_card = QFrame()
                options_card.setObjectName("card")
                options_layout = QVBoxLayout(options_card)
                options_layout.setContentsMargins(12, 12, 12, 12)
                options_layout.setSpacing(8)
                options_layout.addWidget(QLabel("Menu de Opções"))

                self.cb_enabled = QCheckBox("Habilitar MO2Tools")
                self.cb_auto_install = QCheckBox("Ativar Auto Install")
                self.cb_fast_install = QCheckBox("Ativar Fast Install")
                self.cb_auto_replace = QCheckBox("Ativar Auto Replace")
                self.cb_sanitize_name = QCheckBox(
                    "Limpar nome do mod (remove versão/código)")
                self.cb_title_case = QCheckBox(
                    "Capitalizar nome do mod (ex.: Content Patcher)")
                self.cb_strict_archive = QCheckBox(
                    "Aceitar apenas arquivos de mod suportados")
                self.cb_delete_after = QCheckBox(
                    "Excluir download após instalação")
                self.cb_delete_sidecars = QCheckBox(
                    "Excluir metadados e arquivos auxiliares")

                for checkbox in [
                    self.cb_enabled,
                    self.cb_auto_install,
                    self.cb_fast_install,
                    self.cb_auto_replace,
                    self.cb_sanitize_name,
                    self.cb_title_case,
                    self.cb_strict_archive,
                    self.cb_delete_after,
                    self.cb_delete_sidecars,
                ]:
                    options_layout.addWidget(checkbox)

                options_layout.addStretch()
                content_row.addWidget(options_card, 1)

                self._load_values()

                buttons_row = QHBoxLayout()
                buttons_row.addStretch()

                btn_save = QPushButton("Salvar Configurações")
                btn_save.clicked.connect(self._save_values)
                buttons_row.addWidget(btn_save)

                btn_close = QPushButton("Fechar")
                btn_close.clicked.connect(self.close)
                buttons_row.addWidget(btn_close)

                root.addLayout(buttons_row)

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

            def _set_bool(self, setting_key, value):
                if not self._plugin or not getattr(self._plugin, "_organizer", None):
                    return
                try:
                    self._plugin._organizer.setPluginSetting(
                        self._plugin.name(), setting_key, bool(value))
                except Exception:
                    pass

            def _load_values(self):
                self.cb_enabled.setChecked(self._read_bool("enabled", True))
                self.cb_auto_install.setChecked(
                    self._read_bool("autoInstall", True))
                self.cb_fast_install.setChecked(
                    self._read_bool("fastInstall", True))
                self.cb_auto_replace.setChecked(
                    self._read_bool("autoReplace", True))
                self.cb_sanitize_name.setChecked(
                    self._read_bool("sanitizeModName", True))
                self.cb_title_case.setChecked(
                    self._read_bool("titleCaseModName", True))
                self.cb_strict_archive.setChecked(
                    self._read_bool("strictArchiveCheck", True))
                self.cb_delete_after.setChecked(
                    self._read_bool("deleteDownloadAfterInstall", True))
                self.cb_delete_sidecars.setChecked(
                    self._read_bool("deleteDownloadSidecars", True))

            def _save_values(self):
                self._set_bool("enabled", self.cb_enabled.isChecked())
                self._set_bool("autoInstall", self.cb_auto_install.isChecked())
                self._set_bool("fastInstall", self.cb_fast_install.isChecked())
                self._set_bool("autoReplace", self.cb_auto_replace.isChecked())
                self._set_bool("sanitizeModName",
                               self.cb_sanitize_name.isChecked())
                self._set_bool("titleCaseModName",
                               self.cb_title_case.isChecked())
                self._set_bool("strictArchiveCheck",
                               self.cb_strict_archive.isChecked())
                self._set_bool("deleteDownloadAfterInstall",
                               self.cb_delete_after.isChecked())
                self._set_bool("deleteDownloadSidecars",
                               self.cb_delete_sidecars.isChecked())

                if self._status_label is not None:
                    self._status_label.setText(self._build_status_text())

                QMessageBox.information(
                    self, "MO2Tools", "Configurações salvas com sucesso.")

            def _build_status_text(self):
                if not self._plugin or not getattr(self._plugin, "_organizer", None):
                    return "Status: aguardando contexto do MO2"

                enabled = self._read_bool("enabled", True)
                auto_install = self._read_bool("autoInstall", True)
                fast_install = self._read_bool("fastInstall", True)
                auto_replace = self._read_bool("autoReplace", True)
                sanitize_name = self._read_bool("sanitizeModName", True)
                title_case_name = self._read_bool("titleCaseModName", True)
                strict_archive = self._read_bool("strictArchiveCheck", True)
                delete_after_install = self._read_bool(
                    "deleteDownloadAfterInstall", True)
                delete_sidecars = self._read_bool(
                    "deleteDownloadSidecars", True)

                return (
                    "Status técnico: "
                    f"enabled={enabled} | autoInstall={auto_install} | "
                    f"fastInstall={fast_install} | autoReplace={auto_replace} | "
                    f"sanitizeModName={sanitize_name} | titleCaseModName={title_case_name} | "
                    f"strictArchiveCheck={strict_archive} | "
                    f"deleteAfterInstall={delete_after_install} | deleteSidecars={delete_sidecars}"
                )
