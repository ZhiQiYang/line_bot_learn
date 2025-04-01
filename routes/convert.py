import pytz
import re
import datetime
from datetime import datetime, timedelta
from flask import Blueprint
from linebot.models import TextSendMessage

# 創建藍圖
convert_bp = Blueprint('convert', __name__)

# 支持的時區代碼和名稱映射
TIMEZONE_ALIASES = {
    "tw": "Asia/Taipei",
    "taipei": "Asia/Taipei",
    "台北": "Asia/Taipei",
    "台灣": "Asia/Taipei",
    "taiwan": "Asia/Taipei",
    "jp": "Asia/Tokyo",
    "japan": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",
    "日本": "Asia/Tokyo",
    "東京": "Asia/Tokyo",
    "us": "America/New_York",
    "ny": "America/New_York",
    "nyc": "America/New_York",
    "紐約": "America/New_York",
    "美國": "America/New_York",
    "usa": "America/New_York",
    "la": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "洛杉磯": "America/Los_Angeles",
    "uk": "Europe/London",
    "london": "Europe/London",
    "倫敦": "Europe/London",
    "英國": "Europe/London",
    "eu": "Europe/Paris",
    "paris": "Europe/Paris",
    "巴黎": "Europe/Paris",
    "法國": "Europe/Paris",
    "france": "Europe/Paris",
    "cn": "Asia/Shanghai",
    "china": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "中國": "Asia/Shanghai",
    "sg": "Asia/Singapore",
    "singapore": "Asia/Singapore",
    "新加坡": "Asia/Singapore",
    "au": "Australia/Sydney",
    "sydney": "Australia/Sydney",
    "悉尼": "Australia/Sydney",
    "澳洲": "Australia/Sydney",
    "australia": "Australia/Sydney",
    "de": "Europe/Berlin",
    "germany": "Europe/Berlin",
    "berlin": "Europe/Berlin",
    "柏林": "Europe/Berlin",
    "德國": "Europe/Berlin",
    "utc": "UTC",
    "gmt": "UTC"
}

def get_timezone(zone_str):
    """根據輸入的字符串獲取時區對象"""
    zone_str = zone_str.lower().strip()
    
    # 檢查是否是別名
    if zone_str in TIMEZONE_ALIASES:
        timezone_str = TIMEZONE_ALIASES[zone_str]
    else:
        timezone_str = zone_str
    
    try:
        return pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        # 如果找不到時區，嘗試搜索相似的時區
        for name in pytz.all_timezones:
            if zone_str in name.lower():
                return pytz.timezone(name)
        
        # 如果還是找不到，返回UTC
        return pytz.UTC

def parse_time_str(time_str):
    """解析時間字符串，支持多種格式"""
    time_str = time_str.strip()
    
    # 嘗試解析時間格式
    formats = [
        "%H:%M",         # 14:30
        "%I:%M %p",      # 2:30 PM
        "%I:%M%p",       # 2:30PM
        "%I:%M",         # 2:30 (假設是24小時制)
        "%H:%M:%S",      # 14:30:00
        "%I:%M:%S %p",   # 2:30:00 PM
        "%Y-%m-%d %H:%M" # 2023-06-10 14:30
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            # 如果解析成功，使用今天的日期
            now = datetime.now()
            return datetime(now.year, now.month, now.day, dt.hour, dt.minute, dt.second)
        except ValueError:
            continue
    
    # 如果所有格式都失敗，嘗試使用正則表達式解析
    hour_minute_pattern = r"(\d{1,2})[:：時](\d{1,2})(?:分|)(?:\s*(上午|下午|am|pm|AM|PM)|)"
    match = re.search(hour_minute_pattern, time_str)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        am_pm = match.group(3).lower() if match.group(3) else None
        
        # 處理上午/下午/AM/PM
        if am_pm in ["下午", "pm"]:
            if hour < 12:
                hour += 12
        elif am_pm in ["上午", "am"]:
            if hour == 12:
                hour = 0
                
        now = datetime.now()
        return datetime(now.year, now.month, now.day, hour, minute, 0)
    
    # 如果還是無法解析，返回None
    return None

def handle_timezone_conversion(text):
    """處理時區轉換命令"""
    # 命令格式例如: "#時區轉換 14:30 台北 to 紐約"
    pattern = r"#時區轉換\s+(.+?)\s+(.+?)\s+(?:to|到|轉換到|轉換為)\s+(.+)"
    match = re.search(pattern, text)
    
    if not match:
        return "🕒 時區轉換格式不正確\n正確格式：#時區轉換 [時間] [原時區] to [目標時區]\n例如：#時區轉換 14:30 台北 to 紐約"
    
    time_str = match.group(1)
    source_zone_str = match.group(2)
    target_zone_str = match.group(3)
    
    # 解析時間
    dt = parse_time_str(time_str)
    if not dt:
        return f"❌ 無法解析時間: {time_str}\n請使用格式如 14:30 或 2:30 PM"
    
    # 獲取時區
    source_tz = get_timezone(source_zone_str)
    target_tz = get_timezone(target_zone_str)
    
    # 設置源時區
    source_time = source_tz.localize(dt)
    
    # 轉換到目標時區
    target_time = source_time.astimezone(target_tz)
    
    # 格式化輸出
    source_time_str = source_time.strftime("%Y-%m-%d %H:%M")
    target_time_str = target_time.strftime("%Y-%m-%d %H:%M")
    
    result = (
        f"🌐 時區轉換結果：\n\n"
        f"🕒 {source_zone_str} ({source_tz}): {source_time_str}\n"
        f"🕒 {target_zone_str} ({target_tz}): {target_time_str}\n\n"
        f"時差: {_get_timezone_diff(source_tz, target_tz)}"
    )
    
    return result

def _get_timezone_diff(tz1, tz2):
    """計算兩個時區的時差"""
    now = datetime.now(pytz.UTC)
    tz1_offset = now.astimezone(tz1).utcoffset().total_seconds() / 3600
    tz2_offset = now.astimezone(tz2).utcoffset().total_seconds() / 3600
    diff = tz2_offset - tz1_offset
    
    if diff == 0:
        return "相同時區"
    elif diff > 0:
        return f"+{diff:.1f} 小時"
    else:
        return f"{diff:.1f} 小時"

def handle_convert_command(text):
    """處理所有轉換相關的命令"""
    if text.startswith("#時區轉換"):
        return handle_timezone_conversion(text)
    return None 