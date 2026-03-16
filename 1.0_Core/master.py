# Core Module Master
from .1.1_Config.manager import ConfigManager

class CoreMaster:
    def __init__(self, organizer):
        self.config = ConfigManager(organizer)
