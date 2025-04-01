import os
import logging
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuArea, RichMenuSize, RichMenuBounds, URIAction, MessageAction
from linebot.exceptions import LineBotApiError
from PIL import Image, ImageDraw, ImageFont
import io

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 從環境變數獲取LINE Bot API密鑰
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')

def create_minimal_design_rich_menu():
    """創建簡約線條風格的Rich Menu圖像"""
    width, height = 2500, 1686
    # 黑色背景
    image = Image.new('RGBA', (width, height), (25, 25, 25, 255))
    draw = ImageDraw.Draw(image)
    
    # 劃分六個區域，只用線條
    cell_width = width // 2
    cell_height = height // 3
    
    # 水平線
    for i in range(1, 3):
        y = i * cell_height
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 100), width=3)
    
    # 垂直線
    draw.line([(width//2, 0), (width//2, height)], fill=(255, 255, 255, 100), width=3)
    
    # 定義每個區域的圖標和標籤
    icons = ["🗺️", "👤", "📋", "❓", "⏱️", "🤖"]
    labels = ["主題地圖", "呼叫角色", "今日任務", "問答挑戰", "專注訓練", "AI助手"]
    
    positions = [
        (width//4, height//6), (width*3//4, height//6),
        (width//4, height//2), (width*3//4, height//2),
        (width//4, height*5//6), (width*3//4, height*5//6)
    ]
    
    # 嘗試加載字體，如果失敗則使用默認字體
    try:
        # 嘗試找一個系統上可能存在的字體
        font_path = None
        for path in ["C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/simhei.ttf", 
                    "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc"]:
            if os.path.exists(path):
                font_path = path
                break
        
        # 如果找到了字體，使用它
        if font_path:
            label_font = ImageFont.truetype(font_path, 60)
        else:
            # 否則使用默認字體
            label_font = ImageFont.load_default()
            logger.warning("無法找到合適的中文字體，使用默認字體")
    except Exception as e:
        logger.error(f"加載字體時出錯: {e}")
        label_font = ImageFont.load_default()
    
    # 圓形背景和中心點標記
    for i, (pos, icon, label) in enumerate(zip(positions, icons, labels)):
        # 繪製圓形背景
        draw.ellipse(
            [(pos[0]-200, pos[1]-200), (pos[0]+200, pos[1]+200)],
            outline=(255, 255, 255, 150),
            width=5
        )
        
        # 繪製中心點
        draw.ellipse(
            [(pos[0]-10, pos[1]-10), (pos[0]+10, pos[1]+10)],
            fill=(255, 255, 255, 200)
        )
        
        # 繪製標籤
        try:
            if hasattr(draw, 'textbbox'):  # PIL 8.0.0 以上版本
                bbox = draw.textbbox((0, 0), label, font=label_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:  # 舊版本
                text_width, text_height = draw.textsize(label, font=label_font)
            
            draw.text(
                (pos[0] - text_width // 2, pos[1] + 100),
                label,
                fill=(255, 255, 255, 255),
                font=label_font
            )
        except Exception as e:
            logger.error(f"繪製文字時出錯: {e}")
    
    # 添加細小點作為裝飾
    for _ in range(50):
        import random
        x = random.randint(0, width)
        y = random.randint(0, height)
        size = random.randint(1, 3)
        opacity = random.randint(50, 150)
        draw.ellipse(
            [(x-size, y-size), (x+size, y+size)],
            fill=(255, 255, 255, opacity)
        )
    
    return image

def create_rich_menu_object():
    """創建Rich Menu物件"""
    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name="學習助手功能選單",
        chat_bar_text="打開功能選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=562),
                action=MessageAction(text="主題地圖")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=562),
                action=MessageAction(text="今日任務")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=562, width=1250, height=562),
                action=MessageAction(text="呼叫角色")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=562, width=1250, height=562),
                action=MessageAction(text="問答挑戰")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=1124, width=1250, height=562),
                action=MessageAction(text="專注訓練")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=1124, width=1250, height=562),
                action=MessageAction(text="AI助手")
            )
        ]
    )
    return rich_menu

def create_and_apply_rich_menu():
    """創建並應用Rich Menu"""
    try:
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.error("未設置LINE_CHANNEL_ACCESS_TOKEN環境變數")
            return "錯誤：請先設置LINE_CHANNEL_ACCESS_TOKEN環境變數"
        
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        
        # 創建Rich Menu
        rich_menu = create_rich_menu_object()
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
        logger.info(f"已創建Rich Menu，ID: {rich_menu_id}")
        
        # 創建圖像
        image = create_minimal_design_rich_menu()
        
        # 將PIL圖像轉換為字節流
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        
        # 上傳圖像
        line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', image_bytes)
        logger.info(f"已上傳Rich Menu圖像")
        
        # 設為默認選單
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info(f"已設置為默認Rich Menu")
        
        # 保存圖像到本地（可選）
        os.makedirs('resources/images', exist_ok=True)
        image.save('resources/images/rich_menu_minimal.png')
        
        return f"Rich Menu 創建成功，ID: {rich_menu_id}"
    
    except LineBotApiError as e:
        logger.error(f"LINE Bot API錯誤: {e}")
        return f"錯誤：LINE Bot API錯誤 - {e}"
    except Exception as e:
        logger.error(f"創建Rich Menu時出錯: {e}")
        return f"錯誤：{e}"

