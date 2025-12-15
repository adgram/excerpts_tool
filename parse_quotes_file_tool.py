'''可以按照一定的规则将段落格式化为json
段落结构如下：

标签：以#开头（文件开头的#，换行+#，标签行的#），一行或多行，每个标签必须在一行内完成且仅包含中英文、数字和运算符，多个标签可以分布在多行，直至其他标识。
创建时间：以%开头，一行。
来源：以@开头（换行+@），一行。
标题：以‘《》’包括（换行+《），一行。
作者：作者应以‘作者：’开头（换行+作者：），一行。
正文：无开头标识符，多行，空行不计，直至其他标识。
正文角标：正文中以‘[]’标注，仅包含中英文、数字。
注释：以‘注释：’开头（换行+注释：），多行，空行不计，直至其他标识。
相关：以‘相关：’开头（换行+相关：），多行，空行不计，直至其他标识。
附件：以‘相关：’开头（换行+附件：），多行，空行不计，每行一条，直至其他标识。

json格式如下：
{
  "tags": [
    "实体小说",
    "话剧影视"
  ],
  "excerpts": [
    {
      "source": "我很重要",
      "author": "毕淑敏",
      "tags": [
        "议论散文",
        "现代诗歌"
      ],
      "content": "是的，我很重要。我们每一个人都应该有勇气这样说。"
    }
    ]
}

注意：这里的excerpts不能直接导入程序，因为tags值类型不为tags_cid
'''


import re, json
from typing import TypedDict


class ExcerptDict(TypedDict):
    cid        : str            = '' # 摘录ID
    content    : str            = '' # 摘录内容
    source     : str            = '' # 摘录来源
    title      : str            = '' # 摘录标题
    author     : str            = '' # 摘录作者
    note       : str            = '' # 摘录笔记
    created_at : str            = '' # 创建时间
    tags       : list[str]      = [] # 标签ID列表
    tag_cids   : list[str]      = [] # 标签ID列表


def parse_quotes_file(file_path: str) -> list[ExcerptDict]:
    """
    解析包含多个引用的文本文件
    Args:
        file_path: 文本文件路径
    Returns:
        解析后的Quote对象列表
    """
    quotes = []
    p_tags = set()
    
    # try:
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    # 按空行分割不同的引用段落
    # 使用正则表达式分割，确保处理多个连续空行
    sections = re.split(r'\n\s*\n', content.strip())
    for section in sections:
        if not section.strip():
            continue  # 跳过空段落
        # 解析每个段落
        lines = section.strip().split('\n')
        # 内容部分（可能有多行，直到遇到"作者："）
        excerpt = ExcerptDict()
        tags = set()
        content = []
        for line in lines:
            line = line.strip()
            if line.startswith('作者：'):
                excerpt["author"] = line[3:].strip()  # 去掉"作者："前缀
            elif line.startswith('相关：'):
                excerpt["note"] = line[3:].strip()  # 去掉"相关："前缀
            elif line.startswith('《') and line.endswith('》'):
                excerpt["title"] = line[1:-1].strip()
            elif line.startswith('@'):
                excerpt["source"] = line[1:].strip()  # 去掉"@"前缀
            elif line.startswith('#'):
                ns = set(line[1:].strip().split("#"))
                tags |= ns
                pass
            else:
                content.append(line)
        p_tags |= tags
        excerpt["tags"] = list(tags)
        excerpt["content"] = '\n'.join(content)
        quotes.append(excerpt)
    # except FileNotFoundError:
    #     print(f"错误：找不到文件 {file_path}")
    # except Exception as e:
    #     print(f"解析文件时出错: {e}")
    return quotes, list(p_tags)


def main():
    # 配置文件名
    input_file = "数据1.txt"  # 你的文本文件名
    output_file = "数据1.json"  # 输出JSON文件名
    
    quotes, tags = parse_quotes_file(input_file)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"tags": tags, "excerpts": quotes}, f, ensure_ascii=False, indent=2)
    




if __name__ == "__main__":
    main()