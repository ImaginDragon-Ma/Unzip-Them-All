# -*- coding: utf-8 -*-
"""密码管理"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class PasswordManager:
    """密码管理器"""

    passwords: List[str]

    def __init__(self, passwords: Optional[List[str]] = None):
        self.passwords = passwords or []

    def add_password(self, password: str) -> bool:
        """
        添加密码

        Args:
            password: 要添加的密码

        Returns:
            bool: 是否添加成功（密码已存在则返回 False）
        """
        if not password or password in self.passwords:
            return False
        self.passwords.append(password)
        return True

    def remove_password(self, password: str) -> bool:
        """
        删除密码

        Args:
            password: 要删除的密码

        Returns:
            bool: 是否删除成功（密码不存在则返回 False）
        """
        if password in self.passwords:
            self.passwords.remove(password)
            return True
        return False

    def update_password(self, old_password: str, new_password: str) -> bool:
        """
        更新密码

        Args:
            old_password: 旧密码
            new_password: 新密码

        Returns:
            bool: 是否更新成功（旧密码不存在则返回 False）
        """
        if old_password not in self.passwords:
            return False

        index = self.passwords.index(old_password)
        self.passwords[index] = new_password
        return True

    def contains(self, password: str) -> bool:
        """检查密码是否存在"""
        return password in self.passwords

    def get_all(self) -> List[str]:
        """获取所有密码"""
        return self.passwords.copy()

    def clear(self) -> None:
        """清空所有密码"""
        self.passwords.clear()