def delete_all_rich_menus():
    """刪除所有Rich Menu"""
    try:
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.error("未設置LINE_CHANNEL_ACCESS_TOKEN環境變數")
            return "錯誤：請先設置LINE_CHANNEL_ACCESS_TOKEN環境變數"
        
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        
        # 獲取所有Rich Menu
        rich_menu_list = line_bot_api.get_rich_menu_list()
        
        # 刪除每個Rich Menu
        for rich_menu in rich_menu_list:
            line_bot_api.delete_rich_menu(rich_menu.rich_menu_id)
            logger.info(f"已刪除Rich Menu: {rich_menu.rich_menu_id}")
        
        return f"成功刪除 {len(rich_menu_list)} 個Rich Menu"
    
    except LineBotApiError as e:
        logger.error(f"LINE Bot API錯誤: {e}")
        return f"錯誤：LINE Bot API錯誤 - {e}"
    except Exception as e:
        logger.error(f"刪除Rich Menu時出錯: {e}")
        return f"錯誤：{e}"

def preview_rich_menu():
    """生成Rich Menu預覽圖像，保存到本地但不上傳到LINE"""
    try:
        # 創建圖像
        image = create_minimal_design_rich_menu()
        
        # 確保目錄存在
        os.makedirs('resources/images', exist_ok=True)
        
        # 保存圖像到本地
        preview_path = 'resources/images/rich_menu_preview.png'
        image.save(preview_path)
        
        logger.info(f"Rich Menu預覽已保存到: {preview_path}")
        return f"Rich Menu預覽已保存到: {preview_path}"
    
    except Exception as e:
        logger.error(f"創建Rich Menu預覽時出錯: {e}")
        return f"錯誤：{e}"

