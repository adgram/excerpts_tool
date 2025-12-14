from flask import Blueprint, render_template, session
from pathlib import Path

from ...sqlutils import SqlDataManager, get_sql_path


index_bp = Blueprint('main', __name__)


def initialize_database(db_path: Path):
    """在主线程初始化 SqlDataManager 单例"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    manager = SqlDataManager(db_path) 
    manager.set_instance(0) # 设置单例
    return manager


def index(file_name:str):
    """渲染前端主页面 (index.html)"""
    # 尝试初始化数据库以验证路径
    path_obj = get_sql_path()/file_name
    # 调用初始化，设置单例
    initialize_database(path_obj)
    # 存储到 session，作为数据库已选择的标志
    session['db_key'] = str(path_obj) 
    return render_template('index.html')


index_bp.add_url_rule('/<file_name>', "index", index)