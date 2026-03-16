# Automation Module Master
from .3.1_Installer.auto_installer import EnhancedAutoInstaller

class AutomationMaster:
    def __init__(self, organizer):
        self.installer = EnhancedAutoInstaller(organizer)