def create_gold_design_rich_menu():
    """創建金色主題的Rich Menu圖像，與您分享的圖片風格相似"""
    width, height = 2500, 1686
    # 深藍背景
    image = Image.new('RGBA', (width, height), (0, 20, 40, 255))
    draw = ImageDraw.Draw(image)
    
    # 劃分六個區域
    cell_width = width // 2
    cell_height = height // 3
    
    # 水平線
    for i in range(1, 3):
        y = i * cell_height
        draw.line([(0, y), (width, y)], fill=(200, 180, 120, 100), width=2)
    
    # 垂直線
    draw.line([(width//2, 0), (width//2, height)], fill=(200, 180, 120, 100), width=2)
    
    # 定義每個區域的圖標和標籤
    labels = ["主題地圖", "呼叫角色", "今日任務", "問答挑戰", "專注訓練", "AI助手"]
    
    positions = [
        (width//4, height//6), (width*3//4, height//6),
        (width//4, height//2), (width*3//4, height//2),
        (width//4, height*5//6), (width*3//4, height*5//6)
    ]
    
    # 嘗試加載字體
    try:
        font_path = None
        for path in ["C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/simhei.ttf", 
                    "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc"]:
            if os.path.exists(path):
                font_path = path
                break
        
        if font_path:
            label_font = ImageFont.truetype(font_path, 60)
        else:
            label_font = ImageFont.load_default()
            logger.warning("無法找到合適的中文字體，使用默認字體")
    except Exception as e:
        logger.error(f"加載字體時出錯: {e}")
        label_font = ImageFont.load_default()
    
    # 繪製每個項目
    for i, (pos, label) in enumerate(zip(positions, labels)):
        # 繪製金色圓形
        circle_radius = 150
        draw.ellipse(
            [(pos[0]-circle_radius, pos[1]-circle_radius), 
             (pos[0]+circle_radius, pos[1]+circle_radius)],
            outline=(220, 200, 140, 255),
            width=4
        )
        
        # 根據不同選項添加不同的圖標
        draw_icon(draw, i, pos, circle_radius)
        
        # 繪製標籤
        try:
            if hasattr(draw, 'textbbox'):  # PIL 8.0.0 以上版本
                bbox = draw.textbbox((0, 0), label, font=label_font)
                text_width = bbox[2] - bbox[0]
            else:  # 舊版本
                text_width, _ = draw.textsize(label, font=label_font)
            
            draw.text(
                (pos[0] - text_width // 2, pos[1] + circle_radius + 40),
                label,
                fill=(220, 200, 140, 255),
                font=label_font
            )
        except Exception as e:
            logger.error(f"繪製文字時出錯: {e}")
    
    # 添加細小星點作為裝飾
    for _ in range(100):
        import random
        x = random.randint(0, width)
        y = random.randint(0, height)
        size = random.randint(1, 2)
        opacity = random.randint(50, 150)
        draw.ellipse(
            [(x-size, y-size), (x+size, y+size)],
            fill=(220, 200, 140, opacity)
        )
    
    return image

def draw_icon(draw, icon_index, position, radius):
    """根據索引繪製不同的圖標"""
    x, y = position
    gold_color = (220, 200, 140, 255)
    line_width = 3
    
    if icon_index == 0:  # 主題地圖
        # 繪製地球和地圖標記
        circle_radius = radius * 0.5
        draw.ellipse(
            [(x-circle_radius, y-circle_radius), 
             (x+circle_radius, y+circle_radius)],
            outline=gold_color,
            width=line_width
        )
        
        # 添加地圖上的經緯線
        draw.arc(
            [(x-circle_radius, y-circle_radius*0.7), 
             (x+circle_radius, y+circle_radius*1.3)],
            0, 180, fill=gold_color, width=line_width
        )
        
        draw.arc(
            [(x-circle_radius*1.3, y-circle_radius), 
             (x+circle_radius*0.7, y+circle_radius)],
            90, 270, fill=gold_color, width=line_width
        )
        
        # 添加位置標記
        pin_height = circle_radius * 0.8
        draw.line(
            [(x+circle_radius*0.3, y-circle_radius*0.3), 
             (x+circle_radius*0.3, y-circle_radius*0.3-pin_height)],
            fill=gold_color, width=line_width
        )
        draw.ellipse(
            [(x+circle_radius*0.3-pin_height*0.3, y-circle_radius*0.3-pin_height-pin_height*0.3), 
             (x+circle_radius*0.3+pin_height*0.3, y-circle_radius*0.3-pin_height+pin_height*0.3)],
            outline=gold_color, width=line_width
        )
        
    elif icon_index == 1:  # 呼叫角色
        # 繪製人頭輪廓
        head_radius = radius * 0.4
        draw.ellipse(
            [(x-head_radius, y-head_radius*1.2), 
             (x+head_radius, y+head_radius*0.8)],
            outline=gold_color,
            width=line_width
        )
        
        # 繪製身體
        draw.arc(
            [(x-head_radius*1.5, y+head_radius*0.8), 
             (x+head_radius*1.5, y+head_radius*2.5)],
            180, 0, fill=gold_color, width=line_width
        )
        
        # 繪製大腦
        brain_radius = head_radius * 0.7
        draw.arc(
            [(x-brain_radius, y-head_radius*0.8), 
             (x+brain_radius, y-head_radius*0.2)],
            180, 0, fill=gold_color, width=line_width
        )
        
    elif icon_index == 2:  # 今日任務
        # 繪製任務列表
        list_width = radius * 0.8
        list_height = radius * 1.0
        draw.rectangle(
            [(x-list_width, y-list_height), 
             (x+list_width, y+list_height)],
            outline=gold_color,
            width=line_width
        )
        
        # 繪製紙張頂部的夾子
        clip_width = list_width * 0.3
        draw.rectangle(
            [(x-clip_width, y-list_height-list_height*0.15), 
             (x+clip_width, y-list_height)],
            outline=gold_color,
            width=line_width
        )
        
        # 繪製清單條目
        for i in range(3):
            line_y = y - list_height*0.5 + i * list_height*0.5
            draw.line(
                [(x-list_width*0.7, line_y), (x+list_width*0.7, line_y)],
                fill=gold_color, width=line_width
            )
            
            # 在第一行添加勾選標記
            if i == 0:
                draw.line(
                    [(x-list_width*0.5, line_y-list_height*0.1), 
                     (x-list_width*0.3, line_y+list_height*0.1)],
                    fill=gold_color, width=line_width
                )
                draw.line(
                    [(x-list_width*0.3, line_y+list_height*0.1), 
                     (x-list_width*0.1, line_y-list_height*0.15)],
                    fill=gold_color, width=line_width
                )
        
    elif icon_index == 3:  # 問答挑戰
        # 繪製問號
        draw.arc(
            [(x-radius*0.5, y-radius*0.5), 
             (x+radius*0.5, y+radius*0.5)],
            180, 0, fill=gold_color, width=line_width
        )
        
        draw.line(
            [(x+radius*0.5, y), (x+radius*0.5, y+radius*0.3)],
            fill=gold_color, width=line_width
        )
        
        # 繪製問號的點
        draw.ellipse(
            [(x+radius*0.5-line_width, y+radius*0.5-line_width), 
             (x+radius*0.5+line_width, y+radius*0.5+line_width)],
            fill=gold_color
        )
        
    elif icon_index == 4:  # 專注訓練
        # 繪製沙漏
        draw.line(
            [(x-radius*0.5, y-radius*0.5), (x+radius*0.5, y-radius*0.5)],
            fill=gold_color, width=line_width
        )
        
        draw.line(
            [(x-radius*0.5, y+radius*0.5), (x+radius*0.5, y+radius*0.5)],
            fill=gold_color, width=line_width
        )
        
        draw.line(
            [(x-radius*0.5, y-radius*0.5), (x+radius*0.5, y+radius*0.5)],
            fill=gold_color, width=line_width
        )
        
        draw.line(
            [(x+radius*0.5, y-radius*0.5), (x-radius*0.5, y+radius*0.5)],
            fill=gold_color, width=line_width
        )
        
        # 繪製沙子
        draw.arc(
            [(x-radius*0.3, y+radius*0.2), (x+radius*0.3, y+radius*0.5)],
            0, 180, fill=gold_color, width=line_width
        )
        
    elif icon_index == 5:  # AI助手
        # 繪製機器人頭
        head_width = radius * 0.8
        head_height = radius * 0.6
        draw.rectangle(
            [(x-head_width, y-head_height), 
             (x+head_width, y+head_height)],
            outline=gold_color,
            width=line_width
        )
        
        # 繪製天線
        draw.line(
            [(x, y-head_height), (x, y-head_height-radius*0.3)],
            fill=gold_color, width=line_width
        )
        
        draw.ellipse(
            [(x-radius*0.1, y-head_height-radius*0.3-radius*0.1), 
             (x+radius*0.1, y-head_height-radius*0.3+radius*0.1)],
            outline=gold_color, width=line_width
        )
        
        # 繪製眼睛
        eye_radius = head_width * 0.15
        draw.ellipse(
            [(x-head_width*0.5-eye_radius, y-head_height*0.2-eye_radius), 
             (x-head_width*0.5+eye_radius, y-head_height*0.2+eye_radius)],
            outline=gold_color, width=line_width
        )
        
        draw.ellipse(
            [(x+head_width*0.5-eye_radius, y-head_height*0.2-eye_radius), 
             (x+head_width*0.5+eye_radius, y-head_height*0.2+eye_radius)],
            outline=gold_color, width=line_width
        )
        
        # 繪製嘴巴
        draw.arc(
            [(x-head_width*0.6, y+head_height*0.2), 
             (x+head_width*0.6, y+head_height*0.8)],
            0, 180, fill=gold_color, width=line_width
        )

def preview_gold_rich_menu():
    """生成金色風格Rich Menu預覽圖像"""
    try:
        # 創建圖像
        image = create_gold_design_rich_menu()
        
        # 確保目錄存在
        os.makedirs('resources/images', exist_ok=True)
        
        # 保存圖像到本地
        preview_path = 'resources/images/rich_menu_gold_preview.png'
        image.save(preview_path)
        
        logger.info(f"金色風格Rich Menu預覽已保存到: {preview_path}")
        return f"金色風格Rich Menu預覽已保存到: {preview_path}"
    
    except Exception as e:
        logger.error(f"創建金色風格Rich Menu預覽時出錯: {e}")
        return f"錯誤：{e}"

def create_and_apply_gold_rich_menu():
    """創建並應用金色風格Rich Menu"""
    try:
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.error("未設置LINE_CHANNEL_ACCESS_TOKEN環境變數")
            return "錯誤：請先設置LINE_CHANNEL_ACCESS_TOKEN環境變數"
        
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        
        # 創建Rich Menu
        rich_menu = create_rich_menu_object()
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
        logger.info(f"已創建Rich Menu，ID: {rich_menu_id}")
        
        # 創建圖像
        image = create_gold_design_rich_menu()
        
        # 將PIL圖像轉換為字節流
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        
        # 上傳圖像
        line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', image_bytes)
        logger.info(f"已上傳Rich Menu圖像")
        
        # 設為默認選單
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info(f"已設置為默認Rich Menu")
        
        # 保存圖像到本地（可選）
        os.makedirs('resources/images', exist_ok=True)
        image.save('resources/images/rich_menu_gold.png')
        
        return f"金色風格Rich Menu 創建成功，ID: {rich_menu_id}"
    
    except LineBotApiError as e:
        logger.error(f"LINE Bot API錯誤: {e}")
        return f"錯誤：LINE Bot API錯誤 - {e}"
    except Exception as e:
        logger.error(f"創建Gold Rich Menu時出錯: {e}")
        return f"錯誤：{e}"

if __name__ == "__main__":
    # 當直接運行此文件時，創建Rich Menu預覽
    preview_result = preview_rich_menu()
    print(preview_result)
    
    gold_preview_result = preview_gold_rich_menu()
    print(gold_preview_result) 