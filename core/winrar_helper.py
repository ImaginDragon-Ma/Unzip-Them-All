# -*- coding: utf-8 -*-
"""WinRAR 命令行工具封装"""

import glob
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Callable

from config.constants import (
    COMMON_WINRAR_PATHS,
    WINRAR_SUCCESS_CODES
)


class WinRARHelper:
    """WinRAR 命令行工具封装类"""

    @staticmethod
    def find_path() -> Optional[Path]:
        """
        查找 WinRAR 可执行文件的路径

        Returns:
            Path: WinRAR 完整路径，如果找不到返回 None
        """
        # 1. 尝试从 PATH 环境变量查找
        winrar_path = shutil.which('winrar')
        if winrar_path:
            return Path(winrar_path)

        winrar_path = shutil.which('winrar.exe')
        if winrar_path:
            return Path(winrar_path)

        # 2. 尝试常见的安装路径
        for path_str in COMMON_WINRAR_PATHS:
            path = Path(path_str)
            if path.exists():
                return path

        # 3. 使用环境变量路径
        program_files = os.environ.get('ProgramFiles', '')
        if program_files:
            path = Path(program_files) / 'WinRAR' / 'WinRAR.exe'
            if path.exists():
                return path

        program_files_x86 = os.environ.get('ProgramFiles(x86)', '')
        if program_files_x86:
            path = Path(program_files_x86) / 'WinRAR' / 'WinRAR.exe'
            if path.exists():
                return path

        # 4. 使用 glob 搜索多个驱动器
        for drive in ['C', 'D', 'E', 'F']:
            try:
                matches = glob.glob(f'{drive}:\\Program Files*\\WinRAR\\WinRAR.exe')
                for match in matches:
                    path = Path(match)
                    if path.exists():
                        return path
            except OSError:
                pass

        # 5. 尝试从系统环境变量 PATH 搜索
        path_env = os.environ.get('PATH', '')
        for dir_path in path_env.split(os.pathsep):
            try:
                potential_path = Path(dir_path) / 'winrar.exe'
                if potential_path.exists():
                    return potential_path
                potential_path = Path(dir_path) / 'winrar'
                if potential_path.exists():
                    return potential_path
            except OSError:
                pass

        return None

    @staticmethod
    def extract(
        archive_path: Path,
        output_dir: Path,
        winrar_path: Optional[Path] = None,
        password: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        使用 WinRAR 解压文件

        Args:
            archive_path: 压缩文件路径
            output_dir: 输出目录
            winrar_path: WinRAR 可执行文件路径，如果为 None 则自动查找
            password: 解压密码
            log_callback: 日志回调函数

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息/成功信息)
        """
        # 方法1: 使用完整路径
        if winrar_path and winrar_path.exists():
            cmd = [str(winrar_path), 'x', '-y', '-o+', '-inul']
            if password:
                cmd.append(f'-p{password}')
            cmd.extend([str(archive_path), str(output_dir) + os.sep])

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    encoding='gbk',
                    errors='ignore'
                )

                if result.returncode in WINRAR_SUCCESS_CODES:
                    return True, '解压成功'
                else:
                    error_msg = f'WinRAR 返回码: {result.returncode}'
                    if result.stderr:
                        error_msg += f', 错误: {result.stderr}'
                    if log_callback:
                        log_callback(f'  [WinRAR] {error_msg}')
                        if result.stdout:
                            log_callback(f'  [WinRAR] 输出: {result.stdout}')
                    return False, error_msg
            except FileNotFoundError:
                error_msg = f'无法使用 WinRAR 路径: {winrar_path}'
                if log_callback:
                    log_callback(f'  [警告] {error_msg}')
            except Exception as e:
                error_msg = f'解压失败: {str(e)}'
                if log_callback:
                    log_callback(f'  [错误] {error_msg}')
                return False, error_msg

        # 方法2: 使用 shell=True 后备方案
        if log_callback:
            log_callback('  [尝试] 使用 shell 方式调用 WinRAR...')

        cmd_str = f'winrar x -y -o+ -inul'
        if password:
            cmd_str += f' -p{password}'
        cmd_str += f' "{archive_path}" "{output_dir}\\"'

        try:
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='gbk',
                errors='ignore'
            )

            if result.returncode in WINRAR_SUCCESS_CODES:
                if log_callback:
                    log_callback('  [成功] shell 方式调用成功')
                return True, '解压成功'
            else:
                error_msg = f'WinRAR 返回码: {result.returncode}'
                if result.stderr:
                    error_msg += f', 错误: {result.stderr}'
                if log_callback:
                    log_callback(f'  [WinRAR] {error_msg}')
                    if result.stdout:
                        log_callback(f'  [WinRAR] 输出: {result.stdout}')
                return False, error_msg
        except Exception as e:
            error_msg = f'shell 方式调用失败: {str(e)}'
            if log_callback:
                log_callback(f'  [错误] {error_msg}')
            return False, error_msg

    @staticmethod
    def is_available(winrar_path: Optional[Path] = None) -> bool:
        """
        检查 WinRAR 是否可用

        Args:
            winrar_path: WinRAR 路径，如果为 None 则自动查找

        Returns:
            bool: 是否可用
        """
        if winrar_path:
            return winrar_path.exists()
        return WinRARHelper.find_path() is not None
