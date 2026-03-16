import mobase
import os

try:
    from PyQt6.QtGui import QIcon
except ImportError:
    from PyQt5.QtGui import QIcon


class MO2ToolsMaster(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent_widget = None

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer

        # Inicializar Core e Automações (Arquitetura Modular Limpa)
        from .Core.master import CoreMaster
        from .Automation.master import AutomationMaster

        self.core = CoreMaster(organizer)
        self.automation = AutomationMaster(organizer)

        return True

    def name(self) -> str:
        return "MO2Tools"

    def displayName(self) -> str:
        return "MO2Tools"

    def localizedName(self) -> str:
        return "MO2Tools"

    def author(self) -> str:
        return "Necromante96Official"

    def description(self) -> str:
        return "Central de automação modular e avançada para MO2."

    def tooltip(self) -> str:
        return "Abrir painel do MO2Tools"

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(0, 1, 3, mobase.ReleaseType.FINAL)

    def isActive(self) -> bool:
        return True

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", "Habilitar MO2Tools", True),
            mobase.PluginSetting(
                "autoInstall", "Instalação Automática ao concluir download", True),
            mobase.PluginSetting(
                "fastInstall", "Selecionar instalação rápida automaticamente", True),
            mobase.PluginSetting(
                "autoReplace", "Substituir automaticamente quando mod já existir", True),
            mobase.PluginSetting(
                "sanitizeModName", "Limpar nome automático do mod (sem versão/código Nexus)", True),
            mobase.PluginSetting(
                "titleCaseModName", "Capitalizar nome do mod automaticamente (ex.: Content Patcher)", True),
            mobase.PluginSetting(
                "strictArchiveCheck", "Instalar automaticamente apenas arquivos de mod suportados", True),
            mobase.PluginSetting(
                "deleteDownloadAfterInstall", "Excluir download após instalação concluída", True),
            mobase.PluginSetting(
                "deleteDownloadSidecars", "Excluir metadados/arquivos auxiliares do download", True),
            mobase.PluginSetting(
                "autoInstallRetryCount", "Quantidade de retentativas do Auto Install por download", 8),
            mobase.PluginSetting(
                "autoInstallEventWaitSeconds", "Tempo de espera (s) por confirmação do evento de instalação", 4),
            mobase.PluginSetting(
                "autoVersionFixEnabled", "Corrigir versões automaticamente no startup e a cada intervalo", True),
            mobase.PluginSetting(
                "autoVersionFixRunOnStartup", "Executar version fix ao iniciar o MO2", True),
            mobase.PluginSetting(
                "autoVersionFixIntervalMinutes", "Intervalo em minutos do version fix automático", 10),
            mobase.PluginSetting(
                "autoVersionFixRefreshAfterRun", "Atualizar lista de mods após version fix", True),
            mobase.PluginSetting(
                "autoVersionFixCreateBackup", "Criar backup do meta.ini antes de alterar versão", True),
        ]

    def display(self) -> None:
        from .UI.master import MO2ToolsDialog
        dialog = MO2ToolsDialog(plugin=self, parent=self._parent_widget)
        dialog.exec()

    def icon(self) -> QIcon:
        return QIcon()

    def setParentWidget(self, widget):
        self._parent_widget = widget
