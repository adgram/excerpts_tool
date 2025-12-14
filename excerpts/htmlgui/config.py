
from pathlib import Path

ENV = 'development'
DEBUG = 'True'
SECRET_KEY = 'uiuvfdfhf6482bvvn1354'  	# 用于会话加密
SESSION_TYPE = 'filesystem'   			# session类型为文件
SESSION_PERMANENT = False      			# 关闭浏览器session就失效
SESSION_FILE_DIR = Path(__file__).parent/'session' # session文件保存目录

