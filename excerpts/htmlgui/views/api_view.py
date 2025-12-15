from flask import Blueprint, jsonify, request, session, abort
import flask
import logging
from typing import Optional
from pathlib import Path

from ...sqlutils import SqlDataManager, TagData, ExcerptData

# 设置 logging
logger = logging.getLogger(__name__)
# 创建 API 蓝图，所有路由都将以 /api 开头
api_bp = Blueprint('api', __name__, url_prefix='/api')



# 在线程内创建一个独立的SqlDataManager，操作完即释放
def get_db_manager() -> SqlDataManager:
    db_key = session.get('db_key')
    if not db_key:
        jsonify({"error": "Database not selected or session expired"}), 403
        abort(403)
    if 'temp_manager' not in flask.g:
        flask.g.temp_manager = SqlDataManager(Path(db_key))
    return flask.g.temp_manager


def close_manager(e=None):
    """请求结束后关闭数据库连接和管理器"""
    temp_manager:SqlDataManager = flask.g.pop('temp_manager', None)
    if temp_manager is not None:
        temp_manager.close()


# --- 辅助函数：格式化摘录数据 ---
def _format_excerpt_for_frontend(excerpt: ExcerptData) -> dict:
    """将 ExcerptData 转换为前端需要的字典格式 (包含完整的标签信息)"""
    data = excerpt.to_dict()
    manager:SqlDataManager = get_db_manager()
    # 确保 data 中包含 tag_cids 属性，并且它是可迭代的
    tag_list = []
    for cid in data.get('tag_cids', []):
        if cid == "default":
            continue
        tag: TagData = manager.get_tag(cid)
        tag_list.append(tag.to_dict())
    data['tags'] = tag_list
    if 'tag_cids' in data:
        data.pop('tag_cids')
    # 简化 created_at 格式
    if data.get('created_at'):
        data['created_at'] = str(data['created_at'])[:10]
    return data

def get_tags():
    """获取所有标签列表及其包含的摘录数量"""
    manager:SqlDataManager = get_db_manager()
    try:
        tags = manager.get_tags_helper().get_all_by_order()
        
        response_data = []
        for i, tag in enumerate(tags):
            tag_dict = tag.to_dict()
            tag_dict['count'] = manager.get_tags_helper().get_excerpts_count(tag.cid)
            tag_dict['isActive'] = (i == 0)
            response_data.append(tag_dict)
        
        return jsonify(response_data)
    except Exception as e:
        logger.exception("Error processing tags data in /api/tags") 
        return jsonify({"error": "Failed to retrieve tag data."}), 500


def get_excerpts(tag_cid: Optional[str] = None):
    """根据标签 CID 或 'all' 获取摘录列表"""
    manager:SqlDataManager  = get_db_manager()
    
    tag_cid = tag_cid if tag_cid else 'all'
    
    if tag_cid in ('all', 'default'):
        excerpts = manager.get_excerpts_helper().get_all_excerpts()
    else:
        excerpt_ids = manager.get_tags_helper().get_excerpt_cids(tag_cid)
        excerpts = manager.get_excerpts_helper().get_excerpts(excerpt_ids)
    
    response_data = [_format_excerpt_for_frontend(e) for e in excerpts]
    return jsonify(response_data)


def delete_excerpt(cid):
    """删除指定 CID 的摘录"""
    manager:SqlDataManager = get_db_manager()
    
    try:
        manager.get_excerpts_helper().delete_excerpt(cid)
        manager.commit()
        return jsonify({"message": f"Excerpt {cid} deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting excerpt {cid}: {e}")
        return jsonify({"error": "Failed to delete excerpt"}), 500


def search_excerpts():
    """根据关键词搜索摘录 (参数 q)"""
    manager:SqlDataManager = get_db_manager()
    query = request.args.get('q', '') 
    
    if not query:
        return jsonify([])
        
    data = manager.get_excerpts_helper().search(query)
    response_data = [_format_excerpt_for_frontend(e) for e in data]
    return jsonify(response_data)



api_bp.add_url_rule('/tags', 'get_tags', get_tags, methods=['GET'])
api_bp.add_url_rule('/excerpts/by_tag/<tag_cid>', 'get_excerpts', get_excerpts, methods=['GET'])
api_bp.add_url_rule('/excerpts/all', 'get_excerpts', get_excerpts, methods=['GET'])
api_bp.add_url_rule('/excerpt/delete/<cid>', 'delete_excerpt', delete_excerpt, methods=['POST'])
api_bp.add_url_rule('/search', 'search_excerpts', search_excerpts, methods=['GET'])