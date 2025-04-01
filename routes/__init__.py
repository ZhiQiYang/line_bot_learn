"""路由包初始化

這個包包含應用程序的所有路由和處理函數。
"""

# 導入各個模塊的藍圖
try:
    from routes.materials import materials_bp, handle_materials_command
except ImportError:
    print("Warning: materials module import failed")
    materials_bp = None
    handle_materials_command = None

try:
    from routes.convert import convert_bp, handle_convert_command
except ImportError:
    print("Warning: convert module import failed")
    convert_bp = None
    handle_convert_command = None

try:
    from routes.map import map_bp, handle_map_command
except ImportError:
    print("Warning: map module import failed")
    map_bp = None
    handle_map_command = None

try:
    from routes.search import search_bp, handle_search_command
except ImportError:
    print("Warning: search module import failed")
    search_bp = None
    handle_search_command = None

try:
    from routes.task import task_bp, handle_task_command
except ImportError:
    print("Warning: task module import failed")
    task_bp = None
    handle_task_command = None

# 導出模組
__all__ = [
    'materials', 'convert', 'map', 'search', 'task',
    'materials_bp', 'handle_materials_command',
    'convert_bp', 'handle_convert_command',
    'map_bp', 'handle_map_command',
    'search_bp', 'handle_search_command',
    'task_bp', 'handle_task_command'
]

# 處理消息分發
def route_message(line_bot_api, text, user_id, reply_token):
    """根據消息內容將請求分發到相應的處理函數"""
    from linebot.models import TextSendMessage
    
    # 嘗試調用各個模塊的處理函數

    # 處理時區轉換命令
    if handle_convert_command and text.startswith("#時區轉換"):
        response = handle_convert_command(text)
        if response:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response))
            return True

    # 處理搜索命令
    if handle_search_command and (text.startswith("#搜尋") or text.startswith("#搜索")):
        response = handle_search_command(text)
        if response:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response))
            return True

    # 處理地圖命令
    if handle_map_command and (text.startswith("熱力學地圖") or text.startswith("記憶術地圖")):
        response = handle_map_command(text)
        if response:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response))
            return True

    # 處理學習材料命令
    if handle_materials_command:
        response = handle_materials_command(text)
        if response:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response))
            return True

    # 處理任務命令
    if handle_task_command and (text.startswith("#今天任務") or text.startswith("#打卡")):
        response = handle_task_command(text)
        if response:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=response))
            return True

    # 如果沒有匹配的處理函數，返回False
    return False
