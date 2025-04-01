from linebot.models import TextSendMessage, ImageSendMessage, FlexSendMessage
import os
import json
import logging

logger = logging.getLogger(__name__)

# 主題地圖數據
MAPS = {
    "熱力學": {
        "image_url": "https://example.com/thermodynamics_map.jpg",
        "topics": ["熵", "焓", "自由能", "熱力學第一定律", "熱力學第二定律"],
        "resources": ["熱力學入門教程", "物理學概論", "能量轉換實例"]
    },
    "記憶術": {
        "image_url": "https://example.com/memory_techniques_map.jpg",
        "topics": ["宮殿法", "艾賓浩斯曲線", "間隔重複", "聯想法", "視覺編碼"],
        "resources": ["超強記憶力訓練", "記憶冠軍的秘密", "快速記憶技巧"]
    }
}

def handle_map_request(line_bot_api, text, user_id, reply_token):
    """處理主題地圖相關請求"""
    # 提取主題名稱
    topic = text.replace("地圖", "").strip()
    
    if topic in MAPS:
        # 創建主題內容介紹Flex Message
        flex_content = create_map_flex_message(topic, MAPS[topic])
        
        # 回覆消息
        line_bot_api.reply_message(
            reply_token,
            [TextSendMessage(text=f"🗺️ {topic}學習地圖"), flex_content]
        )
    else:
        available_maps = "、".join(MAPS.keys())
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"抱歉，目前沒有「{topic}」的主題地圖。\n可用的地圖有：{available_maps}")
        )

def create_map_flex_message(topic, map_data):
    """創建地圖的Flex消息"""
    # 建立知識點列表
    topics_content = []
    for i, t in enumerate(map_data["topics"]):
        topics_content.append({
            "type": "text",
            "text": f"{i+1}. {t}",
            "size": "sm",
            "color": "#1DB446",
            "wrap": True
        })
    
    # 建立資源列表
    resources_content = []
    for i, r in enumerate(map_data["resources"]):
        resources_content.append({
            "type": "text",
            "text": f"📚 {r}",
            "size": "sm",
            "color": "#666666",
            "wrap": True
        })
    
    # 組合成完整Flex Message
    flex_message = FlexSendMessage(
        alt_text=f"{topic}學習地圖",
        contents={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{topic}學習地圖",
                        "weight": "bold",
                        "size": "xl"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "核心知識點",
                        "weight": "bold",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "sm",
                        "contents": topics_content
                    },
                    {
                        "type": "text",
                        "text": "學習資源",
                        "weight": "bold",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "sm",
                        "contents": resources_content
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "進行挑戰",
                            "text": f"#挑戰 {topic}"
                        },
                        "style": "primary"
                    }
                ]
            }
        }
    )
    return flex_message

def get_available_maps():
    """獲取可用的主題地圖列表"""
    return list(MAPS.keys())
