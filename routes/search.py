import re
import logging
import requests
from flask import Blueprint
from linebot.models import TextSendMessage

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建藍圖
search_bp = Blueprint('search', __name__)

# 定義搜索源
SEARCH_SOURCES = {
    "wikipedia": {
        "name": "維基百科",
        "icon": "📚",
        "api_url": "https://zh.wikipedia.org/w/api.php",
        "params": {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "redirects": 1
        }
    },
    "dictionary": {
        "name": "字典",
        "icon": "📖",
        "api_url": "https://www.moedict.tw/uni/",
        "extract_func": lambda data: extract_moedict_definition(data)
    }
}

def extract_moedict_definition(data):
    """從萌典API返回的數據中提取定義"""
    if not data or not isinstance(data, dict):
        return None
    
    definitions = []
    
    # 檢查是否有heteronyms字段
    if "heteronyms" in data and isinstance(data["heteronyms"], list):
        for h in data["heteronyms"]:
            if "definitions" in h and isinstance(h["definitions"], list):
                for d in h["definitions"]:
                    definition = d.get("def", "")
                    if definition:
                        # 添加例句如果有
                        if "example" in d and isinstance(d["example"], list):
                            examples = d["example"]
                            if examples:
                                definition += "\n例：" + "；".join(examples)
                        
                        definitions.append(definition)
    
    if definitions:
        return "\n\n".join(definitions)
    return None

def search_wikipedia(query, lang="zh"):
    """使用Wikipedia API搜索關鍵詞"""
    source = SEARCH_SOURCES["wikipedia"]
    api_url = source["api_url"]
    params = source["params"].copy()
    
    # 添加查詢詞
    params["titles"] = query
    
    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # 提取頁面內容
        pages = data["query"]["pages"]
        for page_id in pages:
            page = pages[page_id]
            
            # 檢查是否找到內容
            if "extract" in page and page["extract"]:
                # 摘要可能很長，僅返回前200個字符，並確保完整句子
                extract = page["extract"]
                if len(extract) > 200:
                    sentences = re.split(r'[。！？.!?]', extract)
                    short_extract = ""
                    for sentence in sentences:
                        if len(short_extract + sentence) < 200:
                            short_extract += sentence + "。"
                        else:
                            break
                    extract = short_extract
                
                return {
                    "title": page.get("title", query),
                    "extract": extract,
                    "url": f"https://zh.wikipedia.org/wiki/{page.get('title', query).replace(' ', '_')}"
                }
            elif "missing" in page:
                return None
        
        return None
    except Exception as e:
        logger.error(f"維基百科搜索錯誤: {e}")
        return None

def search_moedict(query):
    """使用萌典API搜尋中文詞彙定義"""
    source = SEARCH_SOURCES["dictionary"]
    api_url = source["api_url"] + query
    
    try:
        response = requests.get(api_url)
        
        # 檢查是否成功
        if response.status_code == 200:
            data = response.json()
            
            # 使用提取函數獲取定義
            definition = source["extract_func"](data)
            
            if definition:
                return {
                    "title": query,
                    "extract": definition,
                    "url": f"https://www.moedict.tw/#{query}"
                }
        
        return None
    except Exception as e:
        logger.error(f"萌典搜索錯誤: {e}")
        return None

def handle_search_command(text):
    """處理搜索命令"""
    # 檢查是否是搜索命令
    if not text.startswith("#搜尋") and not text.startswith("#搜索"):
        return None
    
    # 提取搜索關鍵詞
    match = re.match(r"#(?:搜尋|搜索)\s+(.+)", text)
    if not match:
        return "🔍 請提供要搜尋的關鍵詞，例如: #搜尋 量子力學"
    
    keyword = match.group(1).strip()
    if not keyword:
        return "🔍 請提供要搜尋的關鍵詞，例如: #搜尋 量子力學"
    
    # 先嘗試用萌典搜索（如果是中文詞彙）
    if any('\u4e00' <= char <= '\u9fff' for char in keyword):
        result = search_moedict(keyword)
        if result:
            return format_search_result(result, "dictionary")
    
    # 然後嘗試用維基百科搜索
    result = search_wikipedia(keyword)
    if result:
        return format_search_result(result, "wikipedia")
    
    # 如果都沒找到結果
    return f"🔍 抱歉，找不到關於「{keyword}」的資訊。"

def format_search_result(result, source_key):
    """格式化搜索結果為易讀的消息"""
    source = SEARCH_SOURCES[source_key]
    
    formatted_result = (
        f"{source['icon']} {source['name']}：{result['title']}\n\n"
        f"{result['extract']}\n\n"
        f"📎 詳細資訊: {result['url']}"
    )
    
    return formatted_result 