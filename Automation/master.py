# Automation Module Master

class AutomationMaster:
    def __init__(self, organizer):
        from .Installer.auto_installer import EnhancedAutoInstaller
        self.installer = EnhancedAutoInstaller(organizer)
