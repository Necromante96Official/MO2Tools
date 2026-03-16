# UI Module Master
try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
except ImportError:
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class MO2ToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MO2Tools v0.0.1 - Painel")
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout(self)

        title = QLabel("MO2Tools")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #00ff00;")
        layout.addWidget(title)

        info = QLabel("Desenvolvido por: Necromante96Official")
        info.setStyleSheet("font-style: italic;")
        layout.addWidget(info)

        layout.addStretch()

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
