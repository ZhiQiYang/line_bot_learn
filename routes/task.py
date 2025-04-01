from flask import Blueprint
import logging

# 創建藍圖
task_bp = Blueprint('task', __name__)

logger = logging.getLogger(__name__)

# 任務相關的函數（示例）
def handle_task_command(text):
    """處理任務相關命令"""
    from linebot.models import TextSendMessage # 延遲導入

    if text == "#今天任務":
        # TODO: 實現獲取今日任務的邏輯
        return "今天的任務列表正在準備中..."
    elif text.startswith("#打卡"):
        # TODO: 實現任務打卡的邏輯
        parts = text.split(" ", 1)
        if len(parts) > 1:
            task_info = parts[1]
            return f"已記錄打卡：{task_info}"
        else:
            return "打卡格式錯誤，請使用：#打卡 [內容] [時間]分鐘"
    else:
        # 如果沒有匹配的任務命令，可以返回 None 或特定的提示信息
        return None # 或者返回 "未知的任務命令"

# 確保至少有一個導出的函數或變量
def get_example_tasks():
    return ["讀書", "寫代碼"]
