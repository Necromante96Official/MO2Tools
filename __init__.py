from .1.0_Core.master import *
from .2.0_UI.master import *
from .3.0_Automation.master import *

import mobase

def createPlugin() -> mobase.IPluginTool:
    from .master import MO2ToolsMaster
    return MO2ToolsMaster()
