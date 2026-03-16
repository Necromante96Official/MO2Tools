# UI Module Master
try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout
except ImportError:
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout


class MO2ToolsDialog(QDialog):
    def __init__(self, plugin=None, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self.setWindowTitle("MO2Tools v0.0.6 - Premium Control Panel")
        self.setMinimumSize(620, 390)
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
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("MO2Tools")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("Automação premium para Mod Organizer 2")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        badge_row = QHBoxLayout()
        badge = QLabel("v0.0.6")
        badge.setObjectName("badge")
        badge_row.addWidget(badge)
        badge_row.addStretch()
        layout.addLayout(badge_row)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)

        info_layout.addWidget(QLabel("Versão: 0.0.6"))
        info_layout.addWidget(QLabel("Desenvolvido por: Necromante96Official"))
        info_layout.addWidget(QLabel("Plugin: MO2Tools"))
        info_layout.addWidget(
            QLabel("Objetivo: instalação automática de mods com precisão operacional"))

        features = QLabel(
            "Recursos premium:\n"
            "- Auto Install com fila e deduplicação\n"
            "- Fast Install com seleção automática\n"
            "- Auto Replace em conflitos\n"
            "- Sanitização e capitalização inteligente do nome do mod\n"
            "- Exclusão definitiva dos downloads após instalação"
        )
        features.setStyleSheet("color: #c9d1d9;")
        info_layout.addWidget(features)

        quality = QLabel(
            "Nível de Qualidade: Premium\n"
            "Precisão operacional: alta\n"
            "Compatibilidade: PyQt5/PyQt6"
        )
        quality.setStyleSheet("color: #9dd6ff;")
        info_layout.addWidget(quality)

        status = self._build_status_label()
        status.setStyleSheet("color: #79c0ff; font-weight: 600;")
        info_layout.addWidget(status)

        layout.addWidget(info_card)

        layout.addStretch()

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.close)
        buttons_row.addWidget(btn_close)
        layout.addLayout(buttons_row)

    def _build_status_label(self):
        if not self._plugin or not getattr(self._plugin, "_organizer", None):
            return QLabel("Status: aguardando contexto do MO2")

        organizer = self._plugin._organizer
        plugin_name = self._plugin.name()

        def _read_bool(setting_key, default=True):
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

        enabled = _read_bool("enabled", True)
        auto_install = _read_bool("autoInstall", True)
        fast_install = _read_bool("fastInstall", True)
        auto_replace = _read_bool("autoReplace", True)
        sanitize_name = _read_bool("sanitizeModName", True)
        title_case_name = _read_bool("titleCaseModName", True)
        delete_after_install = _read_bool("deleteDownloadAfterInstall", True)
        delete_sidecars = _read_bool("deleteDownloadSidecars", True)

        return QLabel(
            "Status técnico: "
            f"enabled={enabled} | autoInstall={auto_install} | "
            f"fastInstall={fast_install} | autoReplace={auto_replace} | "
            f"sanitizeModName={sanitize_name} | titleCaseModName={title_case_name} | "
            f"deleteAfterInstall={delete_after_install} | deleteSidecars={delete_sidecars}"
        )
