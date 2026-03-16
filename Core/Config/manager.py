# Config Manager v0.0.1
class ConfigManager:
    def __init__(self, organizer):
        self._organizer = organizer
        self._plugin_name = "MO2Tools"

    def get_bool(self, key, default=True):
        return self._organizer.pluginSetting(self._plugin_name, key)

    def set_bool(self, key, value):
        self._organizer.setPluginSetting(self._plugin_name, key, value)
