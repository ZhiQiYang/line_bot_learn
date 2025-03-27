import os
import json
import time
import random
import datetime
import threading
import logging
import requests
import re
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    URIAction, MessageAction
)
import schedule

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Flask
app = Flask(__name__)

# 從環境變數獲取配置
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
USER_ID = os.environ.get('USER_ID')  # 要發送訊息的使用者 ID
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 儲存任務的檔案
TASKS_FILE = 'tasks.json'
REFLECTIONS_FILE = 'reflections.json'
QUESTIONS_FILE = 'questions.json'

# 確保資料檔案存在
def ensure_file_exists(filename, default_content):
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(default_content, file, ensure_ascii=False, indent=2)

# 初始化資料檔案
def init_files():
    ensure_file_exists(TASKS_FILE, {"tasks": [], "daily_plan": {}})
    ensure_file_exists(REFLECTIONS_FILE, {"reflections": []})
    ensure_file_exists(QUESTIONS_FILE, {
        "morning": [
            "今天你最重要的一件事是什麼？",
            "你希望今天結束時能完成什麼？",
            "今天有什麼可能讓你分心的事情？你要如何應對？",
            "你今天最期待什麼事情？",
            "如果今天只能完成一件事，你會選擇做什麼？",
            "今天你想要專注發展哪方面的能力？",
            "有什麼小習慣是你今天想要堅持的？"
        ],
        "evening": [
            "今天你完成了什麼有意義的事？",
            "你今天遇到最大的阻力是什麼？",
            "今天有什麼事情讓你感到開心或有成就感？",
            "明天你想要改進什麼？",
            "今天你學到了什麼？",
            "今天你最感恩的一件事是什麼？",
            "今天有哪個決定你覺得做得特別好？"
        ],
        "deep": [
            "在過去的一個月中，你注意到自己有什麼成長或改變？",
            "目前有什麼事情正在阻礙你實現目標？你可以如何突破？",
            "如果回顧你人生中最有意義的幾個決定，有什麼共同點？",
            "你最近感到壓力的根源是什麼？有哪些方法可以幫助你減輕它？",
            "如果可以給一年前的自己一個建議，你會說什麼？"
        ]
    })
    logger.info("資料檔案初始化完成")


# 讀取資料
def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"讀取 {filename} 時發生錯誤: {e}")
        return None

# 儲存資料
def save_data(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"儲存 {filename} 時發生錯誤: {e}")
        return False

# 1. 修改任務結構，添加提醒相關字段
# 添加任務
def add_task(task_content, reminder_time=None):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 插入新任務
        cursor.execute(
            '''
            INSERT INTO tasks (content, reminder_time, progress) 
            VALUES (%s, %s, %s)
            ''',
            (task_content, reminder_time, 0)
        )
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        logger.error(f"新增任務時發生錯誤: {e}")
        return False
    
    finally:
        conn.close()

# 獲取任務列表
def get_tasks(completed=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        if completed is None:
            # 返回所有任務
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        else:
            # 根據完成狀態過濾
            cursor.execute(
                "SELECT * FROM tasks WHERE completed = %s ORDER BY created_at DESC",
                (completed,)
            )
        
        return cursor.fetchall()
    
    except Exception as e:
        logger.error(f"獲取任務時發生錯誤: {e}")
        return []
    
    finally:
        conn.close()

# 標記任務為已完成
def complete_task(task_content):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 更新任務狀態
        cursor.execute(
            '''
            UPDATE tasks 
            SET completed = TRUE, completed_at = CURRENT_TIMESTAMP 
            WHERE content = %s AND completed = FALSE
            ''',
            (task_content,)
        )
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        return affected_rows > 0
    
    except Exception as e:
        conn.rollback()
        logger.error(f"完成任務時發生錯誤: {e}")
        return False
    
    finally:
        conn.close()

# 獲取今日任務完成率
def get_today_progress():
    conn = get_connection()
    if not conn:
        return 0, 0, 0
    
    try:
        cursor = conn.cursor()
        
        # 獲取今天創建的所有任務
        cursor.execute(
            "SELECT COUNT(*) as total FROM tasks WHERE DATE(created_at) = CURRENT_DATE"
        )
        total = cursor.fetchone()['total']
        
        if total == 0:
            return 0, 0, 0
        
        # 獲取今天創建且已完成的任務
        cursor.execute(
            '''
            SELECT COUNT(*) as completed 
            FROM tasks 
            WHERE DATE(created_at) = CURRENT_DATE AND completed = TRUE
            '''
        )
        completed = cursor.fetchone()['completed']
        
        percentage = (completed / total) * 100
        return completed, total, percentage
    
    except Exception as e:
        logger.error(f"獲取進度時發生錯誤: {e}")
        return 0, 0, 0
    
    finally:
        conn.close()

# 儲存反思內容
def save_reflection(question, answer):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO reflections (question, answer) VALUES (%s, %s)",
            (question, answer)
        )
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        logger.error(f"儲存反思時發生錯誤: {e}")
        return False
    
    finally:
        conn.close()

