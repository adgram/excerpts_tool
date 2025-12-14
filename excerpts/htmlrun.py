from flask import Flask
from pathlib import Path
import logging

from .htmlgui.views import index_bp, api_bp, config_bp, close_manager, check_db_selection
from .htmlgui import config


logger = logging.getLogger(__name__)



def create_flask_app():
    """创建并配置 Flask 应用实例"""
    # 获取路径，确保静态文件和模板路径正确
    template_path = Path(__file__).parent / "htmlgui" / "templates"
    static_path = Path(__file__).parent / "htmlgui" / "static"

    app = Flask(
        __name__.split('.')[0], 
        template_folder = template_path,
        static_folder = static_path
    )
    app.config.from_object(config)
    # 注册钩子：在请求结束后关闭线程安全的连接 (解决 g 存储对象的生命周期)
    app.teardown_appcontext(close_manager) 
    # 注册蓝图 (index_bp 处理 / 路由, api_bp 处理 /api/* 路由)
    app.register_blueprint(index_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(config_bp)
    app.before_request(check_db_selection)
    return app



def run():
    """Web UI 的启动入口 (html_run)"""
    # 创建 Flask 应用
    flask_app = create_flask_app()
    # 启动服务器
    print("Starting Flask web server on http://127.0.0.1:5000")
    flask_app.run(host='0.0.0.0', port = 5000, debug = True)