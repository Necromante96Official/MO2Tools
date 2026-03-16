# UI Module Master
try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout
except ImportError:
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout


class MO2ToolsDialog(QDialog):
    def __init__(self, plugin=None, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self.setWindowTitle("MO2Tools v0.0.5 - Painel Profissional")
        self.setMinimumSize(560, 340)
        self.setStyleSheet(
            "QDialog { background: #10131a; }"
            "QLabel { color: #e6edf3; font-size: 12px; }"
            "QPushButton { background: #1f6feb; color: white; border: none; padding: 8px 14px; border-radius: 6px; }"
            "QPushButton:hover { background: #388bfd; }"
            "QFrame#card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("MO2Tools")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: #58a6ff;")
        layout.addWidget(title)

        subtitle = QLabel("Automação profissional para Mod Organizer 2")
        subtitle.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(subtitle)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)

        info_layout.addWidget(QLabel("Versão: 0.0.5"))
        info_layout.addWidget(QLabel("Desenvolvido por: Necromante96Official"))
        info_layout.addWidget(QLabel("Plugin: MO2Tools"))
        info_layout.addWidget(
            QLabel("Objetivo: instalar mods automaticamente com precisão e segurança"))

        features = QLabel(
            "Recursos ativos:\n"
            "- Auto Install com fila e deduplicação\n"
            "- Fast Install com seleção automática\n"
            "- Auto Replace em conflitos\n"
            "- Limpeza inteligente de nome do mod"
        )
        features.setStyleSheet("color: #c9d1d9;")
        info_layout.addWidget(features)

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

        return QLabel(
            "Status técnico: "
            f"enabled={enabled} | autoInstall={auto_install} | "
            f"fastInstall={fast_install} | autoReplace={auto_replace} | "
            f"sanitizeModName={sanitize_name}"
        )
