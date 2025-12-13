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