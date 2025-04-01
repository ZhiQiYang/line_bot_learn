from flask import Blueprint
import logging

# 創建藍圖
map_bp = Blueprint('map', __name__)

logger = logging.getLogger(__name__)

# 主題地圖數據 (示例)
MAPS = {
    "熱力學": {
        "image_url": "", # 實際應提供圖片URL
        "topics": ["熵", "焓", "自由能"],
        "resources": ["熱力學入門教程"]
    },
    "記憶術": {
        "image_url": "",
        "topics": ["宮殿法", "艾賓浩斯曲線"],
        "resources": ["超強記憶力訓練"]
    }
}

def handle_map_command(text):
    """處理主題地圖相關請求"""
    from linebot.models import TextSendMessage # 延遲導入

    topic = text.replace("地圖", "").strip()

    if topic in MAPS:
        # TODO: 實現創建Flex Message的功能
        # flex_content = create_map_flex_message(topic, MAPS[topic])
        # 臨時回應
        response_text = f"🗺️ {topic}學習地圖\n"
        response_text += "核心知識點:\n" + ", ".join(MAPS[topic]["topics"])
        response_text += "\n學習資源:\n" + ", ".join(MAPS[topic]["resources"])
        return response_text # 只返回文本，由 route_message 處理發送
    else:
        available_maps = "、".join(MAPS.keys())
        return f"抱歉，目前沒有「{topic}」的主題地圖。\n可用的地圖有：{available_maps}"

# TODO: (可選) 實現 create_map_flex_message 函數來創建更豐富的回應

# 確保至少有一個導出的函數或變量，以避免導入錯誤
def get_available_maps():
    return list(MAPS.keys())
