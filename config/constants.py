# -*- coding: utf-8 -*-
"""常量定义"""

# 配置文件名
CONFIG_FILE = 'extractor_config.json'

# 支持的压缩文件扩展名
ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.001', '.002', '.003', '.004', '.005',
}

# 分卷压缩扩展名
VOLUME_EXTENSIONS = {
    '.001', '.002', '.003', '.004', '.005', '.006', '.007', '.008', '.009',
}

# 非压缩文件扩展名（用于排除）
NON_ARCHIVE_EXTENSIONS = {
    '.txt': '文本文件', '.doc': 'Word', '.docx': 'Word',
    '.xls': 'Excel', '.xlsx': 'Excel', '.ppt': 'PowerPoint',
    '.pdf': 'PDF', '.jpg': 'JPEG', '.jpeg': 'JPEG',
    '.png': 'PNG', '.gif': 'GIF', '.bmp': 'BMP',
    '.mp3': 'MP3', '.mp4': 'MP4', '.avi': 'AVI',
    '.mkv': 'MKV', '.flv': 'FLV', '.wmv': 'WMV',
    '.exe': '可执行文件', '.dll': '动态链接库',
    '.iso': 'ISO 镜像', '.img': 'IMG 镜像'
}

# 常见的 WinRAR 安装路径
COMMON_WINRAR_PATHS = [
    r'C:\Program Files\WinRAR\WinRAR.exe',
    r'C:\Program Files (x86)\WinRAR\WinRAR.exe',
    r'C:\WinRAR\WinRAR.exe',
    r'D:\Program Files\WinRAR\WinRAR.exe',
    r'D:\Program Files (x86)\WinRAR\WinRAR.exe',
    r'D:\WinRAR\WinRAR.exe',
]

# 最大递归深度
MAX_RECURSION_DEPTH = 10

# WinRAR 命令行返回码（表示成功）
WINRAR_SUCCESS_CODES = [0, 1]
