import sqlite3
from typing import Any, Iterable, Optional, Callable, Union
import json, datetime, uuid
from pathlib import Path


# import time
# import functools


# def timing_decorator(func: Callable) -> Callable:
#     """
#     装饰器：测量函数执行时间并打印结果
    
#     Args:
#         func: 被装饰的函数
        
#     Returns:
#         包装后的函数
#     """
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs) -> Any:
#         start_time = time.perf_counter()  # 使用高精度计时器
#         result = func(*args, **kwargs)    # 执行原函数
#         end_time = time.perf_counter()
        
#         execution_time = end_time - start_time
#         print(f"函数 {func.__name__} 执行时间: {execution_time:.6f} 秒")
        
#         return result
    
#     return wrapper



def prepare_value(value: Any) -> Any:
    '''将不同类型的值转换为可以存储在 SQLite 数据库中的标准格式
    字典、列表、元组类型：这些复杂数据结构会被转换为 JSON 字符串，方便存储和后续解析。
    日期、时间、datetime 类型：这些类型会被转换为 ISO 8601 格式的字符串（如 YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS），这是 SQLite 中常见的存储日期/时间的格式。
    UUID 类型：UUID 会被转换为字符串格式。
    其他类型：如果是普通的基础数据类型（如整数、浮动、字符串等），则直接返回原值。'''
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    elif isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    elif isinstance(value, uuid.UUID):
        return str(value)
    return value


COLUMN_TYPE_MAPPING = {
    float: "FLOAT",
    int: "INTEGER",
    bool: "INTEGER",
    str: "TEXT",
    dict: "TEXT",
    tuple: "TEXT",
    list: "TEXT",
    bytes: "BLOB",
    bytearray: "BLOB",
    memoryview: "BLOB",
    datetime.datetime: "TEXT",
    datetime.date: "TEXT",
    datetime.time: "TEXT",
    datetime.timedelta: "TEXT",
    type(None): "TEXT",
    uuid.UUID: "TEXT",
    # SQLite explicit types
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "FLOAT": "FLOAT",
    "BLOB": "BLOB",
    "text": "TEXT",
    "str": "TEXT",
    "integer": "INTEGER",
    "int": "INTEGER",
    "float": "FLOAT",
    "blob": "BLOB",
    "bytes": "BLOB",
}




