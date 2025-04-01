import os
import json
import time
import random
import datetime
import threading
import logging
import requests
import re
import pytz
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    URIAction, MessageAction, RichMenu, RichMenuArea, RichMenuBounds, PostbackAction
)
import schedule
from PIL import Image, ImageDraw, ImageFont

# 設置台灣時區環境變數，確保所有時間處理使用相同時區
os.environ['TZ'] = 'Asia/Taipei'
time.tzset() if hasattr(time, 'tzset') else None  # Windows 可能沒有 tzset 函數

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 設置台灣時區
TIMEZONE = pytz.timezone('Asia/Taipei')

# 初始化 Flask
app = Flask(__name__)

# 從環境變數獲取配置
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
USER_ID = os.environ.get('USER_ID')  # 要發送訊息的使用者 ID

# 確保關鍵環境變數存在
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.warning("LINE API 密鑰未設置，機器人功能將受限")

# 初始化 LINE Bot API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN) if LINE_CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(LINE_CHANNEL_SECRET) if LINE_CHANNEL_SECRET else None

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

# 添加任務
def add_task(task_content, reminder_time=None):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    now = datetime.datetime.now(TIMEZONE)
    
    # 創建新任務
    new_task = {
        "content": task_content,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "completed": False,
        "completed_at": None,
        "reminder_time": reminder_time,
        "last_reminded_at": None,
        "progress": 0
    }
    
    # 添加到任務列表
    data["tasks"].append(new_task)
    
    # 保存更新後的數據
    return save_data(TASKS_FILE, data)

# 獲取任務列表
def get_tasks(completed=None):
    data = load_data(TASKS_FILE)
    if not data:
        return []
    
    tasks = []
    for task in data["tasks"]:
        if completed is None or task["completed"] == completed:
            tasks.append(task)
    
    # 按創建時間排序，最新的排在前面
    return sorted(tasks, key=lambda x: x["created_at"], reverse=True)

# 標記任務為已完成
def complete_task(task_content):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    for task in data["tasks"]:
        if task["content"] == task_content and not task["completed"]:
            task["completed"] = True
            task["completed_at"] = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            return save_data(TASKS_FILE, data)
    
    return False

# 獲取今日任務完成率
def get_today_progress():
    data = load_data(TASKS_FILE)
    if not data:
        return 0, 0, 0
    
    today = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    total = 0
    completed = 0
    
    for task in data["tasks"]:
        task_date = task["created_at"].split()[0]  # 只取日期部分
        if task_date == today:
            total += 1
            if task["completed"]:
                completed += 1
    
    percentage = (completed / total * 100) if total > 0 else 0
    return completed, total, percentage

