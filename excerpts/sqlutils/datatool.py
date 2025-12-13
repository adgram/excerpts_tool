import uuid, random, sqlite3
from datetime import datetime
from typing import TypedDict, Optional
from dataclasses import dataclass, asdict

from .sqlbase import TableHelper, IdTableHelper, SqlbaseHelper



class TagDataDict(TypedDict):
    cid   : str # 标签ID
    name  : str # 标签名称
    color : str # 标签颜色
    orders : int # 标签排序


class ExcerptDataDict(TypedDict):
    cid        : str # 摘录ID
    content    : str # 摘录内容
    source     : str # 摘录来源
    title      : str # 摘录标题
    author     : str # 摘录作者
    note       : str # 摘录笔记
    created_at : str # 创建时间
    tag_cids   : list[str] # 标签ID列表



@dataclass
class TagData:
    """标签数据类"""
    cid   : str # 标签ID
    name  : str # 标签名称
    color : str # 标签颜色
    orders : int # 标签排序

    @classmethod
    def default(cls) -> 'TagData':
        return cls("", "", "", 0)

    @classmethod
    def from_dict(cls, data: TagDataDict) -> Optional['TagData']:
        """
        从数据库行中创建DataTag对象
        """
        try:
            return cls(**{**cls.default().to_dict(), **data})
        except (TypeError, ValueError):
            return None

    @classmethod
    def from_dict_list(cls, data_list: list[TagDataDict]) -> list['TagData']:
        """
        从数据库行中创建DataTag对象
        """
        return [item for data in data_list if (item := cls.from_dict(data)) is not None]

    def to_dict(self) -> TagDataDict:
        """
        将数据转换为JSON字符串
        """
        return asdict(self)

    @classmethod
    def new(cls, cid, name, idx) -> 'TagData':
        return cls(cid, name, "#{:06x}".format(random.randint(0, 0xFFFFFF)), idx)


@dataclass
class ExcerptData:
    """摘录数据类"""
    cid        : str # 摘录ID
    content    : str # 摘录内容
    source     : str # 摘录来源
    title      : str # 摘录标题
    author     : str # 摘录作者
    note       : str # 摘录笔记
    created_at : str # 创建时间
    tag_cids   : list[str] # 标签ID列表

    @classmethod
    def default(cls) -> 'TagData':
        return cls("", "", "", "", "", "", "", [])

    @classmethod
    def from_dict(cls, data: ExcerptDataDict) -> Optional['ExcerptData']:
        """
        从数据库行中创建DataTag对象
        """
        try:
            return cls(**{**cls.default().to_dict(), **data})
        except (TypeError, ValueError):
            return None

    @classmethod
    def from_dict_list(cls, data_list: list[ExcerptDataDict]) -> list['ExcerptData']:
        """
        从数据库查询结果行中创建DataExcerpt对象
        """
        return [item for data in data_list if (item := cls.from_dict(data)) is not None]

    def to_dict(self) -> ExcerptDataDict:
        """
        将数据转换为JSON字符串
        """
        return asdict(self)

    @classmethod
    def update(cls, new: 'ExcerptData', old: 'ExcerptData' = None) -> None:
        """更新"""
        if old:
            old.content = new.content or old.content
            old.source = new.source or old.source or "未知"
            old.title = new.title or old.title or "无"
            old.author = new.author or old.author or "佚名"
            old.note = new.note or old.note
            old.tag_cids = new.tag_cids or old.tag_cids
            old.created_at = new.created_at or old.created_at or datetime.now().isoformat()
            if "default" not in old.tag_cids:
                old.tag_cids.append("default")
            return old
        else:
            new.cid = new.cid or str(uuid.uuid4())
            new.source = new.source or "未知"
            new.title = new.title or "无"
            new.author = new.author or "佚名"
            new.note = new.note
            new.created_at = new.created_at or datetime.now().isoformat()
            new.tag_cids = new.tag_cids
            if "default" not in new.tag_cids:
                new.tag_cids.append("default")
            return new


