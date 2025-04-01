from linebot.models import RichMenu, RichMenuArea, RichMenuBounds, RichMenuSize
from linebot.models import MessageAction, URIAction
from PIL import Image, ImageDraw, ImageFont
import os
import logging

logger = logging.getLogger(__name__)

def create_rich_menu_image():
    """創建Rich Menu圖片"""
    try:
        img = Image.new('RGB', (2500, 1686), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 分隔線
        draw.line([(0, 562), (2500, 562)], fill=(200, 200, 200), width=5)
        draw.line([(0, 1124), (2500, 1124)], fill=(200, 200, 200), width=5)
        draw.line([(625, 0), (625, 1686)], fill=(200, 200, 200), width=5)
        draw.line([(1250, 0), (1250, 1686)], fill=(200, 200, 200), width=5)
        draw.line([(1875, 0), (1875, 1686)], fill=(200, 200, 200), width=5)
        
        # 嘗試加載字體
        try:
            font = ImageFont.truetype("Arial.ttf", 50)
        except IOError:
            font = ImageFont.load_default()
        
        # 添加文字
        menu_items = [
            ("主題地圖", 312, 281),
            ("任務打卡", 937, 281),
            ("知識挑戰", 1562, 281),
            ("AI助手", 2187, 281),
            ("專注模式", 312, 843),
            ("角色助理", 937, 843),
            ("學習報告", 1562, 843),
            ("記憶卡片", 2187, 843),
            ("幫助", 312, 1405),
            ("設定", 937, 1405),
            ("任務推播", 1562, 1405),
            ("我的帳戶", 2187, 1405)
        ]
        
        for text, x, y in menu_items:
            # 計算文字寬度以居中顯示
            if hasattr(draw, 'textlength'):
                text_width = draw.textlength(text, font=font)
            else:
                text_width = font.getsize(text)[0]
            
            draw.text((x - text_width // 2, y), text, fill=(50, 50, 50), font=font)
        
        # 保存圖片
        img.save("rich_menu.png")
        logger.info("Rich Menu圖片創建成功")
        return "rich_menu.png"
    except Exception as e:
        logger.error(f"創建Rich Menu圖片時發生錯誤: {e}")
        return None

def setup_rich_menu(line_bot_api):
    """設置Rich Menu"""
    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name="學習助手主選單",
        chat_bar_text="點擊查看選單",
        areas=[
            RichMenuArea(  # 主題地圖
                bounds=RichMenuBounds(x=0, y=0, width=625, height=562),
                action=MessageAction(label="主題地圖", text="熱力學地圖")
            ),
            RichMenuArea(  # 任務打卡
                bounds=RichMenuBounds(x=625, y=0, width=625, height=562),
                action=MessageAction(label="任務打卡", text="#今天任務")
            ),
            RichMenuArea(  # 知識挑戰
                bounds=RichMenuBounds(x=1250, y=0, width=625, height=562),
                action=MessageAction(label="知識挑戰", text="#挑戰 熱力學")
            ),
            RichMenuArea(  # AI助手
                bounds=RichMenuBounds(x=1875, y=0, width=625, height=562),
                action=MessageAction(label="AI助手", text="#AI 請幫我解釋熵的概念")
            ),
            RichMenuArea(  # 專注模式
                bounds=RichMenuBounds(x=0, y=562, width=625, height=562),
                action=MessageAction(label="專注模式", text="#開始專注")
            ),
            RichMenuArea(  # 角色助理
                bounds=RichMenuBounds(x=625, y=562, width=625, height=562),
                action=MessageAction(label="角色助理", text="#呼叫 放鬆使者")
            ),
            RichMenuArea(  # 學習報告
                bounds=RichMenuBounds(x=1250, y=562, width=625, height=562),
                action=MessageAction(label="學習報告", text="#報告")
            ),
            RichMenuArea(  # 記憶卡片
                bounds=RichMenuBounds(x=1875, y=562, width=625, height=562),
                action=MessageAction(label="記憶卡片", text="#卡片 列表")
            ),
            RichMenuArea(  # 幫助
                bounds=RichMenuBounds(x=0, y=1124, width=625, height=562),
                action=MessageAction(label="幫助", text="#幫助")
            ),
            RichMenuArea(  # 設定
                bounds=RichMenuBounds(x=625, y=1124, width=625, height=562),
                action=MessageAction(label="設定", text="#設定")
            ),
            RichMenuArea(  # 任務推播
                bounds=RichMenuBounds(x=1250, y=1124, width=625, height=562),
                action=MessageAction(label="任務推播", text="#任務推播")
            ),
            RichMenuArea(  # 我的帳戶
                bounds=RichMenuBounds(x=1875, y=1124, width=625, height=562),
                action=MessageAction(label="我的帳戶", text="#我的帳戶")
            )
        ]
    )
    
    # 創建Rich Menu
    rich_menu_image = create_rich_menu_image()
    
    try:
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
        
        # 上傳Rich Menu圖片
        with open(rich_menu_image, "rb") as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
        
        # 設置為默認菜單
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info(f"Rich Menu 創建成功: {rich_menu_id}")
        return rich_menu_id
    except Exception as e:
        logger.error(f"Rich Menu 創建失敗: {e}")
        return None
