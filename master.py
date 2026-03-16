import mobase
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon
import os


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

    def author(self) -> str:
        return "Necromante96Official"

    def description(self) -> str:
        return "Central de automação modular e avançada para MO2."

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(0, 0, 1, mobase.ReleaseType.FINAL)

    def isActive(self) -> bool:
        return True

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", "Habilitar MO2Tools", True),
            mobase.PluginSetting(
                "autoInstall", "Instalação Automática Ultra Mejorada", True),
        ]

    def display(self) -> None:
        from .UI.master import MO2ToolsDialog
        dialog = MO2ToolsDialog(self._parent_widget)
        dialog.exec()

    def icon(self) -> QIcon:
        return QIcon()

    def setParentWidget(self, widget):
        self._parent_widget = widget