class DataExcerptTags(TableHelper):
    """摘录-标签关联类"""
    __slots__ = ('cursor', 'name', 'columns', 'keys')
    def __init__(self, cursor: sqlite3.Cursor):
        columns = [('excerpt_cid', str), ('tag_cid', str)]
        super().__init__(cursor, "excerpt_tags", columns)
        self.create_table()

    def create_table(self) -> None:
        """创建摘录-标签关联表（多对多关系）"""
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.name} (
                excerpt_cid TEXT NOT NULL,
                tag_cid TEXT NOT NULL,
                PRIMARY KEY (excerpt_cid, tag_cid),
                FOREIGN KEY (excerpt_cid) REFERENCES excerpts (cid) ON DELETE CASCADE,
                FOREIGN KEY (tag_cid) REFERENCES tags (cid) ON DELETE CASCADE
            )
        """)

    def add_tags(self, excerpt_cid: str, tags: list[str]) -> None:
        """为摘录添加多个标签"""
        if not tags:
            return
        data = [(excerpt_cid, tag) for tag in tags]
        self.cursor.executemany(self.get_insert_sql(['excerpt_cid', 'tag_cid'], 'IGNORE'), data)

    def update_tags(self, excerpt_cid: str, new_tags: list[str]) -> None:
        """更新摘录的标签（完全替换）"""
        if new_tags is None:  # 允许传入 None 表示不更新标签
            return
        # 删除现有标签
        self.delete("excerpt_cid = ?", (excerpt_cid,))
        # 添加新标签
        self.add_tags(excerpt_cid, new_tags)

    def get_tags(self, excerpt_cid: str) -> list[str]:
        """获取摘录的所有标签"""
        sql = f"SELECT tag_cid FROM {self.name} WHERE excerpt_cid = ?"
        results = self.query(sql, (excerpt_cid,))
        return [row['tag_cid'] for row in results]  # 直接返回字符串列表

    def get_excerpts_by_tag(self, tag_cid: str) -> list[str]:
        """获取使用指定标签的所有摘录ID"""
        sql = f"SELECT excerpt_cid FROM {self.name} WHERE tag_cid = ?"
        results = self.query(sql, (tag_cid,))
        return [row['excerpt_cid'] for row in results]

    def get_excerpts_count(self, tag_cid: str) -> int:
        """获取使用指定标签的摘录数量"""
        sql = f"SELECT COUNT(*) FROM {self.name} WHERE tag_cid = ?"
        results = self.query(sql, (tag_cid,))
        return results[0]['COUNT(*)'] if results else 0

    def merge_tags(self, source_tag: str, target_tag: str) -> None:
        """合并两个标签的关联"""
        if source_tag == target_tag:
            return
        # 转移关联到目标标签，避免重复
        sql = f"""
            INSERT OR IGNORE INTO {self.name} (excerpt_cid, tag_cid)
            SELECT excerpt_cid, ? FROM {self.name} 
            WHERE tag_cid = ?
        """
        self.cursor.execute(sql, (target_tag, source_tag))
        # 删除源标签关联
        self.delete("tag_cid = ?", (source_tag,))




class DataTags(IdTableHelper):
    """标签数据类"""
    __slots__ = ('cursor', 'name', 'columns', 'keys', 'id_column', 'excerpt_tags')
    def __init__(self, cursor: sqlite3.Cursor, excerpt_tags: DataExcerptTags):
        columns = [('cid', str),
                ('name', str),
                ('color', str),
                ('orders', int)]
        super().__init__(cursor, "tags", columns, "cid")
        self.excerpt_tags: DataExcerptTags = excerpt_tags
        self.create_table()
        if not self.item_count("cid", "default"):
            self.add_or_update("default", '全部摘录')
    
    def create_table(self) -> None:
        """
        CREATE TABLE IF NOT EXISTS tags - 创建一个名为tags的表，如果该表已经存在则不执行创建操作
        cid TEXT PRIMARY KEY - 创建一个文本类型的主键字段cid，用于唯一标识每个标签
        name TEXT NOT NULL - 创建一个文本类型的name字段，用于存储标签名称，不允许为空
        color TEXT NOT NULL - 创建一个文本类型的color字段，用于存储标签颜色值（如十六进制颜色代码），不允许为空
        orders INTEGER NOT NULL - 创建一个整数类型的orders字段，用于确定标签的显示顺序，不允许为空
        """
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.name} (
                cid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT NOT NULL,
                orders INTEGER NOT NULL
            )
        """)

    # def init_table(self) -> None:
    #     if self.count() == 0:
    #         default_tags = [("default", '全部摘录', "#d13fac", 1)]
    #         sql = self.get_insert_sql(self.keys)
    #         self.cursor.executemany(sql, default_tags)

    def get_all_by_order(self) -> list[TagData]:
        """
        获取所有标签数据，按排序顺序返回
        Returns:
            list[DataTags]: 包含标签信息的DataTags对象列表
        """
        return TagData.from_dict_list(self.get_all(order_by = "orders"))

    def get_item(self, cid: str) -> Optional[TagData]:
        """
        获取指定名称的标签数据
        Args:
            cid (str): 标签名称
        Returns:
            DataTags: 获取的标签数据
        """
        return TagData.from_dict(self.get_line(cid))

    def get_tags(self, cids: list[str]) -> list[TagData]:
        if not cids:
            return []
        placeholders = ','.join(['?'] * len(cids))
        sql = f"SELECT * FROM {self.name} WHERE cid IN ({placeholders})"
        tags = self.query(sql, tuple(cids))
        return TagData.from_dict_list(tags)

    def update_order(self, cids: list[str]) -> None:
        """批量更新标签排序顺序"""
        self.update_pairs({cid: order for order, cid in enumerate(cids, 1)}, "orders")

    def add_or_update(self, cid: str, name: str) -> None:
        """添加或更新标签 """
        self.insert_or_update_upsert([TagData.new(cid, name, self.count()+1).to_dict()])

    def delete_tag(self, tag_cid: str) -> None:
        """删除标签并将关联摘录转移到默认标签"""
        if tag_cid == "default":
            raise ValueError("不能删除默认标签")
        # 转移关联到默认标签
        self.excerpt_tags.merge_tags(tag_cid, "default")
        # 使用 delete() 方法
        self.delete("cid = ?", (tag_cid,))

    def get_excerpt_cids(self, tag_cid: str) -> list[str]:
        """获取使用指定标签的所有摘录ID"""
        return self.excerpt_tags.get_excerpts_by_tag(tag_cid)

    def get_excerpts_count(self, tag_cid: str) -> int:
        """获取使用指定标签的摘录数量"""
        return self.excerpt_tags.get_excerpts_count(tag_cid)

    def get_cid(self, name: str) -> str | None:
        sql = f"SELECT cid FROM {self.name} WHERE name = ?"
        results = self.query(sql, (name,))
        return results[0]["cid"] if results else None

    def search(self, keyword: str) -> list[TagData]:
        """进行模糊搜索"""
        if not keyword:
            return []
        # 空格分割关键词
        parts = [p.strip() for p in keyword.split() if p.strip()]
        # 生成 LIKE 语句
        like_clauses = []
        params = []
        for p in parts:
            like_clauses.append("""(name LIKE ?)""")
            params.extend([f"%{p}%"])
        where_sql = " AND ".join(like_clauses)
        sql = f"""
            SELECT * FROM {self.name}
            WHERE {where_sql}
            ORDER BY orders DESC
        """
        results = self.query(sql, tuple(params))
        return TagData.from_dict_list(results)