# 獲取隨機問題
def get_random_question(time_of_day):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT content FROM questions WHERE time_of_day = %s ORDER BY RANDOM() LIMIT 1",
            (time_of_day,)
        )
        
        result = cursor.fetchone()
        return result['content'] if result else None
    
    except Exception as e:
        logger.error(f"獲取問題時發生錯誤: {e}")
        return None
    
    finally:
        conn.close()

# 設定每日計畫
def set_daily_plan(plan_data):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 清除現有計畫
        cursor.execute("DELETE FROM daily_plans")
        
        # 插入新計畫
        for time_slot, content in plan_data.items():
            cursor.execute(
                "INSERT INTO daily_plans (time_slot, content) VALUES (%s, %s)",
                (time_slot, content)
            )
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        logger.error(f"設定計畫時發生錯誤: {e}")
        return False
    
    finally:
        conn.close()

# 獲取每日計畫
def get_daily_plan():
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT time_slot, content FROM daily_plans")
        
        result = {}
        for row in cursor.fetchall():
            result[row['time_slot']] = row['content']
        
        return result
    
    except Exception as e:
        logger.error(f"獲取計畫時發生錯誤: {e}")
        return {}
    
    finally:
        conn.close()

# 設置任務提醒
def set_task_reminder(task_content, reminder_time):
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            UPDATE tasks 
            SET reminder_time = %s 
            WHERE content = %s AND completed = FALSE
            ''',
            (reminder_time, task_content)
        )
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        return affected_rows > 0
    
    except Exception as e:
        conn.rollback()
        logger.error(f"設置提醒時發生錯誤: {e}")
        return False
    
    finally:
        conn.close()

# 發送任務提醒
def send_task_reminder():
    conn = get_connection()
    if not conn:
        return
    
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    try:
        cursor = conn.cursor()
        
        # 獲取需要提醒的任務
        cursor.execute(
            '''
            SELECT id, content, created_at, progress
            FROM tasks
            WHERE completed = FALSE AND reminder_time = %s
            ''',
            (current_time,)
        )
        
        tasks = cursor.fetchall()
        
        for task in tasks:
            # 發送提醒
            message = f"⏰ 任務提醒：「{task['content']}」\n"
            
            # 如果有進度信息，添加到提醒中
            if task['progress'] > 0:
                message += f"目前進度: {task['progress']}%\n"
            
            # 添加創建時間信息
            created_date = task['created_at'].strftime("%Y-%m-%d")
            message += f"(建立於 {created_date})"
            
            send_line_message(USER_ID, message)
            
            # 更新上次提醒時間
            cursor.execute(
                '''
                UPDATE tasks
                SET last_reminded_at = CURRENT_TIMESTAMP
                WHERE id = %s
                ''',
                (task['id'],)
            )
        
        conn.commit()
    
    except Exception as e:
        conn.rollback()
        logger.error(f"發送提醒時發生錯誤: {e}")
    
    finally:
        conn.close()

# 設置自我請求的時間間隔（秒）
PING_INTERVAL = 840  # 14分鐘，略少於 Render 的 15 分鐘閒置限制

# 你的 Render 應用 URL（從環境變數獲取或使用預設值）
APP_URL = os.environ.get('APP_URL', 'https://line-bot-learn.onrender.com')

def keep_alive():
    """定期發送請求到自己的服務來保持活躍"""
    while True:
        try:
            response = requests.get(APP_URL)
            logger.info(f"Keep-alive ping sent. Response: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")
        
        # 等待到下一次 ping
        time.sleep(PING_INTERVAL)

# 在主應用啟動時啟動保活線程
def start_keep_alive_thread():
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("Keep-alive thread started")

# 2. 添加設置任務提醒的函數
def set_task_reminder(task_content, reminder_time):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    for task in data["tasks"]:
        if task["content"] == task_content and not task["completed"]:
            task["reminder_time"] = reminder_time
            return save_data(TASKS_FILE, data)
    
    return False

# 3. 添加發送任務提醒的函數
def send_task_reminder():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    
    data = load_data(TASKS_FILE)
    if not data:
        return
    
    # 檢查每個未完成的任務，看是否需要提醒
    for task in data["tasks"]:
        if not task["completed"] and task.get("reminder_time") == current_time:
            # 發送提醒
            message = f"⏰ 任務提醒：「{task['content']}」\n"
            
            # 如果有進度信息，添加到提醒中
            if task.get("progress", 0) > 0:
                message += f"目前進度: {task['progress']}%\n"
            
            # 添加創建時間信息
            created_date = task["created_at"].split()[0]  # 只取日期部分
            message += f"(建立於 {created_date})"
            
            send_line_message(USER_ID, message)
            
            # 更新上次提醒時間
            task["last_reminded_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 儲存更新後的任務數據
    save_data(TASKS_FILE, data)

# 4. 修改排程任務，添加定時檢查
def schedule_jobs():
    # 原有的早晚定時發送問題
    schedule.every().day.at("07:00").do(lambda: send_thinking_question(USER_ID, "morning"))
    schedule.every().day.at("21:00").do(lambda: send_thinking_question(USER_ID, "evening"))
    
    # 添加每分鐘檢查任務提醒
    schedule.every(1).minutes.do(send_task_reminder)
    
    # 執行排程任務的線程
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("排程任務已啟動")

# 新增測試路由
@app.route("/ping", methods=['GET'])
def ping():
    return "pong!", 200

# 健康檢查路由
@app.route("/", methods=['GET'])
def health_check():
    return "LINE Bot is running!", 200

# Flask 路由
@app.route("/callback", methods=['POST'])
def callback():
    # 嘗試獲取簽名，如果不存在則設為空字串
    signature = request.headers.get('X-Line-Signature', '')
    
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    
    # 指令處理
    if text.startswith("新增：") or text.startswith("新增:"):
        content = text[3:].strip()
        
        # 檢查是否有提醒時間設置（格式：任務內容 @HH:MM）
        reminder_time = None
        if " @" in content:
            content_parts = content.split(" @")
            task_content = content_parts[0].strip()
            time_part = content_parts[1].strip()
            
            # 驗證時間格式
            if re.match(r'^\d{1,2}:\d{2}$', time_part):
                reminder_time = time_part
            else:
                reply_text = "❌ 時間格式錯誤，請使用 HH:MM 格式（例如 08:30）"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                return
        else:
            task_content = content
        
        if add_task(task_content, reminder_time):
            if reminder_time:
                reply_text = f"✅ 已新增任務：{task_content}，將在每天 {reminder_time} 提醒"
            else:
                reply_text = f"✅ 已新增任務：{task_content}"
        else:
            reply_text = "❌ 新增任務失敗，請稍後再試"
    
    elif text.startswith("完成：") or text.startswith("完成:"):
        task_content = text[3:].strip()
        if complete_task(task_content):
            reply_text = f"🎉 恭喜完成任務：{task_content}"
        else:
            reply_text = "❌ 找不到該未完成任務，請確認任務名稱"
    
    elif text.startswith("提醒：") or text.startswith("提醒:"):
        # 格式：提醒：任務內容=08:30
        parts = text[3:].strip().split('=')
        
        if len(parts) != 2:
            reply_text = "❌ 格式錯誤，請使用「提醒：任務內容=HH:MM」的格式"
        else:
            task_content = parts[0].strip()
            reminder_time = parts[1].strip()
            
            # 簡單驗證時間格式
            if re.match(r'^\d{1,2}:\d{2}$', reminder_time):
                if set_task_reminder(task_content, reminder_time):
                    reply_text = f"⏰ 已設置對任務「{task_content}」的提醒時間為 {reminder_time}"
                else:
                    reply_text = "❌ 找不到該未完成任務，請確認任務名稱"
            else:
                reply_text = "❌ 時間格式錯誤，請使用 HH:MM 格式（例如 08:30）"
    
    elif text == "查詢任務":
        tasks = get_tasks(completed=False)
        message = create_task_list_flex_message(tasks)
        line_bot_api.reply_message(event.reply_token, message)
        return
    
    elif text == "今日進度":
        completed, total, percentage = get_today_progress()
        reply_text = f"📊 今日任務進度：\n完成 {completed}/{total} 項任務\n完成率：{percentage:.1f}%"
    
    elif text == "反思":
        # 當使用者只輸入「反思」時，提供一個隨機反思問題
        current_hour = datetime.datetime.now().hour
        time_of_day = "morning" if 5 <= current_hour < 12 else "evening"
        question = get_random_question(time_of_day)
        
        if question:
            reply_text = f"📝 反思問題：\n\n{question}\n\n請回覆你的想法，或使用「反思：[內容]」格式記錄你的反思。"
        else:
            reply_text = "抱歉，無法獲取反思問題，請稍後再試。"

    elif text.startswith("反思：") or text.startswith("反思:"):
        # 處理使用者直接提供的反思內容
        answer = text[3:].strip()
        
        # 獲取適合當前時間的問題類型
        current_hour = datetime.datetime.now().hour
        time_of_day = "morning" if 5 <= current_hour < 12 else "evening"
        question = get_random_question(time_of_day)
        
        if save_reflection(question, answer):
            reply_text = "✨ 感謝分享你的反思，已記錄下來！"
        else:
            reply_text = "❌ 儲存反思失敗，請稍後再試"
    
    elif text.startswith("設定計畫：") or text.startswith("設定計畫:"):
        try:
            # 格式：設定計畫：{"早上":"晨間閱讀","中午":"午餐後散步","晚上":"復盤一天"}
            plan_str = text[5:].strip()
            plan_data = json.loads(plan_str)
            
            if set_daily_plan(plan_data):
                reply_text = "📅 每日計畫已更新！"
            else:
                reply_text = "❌ 更新計畫失敗，請稍後再試"
        except json.JSONDecodeError:
            reply_text = "❌ 計畫格式錯誤，請使用正確的 JSON 格式"
    
    elif text == "幫助" or text == "help":
        reply_text = (
            "📌 指令說明：\n"
            "• 新增：[任務內容] - 新增一項任務\n"
            "• 新增：[任務內容] @HH:MM - 新增帶提醒的任務\n"
            "• 完成：[任務內容] - 標記任務為已完成\n"
            "• 提醒：[任務內容]=HH:MM - 設置任務的提醒時間\n"
            "• 查詢任務 - 檢視所有未完成任務\n"
            "• 今日進度 - 查看今日任務完成率\n"
            "• 反思 - 獲取一個反思問題\n"
            "• 反思：[內容] - 記錄你的反思\n"
            "• 設定計畫：{JSON格式} - 設定每日計畫\n"
            "• 模板 - 獲取可複製的功能模板"
        )

    elif text == "模板":
        reply_text = (
            "📝 LINE Bot 功能模板集\n"
            "複製後修改 [參數] 即可使用\n\n"
            "==== 任務管理 ====\n"
            "新增：[任務內容]\n"
            "新增：[任務內容] @08:30\n"
            "完成：[任務內容]\n"
            "提醒：[任務內容]=08:30\n"
            "查詢任務\n"
            "今日進度\n\n"
            
            "==== 反思系統 ====\n"
            "反思\n"
            "反思：[反思內容]\n\n"
            
            "==== 計畫管理 ====\n"
            "設定計畫：{\"早上\":\"[活動]\",\"中午\":\"[活動]\",\"下午\":\"[活動]\",\"晚上\":\"[活動]\"}\n\n"
            
            "==== 簡化計畫 ====\n"
            "設定計畫：{\"[時間]\":\"[活動]\"}\n\n"
            
            "==== 其他功能 ====\n"
            "幫助\n"
        )
    
    else:
        # 將用戶的回覆視為對最近問題的回答
        data = load_data(REFLECTIONS_FILE)
        if data and data["reflections"]:
            last_reflection = data["reflections"][-1]
            question = last_reflection["question"]
            
            if save_reflection(question, text):
                reply_text = "✨ 感謝分享你的反思，已記錄下來！"
            else:
                reply_text = "❌ 儲存反思失敗，請稍後再試"
        else:
            reply_text = "🤔 我不確定你想做什麼，請嘗試輸入「幫助」查看可用指令"
    
    # 確保回覆訊息不為空
    if reply_text:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        
if __name__ == "__main__":
    # 初始化文件
    logger.info("正在初始化資料檔案...")
    init_files()
    
    # 啟動排程任務
    logger.info("正在啟動排程任務...")
    schedule_jobs()
    
    # 啟動保活線程
    logger.info("正在啟動保活線程...")
    start_keep_alive_thread()
    
    # 獲取 Render 指定的端口
    port = int(os.environ.get('PORT', 8080))
    
    # 確保正確綁定到指定端口，並打印日誌以便調試
    logger.info(f"正在啟動應用於端口 {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
