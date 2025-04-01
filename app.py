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
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    URIAction, MessageAction, RichMenu, RichMenuArea, RichMenuBounds, PostbackAction,
    RichMenuSize
)
import schedule
from PIL import Image, ImageDraw, ImageFont
from routes import task, convert, search, map
from routes.materials import materials_bp, handle_materials_command
from utils.rich_menu import preview_rich_menu, preview_gold_rich_menu, create_and_apply_rich_menu, create_and_apply_gold_rich_menu, delete_all_rich_menus

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

# 添加靜態資源路由
app.static_folder = 'resources'
app.static_url_path = '/resources'

# 註冊藍圖
app.register_blueprint(materials_bp)

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
    return "Learning LINE Bot is running!", 200

# 時區檢查路由
@app.route("/timezone", methods=['GET'])
def timezone_check():
    now = datetime.datetime.now(TIMEZONE)
    return f"當前時間: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}", 200

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
    
    # 將文本消息轉發到統一路由處理器
    process_message(line_bot_api, text, user_id, event.reply_token)

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

# 確保Rich Menu圖片存在
def ensure_rich_menu_image_exists():
    if not os.path.exists("rich_menu.png"):
        logger.info("正在創建Rich Menu圖片...")
        return create_rich_menu_image()
    return "rich_menu.png"

# 創建Rich Menu圖片
def create_rich_menu_image():
    """創建2500x1686的Rich Menu圖片"""
    try:
        # 創建2500x1686的圖片（標準Rich Menu尺寸）
        img = Image.new('RGB', (2500, 1686), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 繪製網格線和區域
        # 水平分隔線
        draw.line([(0, 843), (2500, 843)], fill=(200, 200, 200), width=5)
        
        # 垂直分隔線
        draw.line([(833, 0), (833, 1686)], fill=(200, 200, 200), width=5)
        draw.line([(1666, 0), (1666, 1686)], fill=(200, 200, 200), width=5)
        
        # 嘗試加載字體
        try:
            font = ImageFont.truetype("Arial.ttf", 60)
        except IOError:
            font = ImageFont.load_default()
        
        # 添加文字
        menu_items = [
            ("新增任務", 416, 421), 
            ("查詢任務", 1249, 421),
            ("今日進度", 2082, 421),
            ("反思", 416, 1264),
            ("設定計畫", 1249, 1264),
            ("幫助", 2082, 1264)
        ]
        
        for text, x, y in menu_items:
            # 計算文字寬度以居中顯示
            if hasattr(draw, 'textlength'):
                text_width = draw.textlength(text, font=font)
            else:  # 對於舊版PIL
                text_width = font.getsize(text)[0]
            
            draw.text((x - text_width // 2, y), text, fill=(50, 50, 50), font=font)
        
        # 保存圖片
        img.save("rich_menu.png")
        logger.info("Rich Menu圖片創建成功")
        return "rich_menu.png"
    except Exception as e:
        logger.error(f"創建Rich Menu圖片時發生錯誤: {e}")
        return None

# 路由處理函數 - 臨時實現
def process_message(line_bot_api, text, user_id, reply_token):
    # 嘗試處理學習材料相關命令
    materials_response = handle_materials_command(text)
    if materials_response:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=materials_response))
        return

    # 根據消息前綴決定使用哪個模組處理
    if text.startswith("熱力學地圖") or text.startswith("記憶術地圖"):
        reply_text = "主題地圖功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("#今天任務") or text.startswith("#打卡"):
        reply_text = "任務與打卡功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("#挑戰"):
        reply_text = "知識挑戰功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("#AI"):
        reply_text = "AI助手功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("#開始專注") or text.startswith("#專注"):
        reply_text = "專注模式功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("#呼叫"):
        reply_text = "角色助理功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("/export-report") or text.startswith("#報告"):
        reply_text = "學習報告功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    elif text.startswith("#新增卡") or text.startswith("#卡片"):
        reply_text = "記憶卡片功能即將推出！"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))
    
    else:
        # 通用命令處理
        handle_general_command(line_bot_api, text, user_id, reply_token)

def handle_general_command(line_bot_api, text, user_id, reply_token):
    """處理通用命令，如幫助、設置等"""
    from linebot.models import TextSendMessage
    
    HELP_TEXT = (
        "📚 學習助手指令：\n\n"
        "ℹ️ 功能說明:\n #幫助、#help\n\n"
        "🔄 時區轉換:\n #時區轉換 [時間] [原時區] to [目標時區]\n\n"
        "🔍 搜尋解釋:\n #搜尋 [關鍵詞]\n\n"
        "🗺️ 主題地圖:\n 熱力學地圖、記憶術地圖\n\n"
        "✅ 任務管理:\n #今天任務、#打卡 [內容] [時間]分鐘\n\n"
        "🔍 知識挑戰:\n #挑戰 [主題]\n\n"
        "🤖 AI協助:\n #AI [問題]\n\n"
        "⏱️ 專注模式:\n #開始專注、#專注 [主題] [時間]分鐘\n\n"
        "📊 學習分析:\n #報告 [日/週/月]\n\n"
        "🏆 設定目標:\n #目標 [描述] [日期]\n\n"
        "📚 學習材料:\n #材料、#材料 [主題]、#推薦材料\n\n"
    )
    
    if text.lower() in ["help", "幫助", "#help", "#幫助"]:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=HELP_TEXT))
    else:
        reply_text = "🤔 我不確定你想做什麼，請輸入「#幫助」查看可用指令"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_text))

# LIFF頁面路由
@app.route('/liff')
def liff_page():
    return render_template('liff.html')

# Rich Menu預覽和管理路由
@app.route('/admin/rich-menu/preview')
def rich_menu_preview():
    preview_path = preview_rich_menu()
    gold_preview_path = preview_gold_rich_menu()
    return render_template('rich_menu_preview.html', 
                           minimal_preview=preview_path, 
                           gold_preview=gold_preview_path)

@app.route('/admin/rich-menu/apply-minimal', methods=['POST'])
def apply_minimal_rich_menu():
    result = create_and_apply_rich_menu()
    return result

@app.route('/admin/rich-menu/apply-gold', methods=['POST'])
def apply_gold_rich_menu():
    result = create_and_apply_gold_rich_menu()
    return result

@app.route('/admin/rich-menu/delete-all', methods=['POST'])
def remove_all_rich_menus():
    result = delete_all_rich_menus()
    return result

if __name__ == "__main__":
    # 初始化資料庫（文件）
    logger.info("正在初始化資料...")
    init_db()
    
    # 確保Rich Menu圖片存在
    logger.info("確認Rich Menu圖片...")
    rich_menu_image = ensure_rich_menu_image_exists()
    if not rich_menu_image:
        logger.warning("無法創建Rich Menu圖片，Rich Menu功能可能不可用")
    
    # 啟動排程任務
    logger.info("正在啟動排程任務...")
    schedule_jobs()
    
    # 啟動保活線程
    logger.info("正在啟動保活線程...")
    start_keep_alive_thread()
    
    # 創建Rich Menu
    try:
        if rich_menu_image:
            rich_menu_id = create_rich_menu()
            logger.info(f"Rich Menu 創建成功: {rich_menu_id}")
    except Exception as e:
        logger.error(f"Rich Menu 創建失敗: {e}")
    
    # 獲取 Render 指定的端口
    port = int(os.environ.get('PORT', 8080))
    
    # 確保正確綁定到指定端口，並打印日誌以便調試
    logger.info(f"正在啟動應用於端口 {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