class DataExcerpts(IdTableHelper):
    """摘录数据类"""
    __slots__ = ('cursor', 'name', 'columns', 'keys', 'id_column', 'excerpt_tags')
    def __init__(self, cursor: sqlite3.Cursor, excerpt_tags: DataExcerptTags):
        columns = [('cid', str),
                ('content', str),
                ('source', str),
                ('title', str),
                ('author', str),
                ('note', str),
                ('created_at', str)]
        super().__init__(cursor, "excerpts", columns, "cid")
        self.excerpt_tags: DataExcerptTags = excerpt_tags
        self.create_table()

    def create_table(self) -> None:
        """
        CREATE TABLE IF NOT EXISTS excerpts - 创建一个名为excerpts的表，如果该表已经存在则不执行创建操作
        cid TEXT PRIMARY KEY - 创建一个文本类型的主键字段cid，用于唯一标识每条摘录
        content TEXT NOT NULL - 创建一个文本类型的content字段，用于存储摘录内容，不允许为空
        source TEXT NOT NULL - 创建一个文本类型的source字段，用于存储摘录来源，不允许为空
        created_at TEXT NOT NULL - 创建一个文本类型的created_at字段，用于记录创建时间，不允许为空
        updated_at TEXT NOT NULL - 创建一个文本类型的updated_at字段，用于记录更新时间，不允许为空
        """
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.name} (
                cid TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

    def add_excerpt(self, content: str, source: str, title: str,
                        author: str, note: str, tag_cids: list[str]) -> str:
        """添加新摘录"""

        cid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        if not tag_cids:
            tag_cids = ["default"]
        excerpt = ExcerptData(cid, content, source or "未知", title or "无",
                              author or "佚名", note, now, tag_cids).to_dict()
        excerpt.pop("tag_cids")
        self.insert([excerpt])
        self.excerpt_tags.add_tags(cid, tag_cids)
        return cid

    def update_excerpt(self, cid: str, content: str = None, source: str = None, title: str = None,
                       author: str = None, note: str = None, tag_cids: list[str] = None) -> bool:
        """更新摘录"""
        updates = {}
        if content is not None:
            updates['content'] = content
        if source is not None:
            updates['source'] = source
        if title is not None:
            updates['title'] = title
        if author is not None:
            updates['author'] = author
        if note is not None:
            updates['note'] = note
        if updates:
            self.update(updates, "cid = ?", (cid,))
        if tag_cids == []:
            tag_cids = ["default"]
        self.excerpt_tags.update_tags(cid, tag_cids)
        return True
    
    def insert_or_update_excerpts(self, records: list[ExcerptData]) -> None:
        """插入或更新摘录记录及其标签（推荐实现）"""
        # 1. 构建主表数据
        excerpts_data = []
        for record in records:
            data = record.to_dict()
            data.pop("tag_cids")
            excerpts_data.append(data)
        # 2. 先 upsert 主表（确保每条摘录存在）
        self.insert_or_update_upsert(excerpts_data)
        # 3. 再更新每条摘录的标签（删除旧的、插入新的）
        for record in records:
            self.excerpt_tags.update_tags(record.cid, record.tag_cids)

    def get_with_tags(self, cid: str) -> Optional[ExcerptData]:
        """获取摘录及其标签"""
        excerpt = self.get_line(cid)
        if not excerpt:
            return None
        excerpt["tag_cids"] = self.excerpt_tags.get_tags(cid)
        return ExcerptData.from_dict(excerpt)

    def query_to_excerpt(self, excerpts: list[dict]) -> Optional[ExcerptData]:
        result = []
        for excerpt in excerpts:
            excerpt["tag_cids"] = self.excerpt_tags.get_tags(excerpt["cid"])
            result.append(ExcerptData.from_dict(excerpt))
        return result

    def get_excerpts(self, cids: list[str]) -> list[ExcerptData]:
        """批量获取摘录"""
        if not cids:
            return []
        placeholders = ','.join(['?'] * len(cids))
        sql = f"SELECT * FROM {self.name} WHERE cid IN ({placeholders})"
        excerpts = self.query(sql, tuple(cids))
        return self.query_to_excerpt(excerpts)

    def get_all_excerpts(self) -> list[ExcerptData]:
        """批量获取摘录"""
        return self.query_to_excerpt(self.get_all())

    def delete_excerpt(self, cid: str):
        '''删除摘录及其所有标签关联'''
        self.delete_by_cid(cid)
        self.excerpt_tags.delete("excerpt_cid = ?", (cid,))

    def get_by_author(self, author: str) -> list[ExcerptData]:
        """获取指定作者的所有摘录"""
        sql = f"SELECT * FROM {self.name} WHERE author = ?"
        excerpts = self.query(sql, (author,))
        return self.query_to_excerpt(excerpts)

    def get_by_source(self, source: str) -> list[ExcerptData]:
        """获取指定来源的所有摘录"""
        sql = f"SELECT * FROM {self.name} WHERE source = ?"
        excerpts = self.query(sql, (source,))
        return self.query_to_excerpt(excerpts)

    def search(self, keyword: str) -> list[ExcerptData]:
        """在标题、来源、作者、相关、正文进行模糊搜索"""
        if not keyword:
            return []
        # 空格分割关键词
        parts = [p.strip() for p in keyword.split() if p.strip()]
        # 生成 LIKE 语句
        like_clauses = []
        params = []
        for p in parts:
            like_clauses.append("""
                (content LIKE ? OR
                title   LIKE ? OR
                author  LIKE ? OR
                note  LIKE ? OR
                source  LIKE ?)
            """)
            like_param = f"%{p}%"
            params.extend([like_param] * 5)
        where_sql = " AND ".join(like_clauses)
        sql = f"""
            SELECT * FROM {self.name}
            WHERE {where_sql}
            ORDER BY created_at DESC
        """
        excerpts = self.query(sql, tuple(params))
        return self.query_to_excerpt(excerpts)




class SqlDataManager(SqlbaseHelper):
    """
    数据库管理器类，用于处理标签和摘录数据的存储与检索
    """
    _instance = None
    def init_database(self) -> None:
        """初始化数据库连接和表结构"""
        super().init_database()
        # 创建中间表
        excerpt_tags = DataExcerptTags(self.cursor)
        self.add_table_helper(excerpt_tags)
        # 创建标签表
        tags = DataTags(self.cursor, excerpt_tags)
        self.add_table_helper(tags)
        # 创建摘录表
        excerpts = DataExcerpts(self.cursor, excerpt_tags)
        self.add_table_helper(excerpts)
        self.conn.commit()
    
    def get_tags_helper(self) -> DataTags:
        return self.table_helpers["tags"]
    
    def get_excerpts_helper(self) -> DataExcerpts:
        return self.table_helpers["excerpts"]

    def get_tag(self, tag_id: str) -> Optional[TagData]:
        return self.get_tags_helper().get_item(tag_id)

    def get_excerpt(self, excerpt_id: str) -> Optional[ExcerptData]:
        result = self.get_excerpts_helper().get_excerpts([excerpt_id])
        if result:
            return result[0]
        return None

    def get_tag_excerpts_count(self, tag_id: str) -> int:
        return self.get_tags_helper().get_excerpts_count(tag_id)

    def get_all_tags(self) -> list[TagData]:
        return self.get_tags_helper().get_all_by_order()
    
    def get_all_excerpts(self) -> list[TagData]:
        return self.get_excerpts_helper().get_all_excerpts()

    def reset_data(self) -> None:
        for table in self.table_helpers.values():
            table.delete_table()
        self.conn.commit()
        self.init_database()
    
    @classmethod
    def instance(cls) -> 'SqlDataManager':
        return cls._instance

    def set_instance(self) -> None:
        SqlDataManager._instance = self

    def update_excerpt(self, new: ExcerptData, old: ExcerptData = None) -> ExcerptData:
        """更新"""
        excerpt = ExcerptData.update(new, old)
        self.get_excerpts_helper().insert_or_update_excerpts([excerpt])
        self.conn.commit()
        return excerpt

    def insert_excerpts(self, records: list[ExcerptData]) -> None:
        """插入或更新摘录记录及其标签"""
        for record in records:
            ExcerptData.update(record, None)
        self.get_excerpts_helper().insert_or_update_excerpts(records)
        self.conn.commit()
    
    def insert_tags_names(self, tags: list[str]) -> None:
        tag_names = set([tag.name for tag in self.get_tags_helper().get_all_by_order()])
        for tag in tags:
            if tag in tag_names:
                continue
            self.get_tags_helper().add_or_update(uuid.uuid4(), tag)
            tag_names.add(tag)
        self.conn.commit()
    
    def insert_excerpts_dict(self, excerpts: list[dict]) -> None:
        for excerpt in excerpts:
            tags = excerpt.pop("tags")
            excerpt["tag_cids"] = [self.get_tags_helper().get_cid(tag) for tag in tags]
        self.insert_excerpts(ExcerptData.from_dict_list(excerpts))