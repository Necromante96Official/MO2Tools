# Core Module Master

class CoreMaster:
    def __init__(self, organizer):
        from .Config.manager import ConfigManager
        from .VersionSync.auto_version_sync import AutoVersionSync

        self.config = ConfigManager(organizer)
        self.version_sync = AutoVersionSync(organizer)
