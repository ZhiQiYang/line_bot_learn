import os
import json
import pandas as pd
import logging
from flask import jsonify, Blueprint

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建藍圖
materials_bp = Blueprint('materials', __name__)

# 學習材料文件路徑
MATERIALS_FILE = 'learning_materials.xlsx'
MATERIALS_CACHE_FILE = 'materials_cache.json'

# 材料類型與對應的圖標
MATERIAL_ICONS = {
    "文章": "fa-file-text",
    "視頻": "fa-video",
    "書籍": "fa-book",
    "練習": "fa-pencil-alt",
    "課程": "fa-graduation-cap",
    "筆記": "fa-sticky-note",
    "測驗": "fa-check-square",
    "項目": "fa-project-diagram"
}

def load_materials_from_excel():
    """從Excel讀取學習材料數據"""
    try:
        # 檢查是否存在快取文件
        if os.path.exists(MATERIALS_CACHE_FILE):
            # 檢查Excel文件是否比快取更新
            excel_time = os.path.getmtime(MATERIALS_FILE)
            cache_time = os.path.getmtime(MATERIALS_CACHE_FILE)
            
            # 如果快取比Excel更新或相同，直接使用快取
            if cache_time >= excel_time:
                with open(MATERIALS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        # 讀取Excel文件
        df = pd.read_excel(MATERIALS_FILE)
        
        # 將DataFrame轉換為字典列表
        materials = []
        for _, row in df.iterrows():
            material = {col: row[col] for col in df.columns}
            # 確保數值是JSON可序列化的
            for key, value in material.items():
                if pd.isna(value):
                    material[key] = None
                elif isinstance(value, pd.Timestamp):
                    material[key] = value.strftime('%Y-%m-%d')
            materials.append(material)
        
        # 按主題分組材料
        materials_by_topic = {}
        for material in materials:
            topic = material.get('主題', '未分類')
            if topic not in materials_by_topic:
                materials_by_topic[topic] = []
            materials_by_topic[topic].append(material)
        
        # 保存到快取文件
        with open(MATERIALS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(materials_by_topic, f, ensure_ascii=False, indent=2)
        
        return materials_by_topic
    
    except Exception as e:
        logger.error(f"讀取學習材料時出錯: {e}")
        return {}

@materials_bp.route('/api/materials', methods=['GET'])
def get_materials():
    """獲取所有學習材料"""
    materials = load_materials_from_excel()
    return jsonify(materials)

@materials_bp.route('/api/materials/topics', methods=['GET'])
def get_topics():
    """獲取所有主題"""
    materials = load_materials_from_excel()
    topics = list(materials.keys())
    return jsonify(topics)

@materials_bp.route('/api/materials/topic/<topic>', methods=['GET'])
def get_materials_by_topic(topic):
    """獲取特定主題的材料"""
    materials = load_materials_from_excel()
    topic_materials = materials.get(topic, [])
    return jsonify(topic_materials)

@materials_bp.route('/api/materials/recommended', methods=['GET'])
def get_recommended_materials():
    """獲取推薦的學習材料"""
    materials = load_materials_from_excel()
    recommended = []
    
    # 遍歷每個主題，獲取其中的推薦材料
    for topic, topic_materials in materials.items():
        for material in topic_materials:
            if material.get('推薦', False):
                recommended.append(material)
    
    return jsonify(recommended)

@materials_bp.route('/api/materials/search/<keyword>', methods=['GET'])
def search_materials(keyword):
    """搜索學習材料"""
    materials = load_materials_from_excel()
    results = []
    
    # 搜索所有材料
    for topic, topic_materials in materials.items():
        for material in topic_materials:
            # 檢查標題、描述和主題是否包含關鍵詞
            title = str(material.get('標題', '')).lower()
            description = str(material.get('描述', '')).lower()
            if keyword.lower() in title or keyword.lower() in description or keyword.lower() in topic.lower():
                results.append(material)
    
    return jsonify(results)

# 獲取材料的圖標
def get_material_icon(material_type):
    """根據材料類型返回對應的Font Awesome圖標類"""
    return MATERIAL_ICONS.get(material_type, "fa-file")

# LINE機器人處理函數
def handle_materials_command(text):
    """處理與學習材料相關的命令"""
    
    # 處理查詢所有材料的命令
    if text == "#材料" or text == "#學習材料":
        materials = load_materials_from_excel()
        topics = list(materials.keys())
        
        response = "📚 學習材料主題：\n\n"
        for i, topic in enumerate(topics, 1):
            response += f"{i}. {topic}\n"
        
        response += "\n要查看特定主題的材料，請發送 #材料 [主題名稱]"
        return response
    
    # 處理查詢特定主題材料的命令
    if text.startswith("#材料 ") or text.startswith("#學習材料 "):
        topic = text.split(" ", 1)[1].strip()
        materials = load_materials_from_excel()
        
        if topic in materials:
            topic_materials = materials[topic]
            
            response = f"📚 {topic} 學習材料：\n\n"
            for i, material in enumerate(topic_materials, 1):
                title = material.get('標題', '未命名')
                material_type = material.get('類型', '未分類')
                response += f"{i}. [{material_type}] {title}\n"
            
            response += "\n要查看詳細資訊，請發送 #詳細 [材料編號] [主題]"
            return response
        else:
            return f"找不到主題 '{topic}' 的學習材料。請輸入 #材料 查看所有可用主題。"
    
    # 處理推薦材料的命令
    if text == "#推薦材料" or text == "#推薦":
        materials = load_materials_from_excel()
        recommended = []
        
        for topic, topic_materials in materials.items():
            for material in topic_materials:
                if material.get('推薦', False):
                    recommended.append((topic, material))
        
        if recommended:
            response = "🌟 推薦學習材料：\n\n"
            for i, (topic, material) in enumerate(recommended, 1):
                title = material.get('標題', '未命名')
                material_type = material.get('類型', '未分類')
                response += f"{i}. [{material_type}] {title} (主題: {topic})\n"
            
            return response
        else:
            return "目前沒有推薦的學習材料。"
    
    return None  # 如果不是與材料相關的命令，返回None 