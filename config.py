import os
import pytz

# 時區設定
TIMEZONE = pytz.timezone('Asia/Taipei')

# LINE API設定
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
USER_ID = os.environ.get('USER_ID')

# 數據庫設定
DATABASE_URL = os.environ.get('DATABASE_URL')

# 功能設定
ENABLE_AI_ASSISTANT = os.environ.get('ENABLE_AI_ASSISTANT', 'true').lower() == 'true'
AI_API_KEY = os.environ.get('AI_API_KEY', '')
MAX_CHALLENGES_PER_DAY = int(os.environ.get('MAX_CHALLENGES_PER_DAY', '10'))

# 文件路徑
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
IMAGES_DIR = os.path.join(RESOURCES_DIR, 'images')
TEMPLATES_DIR = os.path.join(RESOURCES_DIR, 'templates')

# 數據文件
TASKS_FILE = 'tasks.json'
CARDS_FILE = 'cards.json'
CHALLENGES_FILE = 'challenges.json'
CHARACTERS_FILE = 'characters.json'
