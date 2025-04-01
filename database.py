import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import pytz

logger = logging.getLogger(__name__)

# 設置台灣時區
TIMEZONE = pytz.timezone('Asia/Taipei')

# 獲取資料庫連接 URL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """建立並返回資料庫連接"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        # 設置資料庫連接的時區為台灣時區
        cursor = conn.cursor()
        cursor.execute("SET timezone TO 'Asia/Taipei'")
        conn.commit()
        return conn
    except Exception as e:
        logger.error(f"資料庫連接錯誤: {e}")
        return None

def init_db():
    """初始化資料庫表結構"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 創建任務表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            completed_at TIMESTAMP,
            progress INTEGER NOT NULL DEFAULT 0,
            reminder_time VARCHAR(5),
            last_reminded_at TIMESTAMP
        )
        ''')
        
        # 創建反思表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reflections (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 創建問題表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            time_of_day VARCHAR(20) NOT NULL,
            content TEXT NOT NULL
        )
        ''')
        
        # 創建計畫表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_plans (
            id SERIAL PRIMARY KEY,
            time_slot VARCHAR(30) NOT NULL,
            content TEXT NOT NULL
        )
        ''')
        
        # 初始化問題數據
        cursor.execute("SELECT COUNT(*) FROM questions")
        question_count = cursor.fetchone()['count']
        
        if question_count == 0:
            # 添加晨間問題
            morning_questions = [
                "今天你最重要的一件事是什麼？",
                "你希望今天結束時能完成什麼？",
                "今天有什麼可能讓你分心的事情？你要如何應對？",
                "你今天最期待什麼事情？",
                "如果今天只能完成一件事，你會選擇做什麼？",
                "今天你想要專注發展哪方面的能力？",
                "有什麼小習慣是你今天想要堅持的？"
            ]
            
            for q in morning_questions:
                cursor.execute(
                    "INSERT INTO questions (time_of_day, content) VALUES (%s, %s)",
                    ("morning", q)
                )
            
            # 添加晚間問題
            evening_questions = [
                "今天你完成了什麼有意義的事？",
                "你今天遇到最大的阻力是什麼？",
                "今天有什麼事情讓你感到開心或有成就感？",
                "明天你想要改進什麼？",
                "今天你學到了什麼？",
                "今天你最感恩的一件事是什麼？",
                "今天有哪個決定你覺得做得特別好？"
            ]
            
            for q in evening_questions:
                cursor.execute(
                    "INSERT INTO questions (time_of_day, content) VALUES (%s, %s)",
                    ("evening", q)
                )
            
            # 添加深度反思問題
            deep_questions = [
                "在過去的一個月中，你注意到自己有什麼成長或改變？",
                "目前有什麼事情正在阻礙你實現目標？你可以如何突破？",
                "如果回顧你人生中最有意義的幾個決定，有什麼共同點？",
                "你最近感到壓力的根源是什麼？有哪些方法可以幫助你減輕它？",
                "如果可以給一年前的自己一個建議，你會說什麼？"
            ]
            
            for q in deep_questions:
                cursor.execute(
                    "INSERT INTO questions (time_of_day, content) VALUES (%s, %s)",
                    ("deep", q)
                )
        
        conn.commit()
        logger.info("資料庫初始化完成")
        return True
    
    except Exception as e:
        conn.rollback()
        logger.error(f"初始化資料庫時發生錯誤: {e}")
        return False
    
    finally:
        conn.close()
