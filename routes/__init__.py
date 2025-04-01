# 路由模組初始化文件
from linebot.models import TextSendMessage
import logging

logger = logging.getLogger(__name__)

# 路由處理器入口點
def process_message(line_bot_api, text, user_id, reply_token):
    """根據消息前綴處理消息並路由到相應模組"""
    try:
        # 根據消息前綴決定使用哪個模組處理
        if text.startswith("熱力學地圖") or text.startswith("記憶術地圖"):
            from .map import handle_map_request
            handle_map_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("#今天任務") or text.startswith("#打卡"):
            from .task import handle_task_request
            handle_task_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("#挑戰"):
            from .challenge import handle_challenge_request
            handle_challenge_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("#AI"):
            from .ai import handle_ai_request
            handle_ai_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("#開始專注") or text.startswith("#專注"):
            from .focus import handle_focus_request
            handle_focus_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("#呼叫"):
            from .character import handle_character_request
            handle_character_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("/export-report") or text.startswith("#報告"):
            from .report import handle_report_request
            handle_report_request(line_bot_api, text, user_id, reply_token)
        
        elif text.startswith("#新增卡") or text.startswith("#卡片"):
            from .card import handle_card_request
            handle_card_request(line_bot_api, text, user_id, reply_token)
        
        else:
            # 通用命令處理
            handle_general_command(line_bot_api, text, user_id, reply_token)
            
    except ImportError as e:
        logger.error(f"模組導入錯誤: {e}")
        reply_text = "該功能尚未實現，敬請期待！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    except Exception as e:
        logger.error(f"處理消息時發生錯誤: {e}")
        reply_text = "處理您的請求時發生錯誤，請稍後再試。"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))

def handle_general_command(line_bot_api, text, user_id, reply_token):
    """處理通用命令，如幫助、設置等"""
    if text.lower() in ["help", "幫助", "#help", "#幫助"]:
        help_text = (
            "📚 學習助手使用指南 📚\n\n"
            "🗺️ 主題地圖:\n 熱力學地圖、記憶術地圖\n\n"
            "✅ 任務管理:\n #今天任務、#打卡 [內容] [時間]分鐘\n\n"
            "🔍 知識挑戰:\n #挑戰 [主題]\n\n"
            "🤖 AI協助:\n #AI [問題]\n\n"
            "⏱️ 專注模式:\n #開始專注、#專注 [主題] [時間]分鐘\n\n"
            "👥 角色協助:\n #呼叫 [角色名稱]\n\n"
            "📊 學習報告:\n /export-report、#報告\n\n"
            "🗃️ 記憶卡片:\n #新增卡 [前面]:[後面]、#卡片 [操作]"
        )
        line_bot_api.reply_message(reply_token, TextSendMessage(text=help_text))
    else:
        reply_text = "🤔 我不確定你想做什麼，請輸入「#幫助」查看可用指令"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