# 儲存反思內容
def save_reflection(question, answer):
    data = load_data(REFLECTIONS_FILE)
    if not data:
        return False
    
    # 創建新反思
    new_reflection = {
        "question": question,
        "answer": answer,
        "created_at": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 添加到反思列表
    data["reflections"].append(new_reflection)
    
    # 保存更新後的數據
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
    
    # 更新每日計畫
    data["daily_plan"] = plan_data
    
    # 保存更新後的數據
    return save_data(TASKS_FILE, data)

# 獲取每日計畫
def get_daily_plan():
    data = load_data(TASKS_FILE)
    if not data:
        return {}
    
    return data.get("daily_plan", {})

# 設置任務提醒
def set_task_reminder(task_content, reminder_time):
    data = load_data(TASKS_FILE)
    if not data:
        return False
    
    for task in data["tasks"]:
        if task["content"] == task_content and not task["completed"]:
            task["reminder_time"] = reminder_time
            return save_data(TASKS_FILE, data)
    
    return False

# 發送LINE訊息
def send_line_message(user_id, message):
    if not line_bot_api:
        logger.error("LINE Bot API 未初始化，無法發送訊息")
        return False
    
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
        return True
    except Exception as e:
        logger.error(f"發送訊息失敗: {e}")
        return False

# 創建任務列表 Flex 訊息
def create_task_list_flex_message(tasks):
    if not tasks:
        return TextSendMessage(text="📝 目前沒有未完成的任務")
    
    # 創建 Flex 訊息格式
    bubble = BubbleContainer(
        header=BoxComponent(
            layout="vertical",
            contents=[
                TextComponent(text="未完成任務列表", weight="bold", size="xl")
            ]
        ),
        body=BoxComponent(
            layout="vertical",
            contents=[]
        )
    )
    
    # 添加每個任務
    for i, task in enumerate(tasks):
        if i > 0:
            # 添加分隔線
            bubble.body.contents.append(SeparatorComponent())
        
        # 任務內容組件
        task_box = BoxComponent(
            layout="vertical",
            margin="md",
            contents=[
                TextComponent(
                    text=task["content"], 
                    size="md", 
                    wrap=True
                )
            ]
        )
        
        # 如果有提醒時間，添加顯示
        if task.get("reminder_time"):
            task_box.contents.append(
                TextComponent(
                    text=f"⏰ {task['reminder_time']}", 
                    size="sm", 
                    color="#888888"
                )
            )
        
        # 添加創建時間
        created_date = task["created_at"].split()[0]  # 只取日期部分
        task_box.contents.append(
            TextComponent(
                text=f"創建於: {created_date}", 
                size="xs", 
                color="#aaaaaa"
            )
        )
        
        # 添加操作按鈕
        actions_box = BoxComponent(
            layout="horizontal",
            margin="md",
            contents=[
                ButtonComponent(
                    action=MessageAction(
                        label="標記完成",
                        text=f"完成：{task['content']}"
                    ),
                    style="primary",
                    height="sm"
                ),
                ButtonComponent(
                    action=MessageAction(
                        label="設置提醒",
                        text=f"提醒：{task['content']}="
                    ),
                    style="secondary",
                    margin="md",
                    height="sm"
                )
            ]
        )
        
        task_box.contents.append(actions_box)
        bubble.body.contents.append(task_box)
    
    # 創建 Flex 訊息
    return FlexSendMessage(
        alt_text="未完成任務列表",
        contents=bubble
    )

# 發送思考問題
def send_thinking_question(user_id, time_of_day):
    question = get_random_question(time_of_day)
    if not question:
        logger.error(f"無法獲取 {time_of_day} 反思問題")
        return
    
    time_label = "早晨" if time_of_day == "morning" else "晚間"
    message = f"📝 {time_label}反思問題：\n\n{question}\n\n請回覆你的想法。"
    send_line_message(user_id, message)

# 發送任務提醒
def send_task_reminder():
    now = datetime.datetime.now(TIMEZONE)
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

# 排程任務
def schedule_jobs():
    # 早晚定時發送問題 (使用台灣時區，而非UTC時區)
    schedule.every().day.at("07:00").do(lambda: send_thinking_question(USER_ID, "morning"))
    schedule.every().day.at("21:00").do(lambda: send_thinking_question(USER_ID, "evening"))
    
    # 每分鐘檢查任務提醒
    schedule.every(1).minutes.do(send_task_reminder)
    
    # 執行排程任務的線程
    def run_scheduler():
        while True:
            # 計算下一次運行的作業
            schedule.run_pending()
            time.sleep(1)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("排程任務已啟動")

# 初始化資料庫（在這個版本中實際上是初始化檔案）
def init_db():
    init_files()
    logger.info("資料初始化完成")

# 新增測試路由
@app.route("/ping", methods=['GET'])
def ping():
    return "pong!", 200

# 健康檢查路由
@app.route("/", methods=['GET'])
def health_check():
    return "LINE Bot is running!", 200

# 時區檢查路由
@app.route("/timezone", methods=['GET'])
def timezone_check():
    now_utc = datetime.datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
    now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    now_taipei = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")
    
    return f"UTC時間: {now_utc}\n系統時間: {now_local}\n台灣時間: {now_taipei}", 200

# Flask 路由
@app.route("/callback", methods=['POST'])
def callback():
    if not handler:
        abort(500)
    
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
        current_hour = datetime.datetime.now(TIMEZONE).hour
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
        current_hour = datetime.datetime.now(TIMEZONE).hour
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

# 創建Rich Menu
def create_rich_menu():
    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name="任務管理選單",
        chat_bar_text="點擊查看選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=MessageAction(label="新增任務", text="新增任務表單")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                action=MessageAction(label="查詢任務", text="查詢任務")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=0, width=833, height=843),
                action=MessageAction(label="今日進度", text="今日進度")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                action=MessageAction(label="反思", text="反思")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=843, width=833, height=843),
                action=MessageAction(label="設定計畫", text="設定計畫表單")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=843, width=833, height=843),
                action=MessageAction(label="幫助", text="幫助")
            )
        ]
    )
    
    # 創建Rich Menu
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
    
    # 上傳Rich Menu圖片
    with open("rich_menu.png", "rb") as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
    
    # 設置為默認菜單
    line_bot_api.set_default_rich_menu(rich_menu_id)
    
    return rich_menu_id

# 測試Rich Menu創建
@app.route("/test_rich_menu", methods=['GET'])
def test_rich_menu():
    try:
        create_rich_menu_image()
        
        # 創建Rich Menu
        rich_menu_id = create_rich_menu()
        return f"Rich Menu創建成功，ID: {rich_menu_id}", 200
    except Exception as e:
        return f"創建Rich Menu時發生錯誤: {str(e)}", 500

if __name__ == "__main__":
    # 初始化資料庫（文件）
    logger.info("正在初始化資料...")
    init_db()
    
    # 啟動排程任務
    logger.info("正在啟動排程任務...")
    schedule_jobs()
    
    # 啟動保活線程
    logger.info("正在啟動保活線程...")
    start_keep_alive_thread()
    
    # 創建Rich Menu
    try:
        rich_menu_id = create_rich_menu()
        logger.info(f"Rich Menu 創建成功: {rich_menu_id}")
    except Exception as e:
        logger.error(f"Rich Menu 創建失敗: {e}")
    
    # 獲取 Render 指定的端口
    port = int(os.environ.get('PORT', 8080))
    
    # 確保正確綁定到指定端口，並打印日誌以便調試
    logger.info(f"正在啟動應用於端口 {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
