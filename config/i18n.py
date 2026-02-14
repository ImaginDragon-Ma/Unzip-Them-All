# -*- coding: utf-8 -*-
"""国际化支持"""

from typing import Dict


class Translations:
    """翻译字典"""

    ZH_CN = {
        'window_title': '压缩文件批量解压工具',
        'winrar_path': 'WinRAR 路径',
        'winrar_found': '✓',
        'winrar_not_found': '✗ 未找到',
        'browse': '浏览...',
        'global_options': '全局选项',
        'extract_to_source': '解压到原目录（忽略任务中的输出目录设置）',
        'use_unified_password': '使用统一密码（忽略任务中的密码设置）',
        'select_or_input_password': '选择或输入统一密码',
        'password_management': '密码管理',
        'manage_passwords': '管理密码',
        'task_config': '任务配置',
        'add_task': '添加任务',
        'ready': '准备就绪',
        'extracting': '正在解压...',
        'extraction_log': '解压日志',
        'start_extract': '开始解压',
        'output': '输出:',
        'password': '密码:',
        'no_password': '无密码',
        'select_output_dir': '选择输出目录...',
        'select_files': '选择文件',
        'clear': '清空',
        'file_count': '文件: {}',
        'delete_task': '×',
        'delete_task_tooltip': '删除此任务',
        'warning': '警告',
        'no_tasks': '请至少添加一个任务并选择文件！',
        'no_winrar': '未找到 WinRAR！\n\n请点击"浏览..."按钮选择 WinRAR.exe 的位置。',
        'empty_output_dir': '有一个任务的输出目录为空！\n\n请为每个任务设置输出目录或勾选"解压到原目录"。',
        'output_dir_not_exist': '输出目录不存在: {}',
        'complete': '完成',
        'extraction_complete': '解压完成！\n\n成功: {}\n失败: {}',
        'manage_passwords_title': '管理密码',
        'saved_passwords': '已保存的密码:',
        'new_password': '新密码:',
        'add_password': '添加密码',
        'delete_selected': '删除选中',
        'clear_all': '清空全部',
        'confirm': '确认',
        'clear_all_passwords': '确定要清空所有密码吗？',
        'input_password': '请输入密码！',
        'password_exists': '密码已存在！',
        'select_password': '请选择要删除的密码！',
    }

    EN = {
        'window_title': 'Batch Archive Extractor',
        'winrar_path': 'WinRAR Path',
        'winrar_found': '✓',
        'winrar_not_found': '✗ Not Found',
        'browse': 'Browse...',
        'global_options': 'Global Options',
        'extract_to_source': 'Extract to source directory (ignore task output directory settings)',
        'use_unified_password': 'Use unified password (ignore task password settings)',
        'select_or_input_password': 'Select or input unified password',
        'password_management': 'Password Management',
        'manage_passwords': 'Manage Passwords',
        'task_config': 'Task Configuration',
        'add_task': 'Add Task',
        'ready': 'Ready',
        'extracting': 'Extracting...',
        'extraction_log': 'Extraction Log',
        'start_extract': 'Start Extraction',
        'output': 'Output:',
        'password': 'Password:',
        'no_password': 'No password',
        'select_output_dir': 'Select output directory...',
        'select_files': 'Select Files',
        'clear': 'Clear',
        'file_count': 'Files: {}',
        'delete_task': '×',
        'delete_task_tooltip': 'Delete this task',
        'warning': 'Warning',
        'no_tasks': 'Please add at least one task and select files!',
        'no_winrar': 'WinRAR not found!\n\nClick "Browse..." to select WinRAR.exe location.',
        'empty_output_dir': 'A task has empty output directory!\n\nPlease set output directory for each task or check "Extract to source".',
        'output_dir_not_exist': 'Output directory does not exist: {}',
        'complete': 'Complete',
        'extraction_complete': 'Extraction complete!\n\nSuccess: {}\nFailed: {}',
        'manage_passwords_title': 'Manage Passwords',
        'saved_passwords': 'Saved passwords:',
        'new_password': 'New password:',
        'add_password': 'Add Password',
        'delete_selected': 'Delete Selected',
        'clear_all': 'Clear All',
        'confirm': 'Confirm',
        'clear_all_passwords': 'Are you sure you want to clear all passwords?',
        'input_password': 'Please enter a password!',
        'password_exists': 'Password already exists!',
        'select_password': 'Please select a password to delete!',
    }


class I18N:
    """国际化类"""

    def __init__(self, language: str = 'zh_CN'):
        self.language = language

    def set_language(self, language: str) -> None:
        """
        设置语言

        Args:
            language: 语言代码 ('zh_CN' 或 'en')
        """
        self.language = language

    def get(self, key: str, *args) -> str:
        """
        获取翻译文本

        Args:
            key: 翻译键
            *args: 格式化参数

        Returns:
            str: 翻译后的文本
        """
        if self.language == 'en':
            texts = Translations.EN
        else:
            texts = Translations.ZH_CN

        text = texts.get(key, key)
        if args:
            return text.format(*args)
        return text

    def __call__(self, key: str, *args) -> str:
        """支持函数调用方式"""
        return self.get(key, *args)


# 全局翻译实例
_i18n = I18N()


def get_i18n() -> I18N:
    """获取全局翻译实例"""
    return _i18n


def set_language(language: str) -> None:
    """设置全局语言"""
    _i18n.set_language(language)


def t(key: str, *args) -> str:
    """翻译函数简写"""
    return _i18n.get(key, *args)
