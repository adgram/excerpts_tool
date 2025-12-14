from flask import Blueprint, render_template, redirect, url_for, request, session
import logging

from ...sqlutils import get_sql_path, get_db_list

# 设置 logging
logger = logging.getLogger(__name__)


config_bp = Blueprint('config', __name__)


def select_db_view():
    """处理数据库文件选择和初始化"""
    db_dir = get_sql_path()
    db_list = get_db_list(db_dir)
    if request.method == 'POST' and (submitted_path := request.form.get('db_path')) in db_list:
        # 成功，跳转到主页
        return redirect(url_for('main.index', file_name = submitted_path)) 
    # GET 请求，渲染文件选择页面
    return render_template('selectdb.html', db_list = db_list)


def check_db_selection():
    """在处理任何请求之前检查数据库是否已选择"""
    # 允许访问配置页面 ('config.select_db_view') 和静态文件 ('static')
    if request.endpoint not in ('config.select_db_view', 'static') and not session.get('db_key'):
        return redirect(url_for('config.select_db_view'))

config_bp.add_url_rule('/selectdb', 'select_db_view', select_db_view, methods=['GET', 'POST'])
config_bp.add_url_rule('/', 'select_db_view', select_db_view, methods=['GET', 'POST'])