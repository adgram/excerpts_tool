from flask import Blueprint, render_template, session, redirect, url_for
from pathlib import Path

from ...sqlutils import SqlDataManager, get_sql_path


app_bp = Blueprint('app', __name__)


def initialize_database(db_path: Path):
    """在主线程初始化 SqlDataManager 单例"""
    manager = SqlDataManager(db_path) 
    manager.set_instance() # 设置单例
    return manager


def index(file_name:str):
    """渲染前端主页面 (app.html)"""
    # 尝试初始化数据库以验证路径
    path_obj = get_sql_path()/file_name
    if not path_obj.is_file(): 
        # 如果文件不存在，重定向到选择页面
        return redirect(url_for('config.select_db_view'))
    # 调用初始化，设置单例
    initialize_database(path_obj)
    # 存储到 session，作为数据库已选择的标志
    session['db_key'] = str(path_obj) 
    return render_template('app.html')


app_bp.add_url_rule('/app/<file_name>', "index", index)