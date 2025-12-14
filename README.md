[English](#) | [中文](README_zh.md)

### Text Excerpt Tool

This program is used to extract text snippets. The program uses Sqlite for storage, PySide6 and flask&HTML for the interface.

### Structure of Excerpt Data

The structure of an excerpt is as follows:

```md
Tag: Starts with # (the # at the beginning of the file, newline+#, or # on the tag line). One or more lines. Each tag must be on a single line and contain only Chinese/English characters, numbers, and operators. Multiple tags can be spread across multiple lines until another identifier appears.
Creation Time: Starts with %, one line.
Source: Starts with @ (newline+@), one line.
Title: Enclosed in '《》' (newline+《), one line.
Author: Should start with '作者：' (newline+作者：), one line.
Body Text: No starting identifier, multiple lines, empty lines are ignored, continues until another identifier.
Body Footnote: Marked with '[]' within the body text, containing only Chinese/English characters and numbers.
Note: Starts with '注释：' (newline+注释：), multiple lines, empty lines are ignored, continues until another identifier.
Related: Starts with '相关：' (newline+相关：), multiple lines, empty lines are ignored, continues until another identifier.
Attachment: Starts with '相关：' (newline+附件：), multiple lines, empty lines are ignored, one entry per line, continues until another identifier.
```

Note: Body footnotes belong to the body text, only the rendering mode is different.

Note: The UI has not implemented rendering for Note, Related, and Attachment items.

### Starting the Program

Run [main.py](main.py) to start the file selection program:

```python
from excerpts import qt_run

qt_run()
```

```
from excerpts import html_run

html_run()
```

The HTML page can be accessed at:
 http://127.0.0.1:5000

Alternatively, run the following command to start the Qt UI and open a specific file:

```python
from excerpts import qt_run

qt_run(file_name="excerpts1.db")
```

```
from excerpts import html_run

html_run()
```

The HTML page can be accessed directly at:
 http://127.0.0.1:5000/excerpts1.db

![image-20251213195748811](README.assets/image-20251213195748811.png)

![image-20251213200121033](README.assets/image-20251213200121033.png)

### Tag Editing

Click the "⚙️" to the right of "Tag Categories" to open the tag editing interface.

- Select a tag — Delete tag
- Select a tag — Drag to sort
- Double-click a tag — Modify name
- Enter a tag name to add a new tag
- Save tag modifications

![image-20251213200316632](README.assets/image-20251213200316632.png)

### Card Edit Zoom

Click a card to zoom in.

Click again to zoom out.

![image-20251213200607832](README.assets/image-20251213200607832.png)

### Card Editing / Creating New Cards

Click the "Edit" at the bottom right of a card to open the card editing interface.

Click "Create New Excerpt" to create a new card.

![image-20251213200713411](README.assets/image-20251213200713411.png)

### Data Management

Click "Data Management" to manage databases and files.

- New Database
- Switch Database
- Save As...
- Export Data
- Import Data
- Reset Database

![image-20251213200914627](README.assets/image-20251213200914627.png)

### Searching Excerpts

Enter content in the search box and click search to perform a search.

Search does not support searching tag content; searching tags must be done in the tag panel.

![image-20251213201033399](README.assets/image-20251213201033399.png)

![image-20251213201118693](README.assets/image-20251213201118693.png)

### Searching Tags

Search in the tag panel.

![image-20251213201338900](README.assets/image-20251213201338900.png)

### Batch Entry

- Import backed-up data

JSON files backed up via "Data Management - Export Data" can be merged into the current dataset in batches via "Import Data".

- Using Python programs

The [add_test.py](add_test.py) program can batch import formatted JSON excerpts.

```python
from excerpts import run

run(file_name="excerpts3.db", tags = tags, excerpts = excerpts)
```

The [parse_quotes_file_tool.py](parse_quotes_file_tool.py) program can batch format text paragraphs that conform to the "Structure of Excerpt Data".
