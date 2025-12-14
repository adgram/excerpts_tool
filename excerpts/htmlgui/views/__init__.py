
from .api_view import api_bp, close_manager
from .config_view import config_bp, check_db_selection
from .index_view import index_bp


# 导出所有蓝图
__all__ = ['index_bp', 'api_bp', 'config_bp', 'close_manager', 'check_db_selection']