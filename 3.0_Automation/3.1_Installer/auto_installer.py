# Auto-Installer Ultra Mejorada v0.0.1
import os
import time
import queue
import logging
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QPushButton, QDialogButtonBox, QComboBox, QRadioButton

_logger = logging.getLogger("MO2Tools.Installer")


class EnhancedAutoInstaller:
    def __init__(self, organizer):
        self._organizer = organizer
        self._download_manager = organizer.downloadManager()
        self._install_queue = queue.Queue()
        self._is_installing = False

        # Conectar ao evento de download concluído
        if self._download_manager:
            self._download_manager.onDownloadComplete(
                self._on_download_complete)
            _logger.info("Hook de download registrado com sucesso.")

    def _on_download_complete(self, download_id):
        archive_path = self._download_manager.downloadPath(download_id)
        if archive_path and os.path.exists(archive_path):
            _logger.info(
                f"Download concluído: {archive_path}. Adicionando à fila.")
            self._install_queue.put(archive_path)
            # Iniciar processamento da fila com um pequeno delay para evitar conflitos
            QTimer.singleShot(1000, self._process_queue)

    def _process_queue(self):
        if self._is_installing or self._install_queue.empty():
            return

        self._is_installing = True
        archive_path = self._install_queue.get()

        try:
            _logger.info(f"Iniciando instalação automática de: {archive_path}")
            # Iniciar assistente de UI para clicar nos botões
            timer = QTimer()
            timer.setInterval(100)
            timer.timeout.connect(lambda: self._scan_dialogs(timer))
            timer.start()

            # Chamar a instalação nativa do MO2
            self._organizer.installMod(str(archive_path))

            timer.stop()
            _logger.info("Instalação concluída com sucesso.")
        except Exception as e:
            _logger.error(f"Erro na instalação automática: {e}")
        finally:
            self._is_installing = False
            # Processar próximo item se houver
            if not self._install_queue.empty():
                QTimer.singleShot(500, self._process_queue)

    def _scan_dialogs(self, timer):
        # Scan de janelas ativas para automação de botões
        for widget in QApplication.topLevelWidgets():
            if not widget.isVisible():
                continue

            title = str(widget.windowTitle()).lower()

            # Alvos: "Instalar", "Substituir", "OK"
            targets = ["instalar", "install",
                       "repor", "replace", "ok", "confirmar"]

            if any(target in title for target in targets):
                self._automate_widget(widget)

    def _automate_widget(self, widget):
        # Lógica para selecionar 'Quick Install' se disponível
        for combo in widget.findChildren(QComboBox):
            for i in range(combo.count()):
                if "quick" in combo.itemText(i).lower() or "rápida" in combo.itemText(i).lower():
                    combo.setCurrentIndex(i)

        # Clicar no botão de confirmação
        for btn in widget.findChildren(QPushButton):
            text = btn.text().lower()
            if any(t in text for t in ["ok", "instalar", "install", "confirmar", "repor", "replace"]):
                btn.click()
                break