class TableHelper:
    """
    封装了SQLite3的游标，提供了一些常用的方法。
    """
    __slots__ = ('cursor', 'name', 'columns', 'keys')
    def __init__(self, cursor: sqlite3.Cursor, name: str, columns: list[tuple[str, str]]):
        '''
        :param name: 表名
        :param columns: 将列名映射到其类型的列表对，例如 ``[("name", str), ("age", int)]``
        '''
        self.cursor: sqlite3.Cursor = cursor
        self.name: str = name
        self.columns: list[tuple[str, str]] = columns
        self.keys = [c[0] for c in columns]

    def item_count(self, column, value):
        self.cursor.execute(f"SELECT COUNT(*) FROM [{self.name}] WHERE [{column}] = ?", (value,))
        return self.cursor.fetchone()[0]
    
    def count(self) -> int:
        """查询表中的记录总数"""
        self.cursor.execute(f"SELECT COUNT(*) FROM [{self.name}]")
        return self.cursor.fetchone()[0]

    def get_insert_sql(self, keys: list[str], util: str = "") -> str:
        '''生成插入语句'''
        placeholders = ", ".join(["?"] * len(keys))
        columns_str = ", ".join([f"[{col}]" for col in keys])
        util = f" OR {util}" if util else ""
        return f"INSERT{util} INTO [{self.name}] ({columns_str}) VALUES ({placeholders})"

    def insert(self, records: Union[dict[str, Any], Iterable[dict[str, Any]]]) -> None:
        '''插入一条或多条记录'''
        if isinstance(records, dict):
            records = [records]
        columns = list(records[0].keys())
        self.validate_column_names(columns)
    
        data = [tuple(prepare_value(rec.get(col)) for col in columns) for rec in records]
        self.cursor.executemany(self.get_insert_sql(columns), data)

    def update(self, updates: dict[str, Any], where: str, params: tuple = ()) -> None:
        """
        更新记录
        通用 UPDATE 操作（支持复合主键）。
        - 自动禁止更新主键列（更安全）
        Args:
            updates: 要更新的字段和值
            where: WHERE子句
            params: WHERE子句的参数
        """
        self.validate_column_names(updates.keys())
        # ---- 获取主键列（支持复合主键）----
        self.cursor.execute(f"PRAGMA table_info([{self.name}])")
        pk_cols = [row[1] for row in self.cursor.fetchall() if row[5] > 0]
        # ---- 禁止更新主键列 ----
        for pk in pk_cols:
            if pk in updates:
                raise ValueError(f"Cannot update primary key column '{pk}'")
        # ---- 构建 SQL ----
        set_clause = ", ".join(f"[{col}] = ?" for col in updates.keys())
        values = [prepare_value(v) for v in updates.values()]
        sql = f"UPDATE [{self.name}] SET {set_clause} WHERE {where}"
        # ---- 执行 ----
        self.cursor.execute(sql, tuple(values) + params)
    
    def insert_or_update(self,records: Union[dict[str, Any], Iterable[dict[str, Any]]]) -> None:
        """
        通用 insert_or_update，支持复合主键。
        要求：主键列必须在表定义中声明过。
        """
        # --- 规范化 records ---
        if isinstance(records, dict):
            records = [records]
        records = list(records)
        if not records:
            return
        # --- 找到表的主键列 ---
        # 需要 cursor.execute("PRAGMA table_info(table)")
        self.cursor.execute(f"PRAGMA table_info([{self.name}])")
        table_info = self.cursor.fetchall()
        pk_cols = [row[1] for row in table_info if row[5] > 0]  # row[5] = pk flag
        if not pk_cols:
            raise ValueError(f"Table '{self.name}' has no primary key; cannot use insert_or_update()")
        # --- 验证 pk 存在于记录中 ---
        for pk in pk_cols:
            for rec in records:
                if pk not in rec:
                    raise ValueError(f"Record missing primary key field '{pk}'")
        # --- 准备字段列表 ---
        cols = list(records[0].keys())
        self.validate_column_names(cols)
        # --- 查询数据库中已存在的主键组合 ---
        # 提取主键值元组
        pk_value_list = [
            tuple(prepare_value(rec[pk]) for pk in pk_cols)
            for rec in records
        ]
        # 构建 WHERE pk IN ((?,?),(?,?)) 形式的查询
        placeholders = ",".join(
            "(" + ",".join("?" for _ in pk_cols) + ")"
            for _ in pk_value_list
        )
        flat_params = [v for tpl in pk_value_list for v in tpl]
        sql = (
            f"SELECT {', '.join(f'[{pk}]' for pk in pk_cols)} "
            f"FROM [{self.name}] "
            f"WHERE ({', '.join(f'[{pk}]' for pk in pk_cols)}) IN ({placeholders})"
        )
        self.cursor.execute(sql, flat_params)
        existing_pk_set = {tuple(row) for row in self.cursor.fetchall()}
        # --- 分成需要 insert 的和需要 update 的 ---
        inserts = []
        updates = []
        for rec in records:
            pk_tuple = tuple(prepare_value(rec[pk]) for pk in pk_cols)
            if pk_tuple in existing_pk_set:
                updates.append(rec)
            else:
                inserts.append(rec)
        # --- 执行插入 ---
        if inserts:
            insert_data = [
                tuple(prepare_value(rec[col]) for col in cols)
                for rec in inserts
            ]
            self.cursor.executemany(self.get_insert_sql(cols), insert_data)
        # --- 执行更新（逐条更新） ---
        if updates:
            set_clause = ", ".join(f"[{col}] = ?" for col in cols if col not in pk_cols)
            if set_clause:  # 若只有主键列，则无需更新
                update_cols = [col for col in cols if col not in pk_cols]
                for rec in updates:
                    update_values = [prepare_value(rec[col]) for col in update_cols]
                    pk_values = [prepare_value(rec[pk]) for pk in pk_cols]
                    sql = (
                        f"UPDATE [{self.name}] SET {set_clause} "
                        f"WHERE " + " AND ".join(f"[{pk}] = ?" for pk in pk_cols)
                    )
                    self.cursor.execute(sql, tuple(update_values + pk_values))

    def delete(self, where: str, params: tuple = ()) -> None:
        """
        删除记录
        Args:
            where: WHERE子句
            params: WHERE子句的参数
        """
        sql = f"DELETE FROM [{self.name}] WHERE {where}"
        self.cursor.execute(sql, params)

    def get_all(self, where: Optional[str] = None, order_by: Optional[str] = None) -> list[dict[str, Any]]:
        """
        获取所有记录
        Args:
            where: WHERE子句
            order_by: ORDER BY子句
        Returns:
            包含所有记录的字典列表
        """
        sql = f"SELECT * FROM [{self.name}]"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        self.cursor.execute(sql)
        columns = [col[0] for col in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        执行自定义查询
        Args:
            sql：一个字符串，表示你要执行的 SQL 查询语句。它可以是任何有效的 SQL 查询语句（例如 SELECT * FROM table_name）。
            params：一个元组，包含执行 SQL 查询时的参数。如果你的 SQL 查询语句中有占位符（?），可以在此传递参数值。
        Returns:
            返回一个列表，列表中的每个元素是一个字典，表示查询结果中的一行数据。字典的键是数据库表中的列名，值是对应的列数据。
        
        假设有一个名为 tags 的表，包含以下列：id, name, color, orders。我们可以使用 query() 方法来执行查询。
        示例 1：查询所有记录
            tags_helper = db.get_table_helper("tags")
            tags = tags_helper.query("SELECT * FROM [tags]")
            # 输出查询结果
            print(tags)[
                            {"id": "1", "name": "tag1", "color": "#ff0000", "orders": 1},
                            {"id": "2", "name": "tag2", "color": "#00ff00", "orders": 2}
                        ]
        示例 2：使用 WHERE 子句查询特定记录
            tags_helper = db.get_table_helper("tags")
            tags = tags_helper.query("SELECT * FROM [tags] WHERE color = ?", ("#ff0000",))
            # 输出查询结果
            print(tags)[
                            {"id": "1", "name": "tag1", "color": "#ff0000", "orders": 1}
                        ]
        示例 3：使用 ORDER BY 子句查询并排序
            tags_helper = db.get_table_helper("tags")
            tags = tags_helper.query("SELECT * FROM [tags] ORDER BY orders DESC")
            # 输出查询结果
            print(tags)[
                            {"id": "2", "name": "tag2", "color": "#00ff00", "orders": 2},
                            {"id": "1", "name": "tag1", "color": "#ff0000", "orders": 1}
                        ]
        示例 4：查询单个值
            你也可以使用 query() 来执行其他类型的查询，例如聚合查询。以下是一个查询记录数的示例：
            tags_helper = db.get_table_helper("tags")
            count = tags_helper.query("SELECT COUNT(*) FROM [tags]")
            # 输出查询结果
            print(count)[{"COUNT(*)": 2}]
        """
        self.cursor.execute(sql, params)
        if self.cursor.description:
            columns = [col[0] for col in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        return []

    def delete_table(self):
        # 删除表，如果表存在的话
        self.cursor.execute(f'DROP TABLE IF EXISTS {self.name}')
    
    @staticmethod
    def validate_column_names(columns):
        '''验证列名是否有效，确保列名中不包含非法字符 [ 和 ]'''
        for column in columns:
            if "[" in column or "]" in column:
                raise ValueError("'[' or ']' not allowed in column names")


class IdTableHelper(TableHelper):
    """
    封装了SQLite3的游标，改对象有一个唯一的ID字段，用于唯一标识记录。
    """
    __slots__ = ('cursor', 'name', 'columns', 'keys', 'id_column')
    def __init__(self, cursor: sqlite3.Cursor, name: str,
                 columns: list[tuple[str, str]], id_column: str):
        '''
        :param name: 表名
        :param columns: 将列名映射到其类型的列表对，例如 ``[("name", str), ("age", int)]``
        '''
        super().__init__(cursor, name, columns)
        if id_column not in self.keys:
            raise ValueError(f"{id_column} is not a column in {name}")
        if self.columns[self.keys.index(id_column)][1] != str:
            print(id_column,self.keys, self.columns[self.keys.index(id_column)])
            raise ValueError(f"{id_column} is not a string column in {name}")
        self.id_column: str = id_column

    def get_line(self, line_id: str) -> Optional[dict[Any]]:
        self.cursor.execute(f"SELECT * FROM [{self.name}] WHERE [{self.id_column}] = ?", (line_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        return dict(zip(self.keys, row))

    def insert_or_update(self, records: Union[dict[str, Any], Iterable[dict[str, Any]]]) -> None:
        '''更新或插入一条或多条记录'''
        if isinstance(records, dict):
            records = [records]
        if not records:
            return
        columns = list(records[0].keys())
        self.validate_column_names(columns)
        
        # 批量检查存在的记录
        id_values = [prepare_value(record[self.id_column]) for record in records]
        placeholders = ", ".join(["?"] * len(id_values))
        
        # 查询已存在的 ID
        existing_sql = f"SELECT [{self.id_column}] FROM [{self.name}] WHERE [{self.id_column}] IN ({placeholders})"
        self.cursor.execute(existing_sql, id_values)
        existing_ids = {row[0] for row in self.cursor.fetchall()}
        
        # 分离需要插入和更新的记录
        records_to_insert = []
        records_to_update = []
        
        for record in records:
            id_value = prepare_value(record[self.id_column])
            if id_value in existing_ids:
                records_to_update.append(record)
            else:
                records_to_insert.append(record)
        
        # 批量插入新记录
        if records_to_insert:
            insert_data = []
            for record in records_to_insert:
                row_data = [prepare_value(record.get(col)) for col in columns]
                insert_data.append(tuple(row_data))
            
            self.cursor.executemany(self.get_insert_sql(columns), insert_data)
        
        # 批量更新现有记录
        for record in records_to_update:
            id_value = prepare_value(record[self.id_column])
            # 创建不包含主键的更新字典
            updates = {col: record[col] for col in columns if col != self.id_column}
            if updates:  # 确保有需要更新的字段
                self.update(updates, f"[{self.id_column}] = ?", (id_value,))

    def insert_or_update_upsert(self, records: Union[dict[str, Any], Iterable[dict[str, Any]]]) -> None:
        '''使用 UPSERT 语法插入或更新记录（更高效）'''
        if isinstance(records, dict):
            records = [records]
        if not records:
            return
        columns = list(records[0].keys())
        self.validate_column_names(columns)
        
        # 准备数据
        data = [tuple(prepare_value(r.get(col)) for col in columns) for r in records]
        
        # 构建 UPSERT SQL
        placeholders = ", ".join(["?"] * len(columns))
        columns_str = ", ".join([f"[{col}]" for col in columns])
        
        # 构建 SET 子句（更新除主键外的所有列）
        set_clause = ", ".join([f"[{col}] = excluded.[{col}]" for col in columns if col != self.id_column])
        
        upsert_sql = f"""
        INSERT INTO [{self.name}] ({columns_str}) 
        VALUES ({placeholders})
        ON CONFLICT([{self.id_column}]) DO UPDATE SET {set_clause}
        """
        
        self.cursor.executemany(upsert_sql, data)

    def update_pairs(self, pairs: dict[str, Any], other_column: str) -> None:
        """更新记录（按键值对）"""
        params = [(other, id_) for (id_, other) in pairs.items()]
        sql = f"UPDATE [{self.name}] SET [{other_column}] = ? WHERE [{self.id_column}] = ?"
        self.cursor.executemany(sql, params)

    def delete_by_cid(self, line_id: str) -> None:
        """
        删除记录
        """
        super().delete(f"[{self.id_column}] = ?", (line_id,))





class SqlbaseHelper:
    """
    数据库管理器类，用于处理数据的存储与检索
    """
    __slots__ = ('db_path', 'db_key', 'conn', 'cursor', 'table_helpers')
    _instances: dict[int, 'SqlbaseHelper'] = {}
    def __init__(self, db_path: Path) -> None:
        """
        初始化数据库管理器
        Args:
            db_path (str): 数据库文件路径，默认为""
        """
        self.db_path: Path = db_path
        self.db_key = hash(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.table_helpers: dict[str, TableHelper] = {}
        self.init_database()

    def init_database(self) -> None:
        """初始化数据库连接和表结构"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")  # 启用外键
            self.cursor = self.conn.cursor()
    
    @classmethod
    def instance(cls, key: int = 0) -> Optional['SqlbaseHelper']:
        return cls._instances.get(key, None)

    def set_instance(self, key: int = None) -> None:
        """
        将当前实例注册为指定键的实例。
        """
        if key == 0:
            self.__class__._instances[0] = self
        elif key is None:
            self.__class__._instances[self.db_key] = self
        else:
            self.db_key = key
            self.__class__._instances[key] = self

    def create_table_helper(self, name: str, columns: list[tuple[str, str]], 
                           pk: Union[str, list[str]] = "id", 
                           not_null: Optional[list[str]] = None,
                           foreign_columns: Optional[dict[str, tuple[str, str]]] = None,
                           if_not_exists: bool = True, on_delete: str = "CASCADE") -> TableHelper:
        '''
        创建表并返回TableHelper实例
        :param name: 表名
        :param columns: 将列名映射到其类型的列表对，例如 ``[("name", str), ("age", int)]``
        :param pk: 主键列
        :param not_null: NOT NULL约束的列
        :param foreign_columns: 外键定义
        :param if_not_exists: 是否使用IF NOT EXISTS
        :param on_delete: 设置外键删除行为，默认为 "CASCADE"。默认为 CASCADE，也可以设置为 SET NULL 或其他选项。
        '''
        cursor = TableHelper(self.get_cursor(), name, columns)
        if isinstance(pk, str) and pk not in cursor.keys:
            raise ValueError("pk not in columns")
        cursor.create_table(pk, not_null or [], foreign_columns or {}, if_not_exists, on_delete)
        self.table_helpers[name] = cursor
        return cursor

    def add_table_helper(self, cursor: TableHelper) -> None:
        '''
        '''
        self.table_helpers[cursor.name] = cursor

    def get_table_helper(self, name: str) -> TableHelper:
        """获取表的TableHelper实例"""
        if name not in self.table_helpers:
            raise ValueError(f"Table helper for '{name}' not found")
        return self.table_helpers[name]
    
    def get_cursor(self) -> sqlite3.Cursor:
        """获取数据库游标"""
        if self.cursor is None:
            self.init_database()
        return self.cursor

    def commit(self) -> None:
        """提交事务"""
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        """回滚事务"""
        if self.conn:
            self.conn.rollback()

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出时关闭连接"""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
