# Core Module Master

class CoreMaster:
    def __init__(self, organizer):
        from .Config.manager import ConfigManager
        self.config = ConfigManager(organizer)
