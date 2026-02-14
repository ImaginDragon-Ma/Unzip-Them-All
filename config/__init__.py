# -*- coding: utf-8 -*-
"""配置模块"""

from config.settings import Config, load_config, save_config
from config.constants import CONFIG_FILE

__all__ = ['Config', 'load_config', 'save_config', 'CONFIG_FILE']
