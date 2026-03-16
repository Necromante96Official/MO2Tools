import mobase


def createPlugin() -> mobase.IPluginTool:
    from .master import MO2ToolsMaster
    return MO2ToolsMaster()
