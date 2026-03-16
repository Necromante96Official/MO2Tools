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

            # 1. Obter nome base do mod (remover extensão)
            mod_name = os.path.splitext(os.path.basename(archive_path))[0]

            # 2. Iniciar assistente de UI ANTES de chamar installMod
            self._scan_timer = QTimer()
            self._scan_timer.setInterval(200)
            self._scan_timer.timeout.connect(self._scan_tick)
            self._scan_timer.start()

            # 3. Chamar a instalação nativa do MO2 (Bloqueante se houver UI)
            # Nota: No MO2 v2.4+, installMod pode exigir dois argumentos: path e name
            try:
                self._organizer.installMod(str(archive_path), mod_name)
            except TypeError:
                self._organizer.installMod(str(archive_path))

            self._scan_timer.stop()
            _logger.info(f"Fim da rotina de instalação para: {archive_path}")
        except Exception as e:
            _logger.error(f"Erro na instalação automática: {e}")
            if hasattr(self, "_scan_timer"):
                self._scan_timer.stop()
        finally:
            self._is_installing = False
            # Processar próximo item se houver
            if not self._install_queue.empty():
                QTimer.singleShot(1000, self._process_queue)

    def _scan_tick(self):
        # Scan de janelas ativas para automação de botões
        for widget in QApplication.topLevelWidgets():
            try:
                if not widget.isVisible():
                    continue

                title = str(widget.windowTitle()).lower()

                # Diálogos comuns do MO2: "Query", "Install Mod", "Mod Already Installed"
                targets = ["instalar", "install", "repor",
                           "replace", "ok", "confirmar", "query"]

                if any(target in title for target in targets):
                    self._automate_widget(widget)
            except Exception:
                continue

    def _scan_dialogs(self, timer):
        # Mantido para retrocompatibilidade, mas chamamos o tick
        self._scan_tick()

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
