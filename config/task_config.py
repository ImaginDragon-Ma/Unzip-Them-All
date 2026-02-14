# -*- coding: utf-8 -*-
"""任务配置"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class TaskConfig:
    """单个任务配置"""
    output_dir: str = ''  # 输出目录
    password: str = ''  # 解压密码（可为空）
    files: List[str] = field(default_factory=list)  # 文件路径列表

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TaskConfig':
        """从字典创建配置"""
        return cls(**{
            k: v for k, v in data.items() if k in cls.__dataclass_fields__
        })

    def add_file(self, file_path: Path) -> None:
        """添加文件"""
        file_str = str(file_path)
        if file_str not in self.files:
            self.files.append(file_str)

    def remove_file(self, file_path: Path) -> None:
        """移除文件"""
        file_str = str(file_path)
        if file_str in self.files:
            self.files.remove(file_str)

    def get_file_paths(self) -> List[Path]:
        """获取文件路径列表"""
        return [Path(f) for f in self.files]
