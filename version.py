"""
版本信息模块
"""

VERSION = (2025, 12, 15) # 以日期为版本
__version__ = '.'.join(map(str, VERSION))
__version_tuple__ = VERSION

# 预发布标识符
__release__ = 'beta'  # 可选: alpha, beta, rc (release candidate)
__full_version__ = f'{__version__}-{__release__}' if __release__ else __version__