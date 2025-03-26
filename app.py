import os
import json
import time
import random
import datetime
import threading
import logging
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
ensure_file_exists(TASKS_FILE, {"tasks": [], "daily_plan": {}})
ensure_file_exists(REFLECTIONS_FILE, {"reflections": []})
ensure_file_exists(QUESTIONS_FILE, {
    "morning": [
        "今天你最重要的一件事是什麼？",
        "你希望今天結束時能完成什麼？",
        "今天有什麼可能讓你分心的事情？你要如何應對？",
        "你今天最期待什麼事情？",
        "如果今天只能完成一件事，你會選擇做什麼？"
    ],
    "evening": [
        "今天你完成了什麼有意義的事？",
        "你今天遇到最大的阻力是什麼？",
        "今天有什麼事情讓你感到開心或有成就感？",
        "明天你想要改進什麼？",
        "今天你學到了什麼？"
    ]
})

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

# 處理新增任務
def add_task(task_content):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    # 建立新任務
    new_task = {
        "id": len(data["tasks"]) + 1,
        "content": task_content,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed": False,
        "completed_at": None
    }
    
    data["tasks"].append(new_task)
    return save_data(TASKS_FILE, data)

# 獲取任務列表
def get_tasks(completed=None):
    data = load_data(TASKS_FILE)
    if not data:
        return []
    
    if completed is None:  # 返回所有任務
        return data["tasks"]
    else:  # 根據完成狀態過濾
        return [task for task in data["tasks"] if task["completed"] == completed]

# 標記任務為已完成
def complete_task(task_content):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    for task in data["tasks"]:
        if task["content"] == task_content and not task["completed"]:
            task["completed"] = True
            task["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return save_data(TASKS_FILE, data)
    
    return False

# 獲取今日任務完成率
def get_today_progress():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    data = load_data(TASKS_FILE)
    if not data:
        return 0, 0, 0
    
    # 篩選今天創建的任務
    today_tasks = [task for task in data["tasks"] 
                  if task["created_at"].startswith(today)]
    
    total = len(today_tasks)
    completed = sum(1 for task in today_tasks if task["completed"])
    
    if total == 0:
        return 0, 0, 0
    
    return completed, total, (completed / total) * 100

# 儲存反思內容
def save_reflection(question, answer):
    data = load_data(REFLECTIONS_FILE)
    if not data:
        return False
    
    new_reflection = {
        "id": len(data["reflections"]) + 1,
        "question": question,
        "answer": answer,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data["reflections"].append(new_reflection)
    return save_data(REFLECTIONS_FILE, data)

# 獲取隨機問題
def get_random_question(time_of_day):
    data = load_data(QUESTIONS_FILE)
    if not data or time_of_day not in data or not data[time_of_day]:
        return None
    
    return random.choice(data[time_of_day])

# 設定每日計畫
def set_daily_plan(plan_data):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    data["daily_plan"] = plan_data
    return save_data(TASKS_FILE, data)

# 獲取每日計畫
def get_daily_plan():
    data = load_data(TASKS_FILE)
    if not data or "daily_plan" not in data:
        return {}
    
    return data["daily_plan"]

# 傳送 LINE 訊息
def send_line_message(user_id, message):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
        return True
    except Exception as e:
        logger.error(f"傳送訊息時發生錯誤: {e}")
        return False

# 傳送每日計畫提醒
def send_plan_reminder(user_id, time_slot):
    plan = get_daily_plan()
    if not plan or time_slot not in plan:
        return False
    
    task = plan[time_slot]
    message = f"⏰ 提醒：現在是{time_slot}，該執行「{task}」了"
    return send_line_message(user_id, message)

# 傳送思考問題
def send_thinking_question(user_id, time_of_day):
    question = get_random_question(time_of_day)
    if not question:
        return False
    
    if time_of_day == "morning":
        prefix = "🌞 早安！今天的思考問題："
    else:
        prefix = "🌙 晚安！今天的反思問題："
    
    message = f"{prefix}\n\n{question}"
    return send_line_message(user_id, message)

# 根據任務列表產生美觀的 Flex 訊息
def create_task_list_flex_message(tasks):
    if not tasks:
        return TextSendMessage(text="目前沒有任何任務")
    
    contents = []
    
    # 標題
    contents.append(TextComponent(
        text="📋 任務清單",
        weight="bold",
        size="xl",
        margin="md"
    ))
    
    # 分隔線
    contents.append(SeparatorComponent(margin="xxl"))
    
    # 任務列表
    for i, task in enumerate(tasks):
        status = "✅" if task["completed"] else "⬜"
        contents.append(BoxComponent(
            layout="horizontal",
            margin="md",
            contents=[
                TextComponent(
                    text=f"{status} {task['content']}",
                    size="md",
                    color="#555555",
                    flex=5
                )
            ]
        ))
        
        if i < len(tasks) - 1:
            contents.append(SeparatorComponent(margin="sm"))
    
    bubble = BubbleContainer(
        direction='ltr',
        body=BoxComponent(
            layout='vertical',
            contents=contents
        )
    )
    
    return FlexSendMessage(alt_text="任務清單", contents=bubble)

# 健康檢查路由
@app.route("/", methods=['GET'])
def health_check():
    return "LINE Bot is running!", 200

# Flask 路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    
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
        task_content = text[3:].strip()
        if add_task(task_content):
            reply_text = f"✅ 已新增任務：{task_content}"
        else:
            reply_text = "❌ 新增任務失敗，請稍後再試"
    
    elif text.startswith("完成：") or text.startswith("完成:"):
        task_content = text[3:].strip()
        if complete_task(task_content):
            reply_text = f"🎉 恭喜完成任務：{task_content}"
        else:
            reply_text = "❌ 找不到該未完成任務，請確認任務名稱"
    
    elif text == "查詢任務":
        tasks = get_tasks(completed=False)
        message = create_task_list_flex_message(tasks)
        line_bot_api.reply_message(event.reply_token, message)
        return
    
    elif text == "今日進度":
        completed, total, percentage = get_today_progress()
        reply_text = f"📊 今日任務進度：\n完成 {completed}/{total} 項任務\n完成率：{percentage:.1f}%"
    
    elif text.startswith("反思：") or text.startswith("反思:"):
        # 假設這是對早上或晚上問題的回答
        answer = text[3:].strip()
        
        # 這裡我們暫時不知道問題是什麼，所以使用時間來猜測
        current_hour = datetime.datetime.now().hour
        time_of_day = "morning" if 5 <= current_hour < 12 else "evening"
        question = get_random_question(time_of_day)  # 這只是一個佔位符
        
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
            "• 完成：[任務內容] - 標記任務為已完成\n"
            "• 查詢任務 - 檢視所有未完成任務\n"
            "• 今日進度 - 查看今日任務完成率\n"
            "• 反思：[內容] - 記錄你的反思\n"
            "• 設定計畫：{JSON格式} - 設定每日計畫"
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
                reply_text = ""

line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
