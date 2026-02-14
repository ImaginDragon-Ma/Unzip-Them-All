# -*- coding: utf-8 -*-
"""配置管理"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from .constants import CONFIG_FILE


@dataclass
class Config:
    """配置数据类"""
    winrar_path: str = ''
    output_dir: str = ''
    extract_to_source: bool = False
    remember_password: bool = False
    password: str = ''

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """从字典创建配置"""
        return cls(**{
            k: v for k, v in data.items() if k in cls.__dataclass_fields__
        })


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认使用常量中的 CONFIG_FILE

    Returns:
        Config: 配置对象
    """
    path = config_path or CONFIG_FILE

    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Config.from_dict(data)
        except (json.JSONDecodeError, TypeError, OSError):
            pass

    return Config()


def save_config(config: Config, config_path: Optional[str] = None) -> bool:
    """
    保存配置到文件

    Args:
        config: 配置对象
        config_path: 配置文件路径，默认使用常量中的 CONFIG_FILE

    Returns:
        bool: 是否保存成功
    """
    path = config_path or CONFIG_FILE

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except (TypeError, OSError) as e:
        print(f"保存配置失败: {e}")
        return False
