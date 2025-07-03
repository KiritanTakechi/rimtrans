# -*- coding: utf-8 -*-
import os
import random
import sys
import subprocess
import time
import json

import argparse
import tomllib

from PIL import Image, ImageDraw, ImageFont
from google.genai.errors import APIError
from lxml import etree
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

import google.genai as genai
from google.genai import types
from tqdm import tqdm

# --- 全局配置  ---
DEFAULT_CONFIG = {
    "system": {
        "steamcmd_path": "./steamcmd/steamcmd.sh",
        "steam_user": "anonymous",
        "steam_password": "",
        "windows_steam_path": "C:/Program Files (x86)/Steam",
        "rimworld_app_id": "294100",
        "gemini_model": "gemini-2.5-flash",
        "slow_mode": False, # 默认关闭慢速模式
        "slow_mode_delay": 2
    }
}

# 输出目录
BASE_WORKING_DIR: Path = Path(__file__).parent
OUTPUT_PATH: Path = BASE_WORKING_DIR / "translation_output"

# RimWorld 核心术语表
RIMWORLD_GLOSSARY = {
    "Addictiveness": "成瘾性", "AI Kassandra": "AI故事叙述者", "AI Persona Core": "人工智能思维核心", "AI Storytellers": "AI故事叙述者",
    "Advanced Weapons": "高级武器", "Agave": "龙舌兰果", "Aiming Time": "瞄准时间", "Allowed area": "许可区域", "Alpaca": "羊驼",
    "Alpaca wool": "羊驼毛", "Alpacahide": "豚鼠皮", "Alphabeaver": "阿尔法海狸", "Animal": "动物", "Animal bed": "动物床铺",
    "Animal sleeping box": "动物睡眠箱", "Animal sleeping spot": "动物睡眠处", "Animals": "动物", "Architect Menu": "建造",
    "Arctic fox": "北极狐", "Arctic foxskin": "北极狐皮", "Arctic wolf": "北极狼", "Arctic wolfskin": "北极狼皮",
    "Arid shrubland": "旱带灌木从", "Armchair": "扶手椅", "Armor": "护甲", "Armor Categories": "护甲种类", "Arms": "手臂",
    "Artillery shell": "炮弹", "Assault Rifle": "突击步枪", "Assignment": "委派方案", "Auto-turret": "无人机枪", "Autodoor": "自动门",
    "Backstories": "背景故事", "Base": "殖民地", "Base Healing Quality": "医疗能力", "Basics": "基础概念", "Battery": "蓄电池",
    "Bearskin": "熊皮", "Beauty": "美观", "Beaverskin": "海狸皮", "Bed": "单人床", "Beer": "啤酒", "Berries": "浆果",
    "Billiards table": "台球桌", "Bionic Arm": "仿生臂", "Bionic Eye": "仿生眼", "Bionic Leg": "仿生腿", "Birch Tree": "桦树",
    "Blue carpet": "蓝色地毯", "Boar": "野猪", "Body Parts": "身体部位", "Boomalope": "爆炸羊", "Boomalope leather": "爆炸兽皮",
    "Boomrat": "爆炸鼠", "Brewery": "酿造台", "Brewing Speed": "酿造速度", "Bush": "灌木", "Butcher table": "屠宰台",
    "Butchery Efficiency": "屠宰效率", "Butchery Speed": "屠宰速度", "Camelhair": "骆驼毛", "Campfire": "篝火", "Capybara": "水豚",
    "Capybaraskin": "水豚皮", "Caribou": "驯鹿", "Carpets": "地毯", "Cassandra Classic": "「经典」卡桑德拉", "Cassowary": "鹤驼",
    "Centipede": "机械蜈蚣", "Character Types": "生物", "Characters": "角色属性", "Charge Lance": "电荷标枪", "Chess table": "象棋桌",
    "Chicken": "鸡", "Chinchilla": "栗鼠", "Chinchilla fur": "粟鼠皮", "Chocolate": "巧克力", "Chop Wood": "伐木", "Claim": "占有",
    "Cloth": "布", "Clothing": "衣服", "Club": "棍棒", "Cobra": "眼镜蛇", "Colonist": "殖民者", "Colonists": "殖民者",
    "Colony": "殖民地", "Combat": "战斗", "Comfort": "舒适", "Comms console": "通讯台", "Construction Speed": "建造速度",
    "Controls": "操作控制", "Cook stove": "电动炉灶", "Cooking Speed": "烹饪速度", "Cooler": "制冷机", "Corn": "玉米",
    "Cotton Plant": "棉花（植株）", "Cougar": "美洲豹", "Cover": "掩护", "Cow": "奶牛", "Crafting spot": "加工点",
    "Crematorium": "焚化炉", "Cryptosleep casket": "低温休眠舱", "Damage": "伤害", "Damage Types": "伤害类型", "DPS": "DPS",
    "Daylily": "金针莱", "Deadfall trap": "尖刺陷阱", "Debris": "碎石", "Deconstruct": "拆除", "Deer": "鹿",
    "Deterioration": "变质", "Devilstrand": "魔菇布", "Dining chair": "餐椅", "Disease": "疾病", "Door": "门",
    "EMP Grenade": "EMP手榴弹", "Eating Speed": "进食速度", "Electric crematorium": "焚化炉", "Electric smelter": "电动熔炼机",
    "Electric smithy": "电动锻造台", "Electric tailoring bench": "电动裁缝台", "Elephant": "大象", "Emu": "鸸鹋",
    "Environment": "环境", "Events": "特殊事件", "Fabric": "纤维", "Fabrics": "纤维", "Feet": "脚部", "Fine Meal": "精致食物",
    "Fire": "火", "Firefighting": "灭火", "Firefoam popper": "泡沫灭火器", "Flammability": "易燃性", "Floor": "地板",
    "Food": "食物", "Food Poison Chance": "烹饪生毒几率", "Frag Grenades": "破片手榴弹", "Fueled smithy": "燃料锻造台",
    "Furniture": "家具", "Gameplay": "游戏机制", "Gazelle": "瞪羚", "Geothermal Generator": "地热发电机", "Gladius": "短剑",
    "Glitterworld": "闪耀世界", "Glitterworld Medicine": "高级药物", "Global Learning Factor": "全局学习能力",
    "Global Work Speed": "全局工作速度", "Gold": "黄金", "Granite Blocks": "花岗岩砖块", "Grass": "草", "Grave": "坟墓",
    "Great Bow": "长弓", "Grizzly Bear": "灰熊", "Growing Zone": "种植区", "Hand-tailoring bench": "手工缝纫台",
    "Hands": "双手", "Happiness": "幸福", "Hare": "野兔", "Haul Things": "搬运", "Hauling": "搬运", "Hay": "干草",
    "Healing Speed": "医疗速度", "Healroot": "药草", "Health": "健康", "Heart": "心脏", "Heater": "加热器",
    "Heavy SMG": "重型冲锋枪", "Herbal Medicine": "草药", "Home Region": "居住区", "Home Zone": "居住区",
    "Hop Plant": "啤酒花（植株）", "Hopper": "进料口", "Hops": "啤酒花", "Horseshoe pins": "掷马蹄铁", "Hospital bed": "病床",
    "Human": "人类", "Human leather": "人皮", "Hunt": "狩猎", "Husky": "哈士奇犬", "Hydroponics basin": "无土栽培皿",
    "Hyperweave": "超织物", "IED trap": "自制炸弹陷阱", "Ibex": "野山羊", "Iguana": "鬣蜥", "Immunity Gain Speed": "免疫力获得速度",
    "Improvised Turret": "简易机枪", "Incendiary Mortar": "燃烧弹迫击炮", "Inferno Cannon": "地狱火加农炮", "Injury": "伤势",
    "Jade": "翡翠", "Joy": "娱乐", "Kidney": "肾", "Knife": "匕首", "LMG": "轻机枪", "Labrador retriever": "拉布拉多猎犬",
    "Large Sculpture": "大雕塑", "Lavish Meal": "奢侈食物", "Leather": "皮革", "Leathers": "皮革", "Legs": "腿部",

    "Limestone Blocks": "石灰岩砖块", "Liver": "肝", "Log wall": "木墙", "Long Sword": "长剑", "Lung": "肺",
    "Machining table": "机械加工台", "Marble Blocks": "大理石砖", "Market Value": "市场价值", "Material": "材质",
    "Materials": "材质", "Max Hit Points": "最大耐久度", "Meal": "熟食", "Meals": "熟食", "Meat": "肉类",
    "Mechanoid": "机械体", "Mechanoid Centipede": "机械蜈蚣", "Mechanoid Scyther": "机械螳螂", "Mechanoids": "机械体",
    "Medical Items": "医疗用品", "Medical Operation Speed": "手术速度", "Medical Potency": "医用效果", "Medicine": "药物",
    "Megascarab": "巨型甲虫", "Megascreen Television": "巨屏电视", "Megaspider": "巨型蜘蛛", "Megatherium": "大地懒",
    "Melee Hit Chance": "近战攻击命中率", "Mental Break Threshold": "崩溃临界值", "Metal tile": "金属地砖",
    "Milk": "鲜奶", "Mine": "采矿", "Minigun": "速射机枪", "Mining Speed": "开采速度", "Misc": "杂项",
    "Mood": "心情", "Mortar": "迫击炮", "Move Speed": "移动速度", "Muffalo": "野牦牛", "Multi-analyzer": "多元分析仪",
    "Need": "需求", "Needs": "需求", "Neolithic": "新石器", "Nutrient Paste Meal": "营养糊",
    "Nutrient paste dispenser": "营养糊供应机", "Oak Tree": "橡树", "Orders": "命令", "Ostrich": "鸵鸟",
    "PDW": "冲锋手枪", "Packaged Survival Meal": "生存包装食品", "Pain": "痛感", "Panther": "黑豹",
    "Paved tile": "铺装地砖", "Peg Leg": "假腿", "Pemmican": "肉脯", "People": "人", "Phoebe Chillax": "「建筑师」菲比",
    "Pig": "猪", "Pila": "重标枪", "Pine Tree": "松树", "Pistol": "自动手枪", "Plague": "瘟疫", "Plan": "计划",
    "Planet": "星球", "Plant Work Speed": "种植速度", "Plant pot": "花盆", "Plants": "植物", "Plasteel": "玻璃钢",
    "Polar bear": "北极熊", "Poplar Tree": "杨树", "Potato Plant": "土豆（植株）", "Potatoes": "土豆",
    "Power": "电力", "Power Claw": "动力爪", "Power conduit": "电缆", "Power switch": "电力开关",
    "Primitive": "原始", "Prisoner": "囚犯", "Production": "生产", "Psychic Sensitivity": "灵能敏感度",
    "Pump Shotgun": "泵动霰弹枪", "Quality": "品质", "R-4 charge rifle": "R4电荷步枪", "Raccoon": "浣熊",
    "Raider": "掠夺者", "Randy Random": "「随机」兰迪", "Raw Food": "生食", "Recruit Prisoner Chance": "招募囚犯几率",
    "Research": "研究", "Research Speed": "研究速度", "Research bench": "简易研究台", "Resources": "资源",
    "Rest": "休息", "Rest Effectiveness": "休息效率", "Rhinoceros": "犀牛", "Rice": "稻米", "Rifle": "步枪",
    "Room roles": "房间功能", "Rose": "玫瑰", "Royal Bed": "豪华双人床", "Royalty": "皇权", "Rubble": "碎石",
    "SMG": "冲锋枪", "Sandbag": "沙袋", "Sandstone Blocks": "砂岩砖", "Saturation": "饱腹度",
    "Sculptor's table": "雕刻台", "Sculptures": "雕塑", "Scyther": "机械螳螂", "Scyther Blade": "螳螂刀",
    "Security": "防卫", "Sell Price Multiplier": "出售价格系数", "Shield Max Energy": "护盾最大能量",
    "Shield Recharge Rate": "护盾充能速度", "Ship": "飞船", "Ship computer core": "飞船电脑核心",
    "Ship cryptosleep casket": "飞船休眠舱", "Ship engine": "飞船引擎", "Ship reactor": "飞船反应堆",
    "Shooting Accuracy": "射击精度", "Short Bow": "短弓", "Sickness": "疾病", "Silver": "白银",
    "Simple Meal": "简易食物", "Simple Prosthetic Arm": "简易假臂", "Simple Prosthetic Leg": "简易假腿",
    "Skills": "技能", "Slate Blocks": "板岩砖", "Sleeping Spot": "睡眠点", "Small Sculpture": "小雕塑",
    "Smelting Speed": "熔炼速度", "Smithing Speed": "锻造速度", "Smooth stone": "光滑石板",

    "Smoothing Speed": "打磨速度", "Sniper Rifle": "狙击步枪", "Snowhare": "雪兔", "Social": "社交",
    "Social Chat Impact": "社交影响", "Solar generator": "太阳能板", "Spear": "矛", "Squirrel": "松鼠",
    "Standing Lamp": "落地灯", "Steel": "钢铁", "Sterile tile": "无菌地砖", "Stockpile zone": "贮存区",
    "Stone Blocks": "石块", "Stonecutting Speed": "切石速度", "Stool": "凳子", "Strawberry Plant": "草莓（植株）",
    "Structure": "结构", "Sun lamp": "太阳灯", "Surgery Success Chance": "手术成功率", "Survival Rifle": "幸存者步枪",
    "Synthread": "合成纤维", "T-9 Incendiary Launcher": "燃烧弹发射器", "Table": "桌子", "Tailoring Speed": "缝制速度",
    "Tall Grass": "高草", "Temperature": "温度", "Textiles": "纺织品", "Thoughts": "想法", "Thrumbo": "敲击兽",
    "Tick": "刻", "Time": "时间", "Tool cabinet": "工具柜", "Torch lamp": "火把", "Torso": "躯干",
    "Tortoise": "乌龟", "Trade": "贸易", "Trade Price Improvement": "交易价格改善", "Trader": "商人",

    "Traits": "特性", "Trees": "树木", "Triple Rocket Launcher": "三管火箭发射器", "Tube Television": "显像管电视",
    "Tundra": "苔原", "Turkey": "火鸡", "Turret": "炮塔", "UI": "用户界面", "Uranium": "铀",
    "User interface": "用户界面", "Vent": "通风口", "Version": "版本", "Vitals monitor": "体征监测仪",
    "Wall": "墙", "Warg": "座狼", "Weapon": "武器", "Weapons": "武器", "Wild Plants": "野生植物",
    "Wind Turbine": "风力发电机", "Wood": "木材", "Wood-fired generator": "木柴发电机", "Wood floor": "木地板",
    "Work To Make": "工作量", "World": "世界", "World Generation": "世界生成", "Yorkshire terrier": "约克夏㹴",
    "Zone": "区域", "pawn": "殖民者", "raid": "袭击"
}

# --- 脚本核心代码 ---

# --- Pydantic模型定义 ---
class TranslationItem(BaseModel):
    """定义单个翻译条目的数据结构"""
    key: str = Field(description="The original XML tag or injection key. This field MUST NOT be changed or translated.")
    source_text: str = Field(description="The original English text to be translated.")
    translated_text: str = Field(description="The translated Simplified Chinese text. This is the field you need to fill.")

# --- “包装器” Pydantic 模型 ---
class TranslationResponse(BaseModel):
    """定义API返回的JSON对象的顶层结构，用于包装翻译条目列表。"""
    translations: List[TranslationItem] = Field(description="A list of all the translated items.")


def get_workshop_content_path() -> Path:
    """根据操作系统自动获取 Steam Workshop 内容的基础路径。"""
    platform = sys.platform
    home = Path.home()

    if platform == "win32":
        # Windows: 通常在 Steam 安装目录下
        path = Path(CONFIG['system']['windows_steam_path']) / "steamapps" / "workshop" / "content"
    elif platform == "darwin":
        # macOS
        path = home / "Library/Application Support/Steam/steamapps/workshop/content"
    elif platform == "linux":
        # Linux: 可能是 .steam/steam 或 .local/share/Steam
        path1 = home / ".steam/steam/steamapps/workshop/content"
        path2 = home / ".local/share/Steam/steamapps/workshop/content"
        if path1.exists():
            path = path1
        else:
            path = path2  # 默认使用第二个常见路径
    else:
        raise OSError("不支持的操作系统，无法确定 Steam Workshop 路径。")

    print(f"检测到系统平台: {platform}, 将在此路径查找 Mod: {path}")
    if not path.exists():
        print(f"警告: 自动检测到的 Steam Workshop 路径不存在。请确保 Steam 已安装且路径正确。")
    return path


def setup_environment():
    """初始化环境，检查配置并创建所需目录。"""
    print("--- 环境设置 ---")
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("错误: 找不到环境变量 'GEMINI_API_KEY'。")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        print("Gemini API 客户端初始化成功。")
    except Exception as e:
        print(f"错误: Gemini API 客户端初始化失败: {e}")
        sys.exit(1)

    if not Path(CONFIG['system']['steamcmd_path']).is_file():
        print(f"错误: 在路径 '{CONFIG['system']['steamcmd_path']}' 未找到 SteamCMD。")
        sys.exit(1)

    if not CONFIG['mod_ids']['translate']:
        print("错误: 'CONFIG['mod_ids']['translate']' 不能为空。")
        sys.exit(1)

    OUTPUT_PATH.mkdir(exist_ok=True)
    print(f"输出目录: {OUTPUT_PATH}\n")
    return client


def parse_ids(id_string: str) -> List[str]:
    """将逗号分隔的 ID 字符串解析为列表。"""
    if not id_string:
        return []
    return [item.strip() for item in id_string.split(',') if item.strip()]


def download_with_steamcmd(mod_ids: List[str]):
    """使用 SteamCMD 下载指定的创意工坊物品。"""
    if not mod_ids:
        return

    print(f"--- 开始使用 SteamCMD 下载 {len(mod_ids)} 个 Mod ---")
    command = [CONFIG['system']['steamcmd_path'], "+login", CONFIG['system']['steam_user'], CONFIG['system']['steam_password']]

    for mod_id in mod_ids:
        print(f"准备下载 Mod ID: {mod_id}")
        command.extend(["+workshop_download_item", CONFIG['system']['rimworld_app_id'], mod_id])
    command.append("+quit")

    try:
        # 使用 Popen 以便实时读取输出
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   encoding='utf-8')

        # 简单的进度条逻辑
        with tqdm(total=len(mod_ids), desc="SteamCMD 下载中", unit="item") as pbar:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if "Success. Downloaded item" in line:
                        pbar.update(1)

        if process.returncode != 0:
            print(f"\n警告: SteamCMD 进程以非零代码 {process.returncode} 退出。")
        else:
            print("\n所有 Mod 下载任务已提交。")

    except FileNotFoundError:
        print(f"错误: 无法执行 SteamCMD。路径 '{CONFIG['system']['steamcmd_path']}' 是否正确？")
        sys.exit(1)
    except Exception as e:
        print(f"SteamCMD 执行时发生未知错误: {e}")
        sys.exit(1)
    print("--- 下载完成 ---\n")


def get_mod_info(mod_path: Path) -> Optional[Dict[str, str]]:
    """从Mod的About.xml中提取名称和packageId。"""
    about_file = mod_path / "About" / "About.xml"
    if not about_file.is_file():
        return None
    try:
        tree = etree.parse(str(about_file))
        root = tree.getroot()
        name_node = root.find("name")
        package_id_node = root.find("packageId")
        author_node = root.find("author")

        # 清理函数，只保留字母、数字和下划线
        def sanitize_for_package_id(text: str) -> str:
            return "".join(c for c in text if c.isalnum() or c == '_')

        author = sanitize_for_package_id(author_node.text.strip()) if author_node is not None and author_node.text else "UnknownAuthor"
        name = name_node.text.strip() if name_node is not None and name_node.text else mod_path.name

        # 使用更安全的清理函数
        safe_name_for_id = sanitize_for_package_id(name)

        package_id = package_id_node.text.strip() if package_id_node is not None and package_id_node.text else f"{author}.{safe_name_for_id}"

        return {"name": name, "packageId": package_id.lower()}
    except etree.XMLSyntaxError:
        return None


def create_placeholder_images(about_dir: Path):
    """使用Pillow库和自带的Inter字体创建占位符图片，并动态调整字体大小以适应文本。"""
    print("正在生成占位符图片...")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("警告: Pillow库未安装，无法生成图片。请运行 'pip install Pillow'。")
        return

    mod_name = CONFIG['pack_info']['name']
    author_name = CONFIG['pack_info']['author']
    font_path = Path(__file__).parent / "assets" / "Inter-Regular.ttf"

    # --- 生成 Preview.png ---
    preview_size = (640, 360)
    preview_bg_color = (48, 48, 64)
    text_color = (255, 255, 255)

    preview_image = Image.new('RGB', preview_size, preview_bg_color)
    draw = ImageDraw.Draw(preview_image)

    # --- 标题字体动态大小逻辑 ---
    font_size = 60  # 初始最大字体大小
    title_font = None
    padding = 40  # 图片左右留白

    while font_size > 10:  # 最小字体限制
        try:
            if font_path.is_file():
                title_font = ImageFont.truetype(str(font_path), font_size)
            else:  # 字体文件不存在，使用默认字体并跳出循环
                title_font = ImageFont.load_default(size=30 if font_size > 20 else 15)
                break
        except Exception:  # 字体加载异常
            title_font = ImageFont.load_default()
            break

        title_bbox = draw.textbbox((0, 0), mod_name, font=title_font)
        text_width = title_bbox[2] - title_bbox[0]

        if text_width < preview_size[0] - padding:
            # 如果宽度合适，就用这个字体大小
            break

        font_size -= 2  # 否则，缩小字体再试

    # 使用最终计算好的字体大小来绘制文本
    title_bbox = draw.textbbox((0, 0), mod_name, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    title_pos = ((preview_size[0] - title_width) / 2, 140 - (title_height / 2))  # 垂直居中
    draw.text(title_pos, mod_name, fill=text_color, font=title_font)

    # 绘制作者信息 (通常不需要动态大小，但依然使用try-except)
    try:
        if font_path.is_file():
            subtitle_font = ImageFont.truetype(str(font_path), 30)
        else:
            subtitle_font = ImageFont.load_default(size=15)
    except Exception:
        subtitle_font = ImageFont.load_default()

    subtitle_text = f"Translation by {author_name}"
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_pos = ((preview_size[0] - subtitle_width) / 2, 220)
    draw.text(subtitle_pos, subtitle_text, fill=(200, 200, 200), font=subtitle_font)

    preview_image.save(about_dir / "Preview.png")

    # --- 生成 ModIcon.png ---
    icon_size = (256, 256)
    icon_image = Image.new('RGB', icon_size, preview_bg_color)
    draw = ImageDraw.Draw(icon_image)

    icon_text = "".join([word[0] for word in mod_name.split()[:2]]).upper() or (
        mod_name[0].upper() if mod_name else "T")

    try:
        if font_path.is_file():
            icon_font = ImageFont.truetype(str(font_path), 120)  # 图标字体可以大一些
        else:
            icon_font = ImageFont.load_default(size=40)
    except Exception:
        icon_font = ImageFont.load_default()

    # 简单处理，通常图标文字不会超出
    icon_bbox = draw.textbbox((0, 0), icon_text, font=icon_font)
    icon_width = icon_bbox[2] - icon_bbox[0]
    icon_height = icon_bbox[3] - icon_bbox[1]
    # 进行轻微的垂直偏移，让文字视觉上更居中
    icon_pos = ((icon_size[0] - icon_width) / 2, (icon_size[1] - icon_height) / 2 - (icon_font.size * 0.1))
    draw.text(icon_pos, icon_text, fill=text_color, font=icon_font)

    icon_image.save(about_dir / "ModIcon.png")
    print("  -> 已自动生成自适应文本大小的 Preview.png 和 ModIcon.png。")


def create_about_file(output_path: Path, mod_info_map: Dict[str, dict]):
    """创建汉化包的About/About.xml文件 (lxml版本)。"""
    about_dir = output_path / "About"
    about_dir.mkdir(exist_ok=True, parents=True)

    # 1. 创建根节点
    root = etree.Element("ModMetaData")

    # 2. 添加子节点和内容
    etree.SubElement(root, "name").text = CONFIG['pack_info']['name']
    etree.SubElement(root, "author").text = CONFIG['pack_info']['author']

    supported_versions_node = etree.SubElement(root, "supportedVersions")
    for version in CONFIG['versions']['targets']:
        etree.SubElement(supported_versions_node, "li").text = version

    package_id = f"{CONFIG['pack_info']['author'].replace(' ', '')}.{CONFIG['pack_info']['name'].replace(' ', '')}"
    etree.SubElement(root, "packageId").text = package_id

    supported_mods_list = "\n".join([f"  - {info['name']}" for info in mod_info_map.values()])
    full_description = CONFIG['pack_info']['description'] + supported_mods_list

    etree.SubElement(root, "description").text = full_description

    # 3. 循环添加依赖项
    # dependencies_node = etree.SubElement(root, "modDependencies")
    # for mod_info in mod_info_map.values():
    #     li_node = etree.SubElement(dependencies_node, "li")
    #     etree.SubElement(li_node, "packageId").text = mod_info['packageId']
    #     etree.SubElement(li_node, "displayName").text = mod_info['name']
    #     etree.SubElement(li_node, "steamWorkshopUrl").text = f"steam://url/CommunityFilePage/{mod_info['id']}"

    # 4. 循环添加加载顺序
    load_after_node = etree.SubElement(root, "loadAfter")
    for mod_info in mod_info_map.values():
        etree.SubElement(load_after_node, "li").text = mod_info['packageId']

    # 5. 生成并写入文件
    tree = etree.ElementTree(root)
    tree.write(
        str(about_dir / "About.xml"),
        encoding='utf-8',
        xml_declaration=True,
        pretty_print=True
    )

    print("已生成 About/About.xml。")

    published_file_id_path = about_dir / "PublishedFileId.txt"
    previous_ids_str = CONFIG['mod_ids'].get('previous', '')
    prev_ids = parse_ids(previous_ids_str)

    if prev_ids:
        main_id_to_write = prev_ids[0]
        published_file_id_path.write_text(main_id_to_write.strip())
        print(f"检测到 'previous' ID，已将 {main_id_to_write} 写入 PublishedFileId.txt 用于更新。")
    else:
        published_file_id_path.touch()
        print("未提供 'previous' ID，已创建空的 PublishedFileId.txt 用于首次上传。")

    create_placeholder_images(about_dir, CONFIG['pack_info']['name'], CONFIG['pack_info']['author'])


def create_load_folders_file(output_path: Path, mod_info_map: Dict[str, dict]):
    """创建LoadFolders.xml文件 (lxml版本)。"""
    root = etree.Element("loadFolders")

    for version in CONFIG['versions']['targets']:
        version_node = etree.SubElement(root, f"v{version}")
        for mod_info in mod_info_map.values():
            safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
            li_node = etree.SubElement(version_node, "li")
            li_node.set("IfModActive", mod_info['packageId'])
            li_node.text = f"Cont/{safe_mod_name}"

    tree = etree.ElementTree(root)
    tree.write(
        str(output_path / "LoadFolders.xml"),
        encoding='utf-8',
        xml_declaration=True,
        pretty_print=True
    )
    print("生成 LoadFolders.xml。")


def create_self_translation(output_path: Path):
    """为汉化包自身创建简体中文翻译 (lxml版本)。"""
    lang_dir = output_path / "Languages" / "ChineseSimplified" / "Keyed"
    lang_dir.mkdir(parents=True, exist_ok=True)

    root = etree.Element("LanguageData")

    # 动态生成tag名
    tag_name = f"{CONFIG['pack_info']['author'].replace(' ', '')}.{CONFIG['pack_info']['name'].replace(' ', '')}.ModName"
    etree.SubElement(root, tag_name).text = CONFIG['pack_info']['name']

    tree = etree.ElementTree(root)
    tree.write(
        str(lang_dir / "SelfTranslation.xml"),
        encoding='utf-8',
        xml_declaration=True,
        pretty_print=True
    )
    print("为汉化包创建自翻译文件。")


def find_language_files(mod_path: Path, lang_folder: str) -> List[Path]:
    """在 Mod 目录中查找指定语言的 XML 文件，修复了文件名冲突的bug。"""
    found_files_map = {}  # 使用相对路径作为键，避免文件名冲突

    def scan_lang_dir(lang_dir: Path):
        if not lang_dir.is_dir(): return
        for f in lang_dir.rglob("*.xml"):
            relative_path = f.relative_to(lang_dir)
            found_files_map[relative_path] = f

    # 优先级顺序: 根目录 -> 版本目录 (后面的会覆盖前面的)
    scan_lang_dir(mod_path / "Languages" / lang_folder)
    for version in CONFIG['versions']['targets']:
        scan_lang_dir(mod_path / version / "Languages" / lang_folder)

    # 备用方案，用于结构非常不标准的Mod
    if not found_files_map:
        for p in mod_path.glob('**/Languages'):
            lang_path = p / lang_folder
            if lang_path.is_dir():
                return sorted(list(lang_path.rglob("*.xml")))

    return sorted(list(found_files_map.values()))


def load_xml_as_dict(file_path: Path) -> Dict[str, str]:
    """将 RimWorld 语言 XML 文件解析为字典 (使用 lxml)。"""
    translations = {}
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(str(file_path), parser)
        root = tree.getroot()
        for elem in root:
            # --- 修正点: 确保只处理元素节点，忽略注释等 ---
            if isinstance(elem.tag, str) and elem.text:
                translations[elem.tag] = elem.text.strip()
    except etree.XMLSyntaxError as e:
        print(f"警告: lxml解析文件失败: {file_path}, 错误: {e}")
    return translations


def build_translation_memory(prev_ids: List[str], workshop_path: Path) -> Dict[str, dict]:
    """从旧汉化包的translation_cache.json文件中构建三方校对记忆库。"""
    if not prev_ids:
        return {}

    print("--- 正在构建三方校对记忆库 ---")
    memory = {}
    mod_content_path = workshop_path / CONFIG['system']['rimworld_app_id']

    for mod_id in tqdm(prev_ids, desc="扫描旧汉化包"):
        mod_path = mod_content_path / mod_id
        if not mod_path.is_dir():
            print(f"\n警告: 找不到 Mod {mod_id} 的下载目录，跳过。")
            continue

        cache_files = list(mod_path.rglob("translation_cache.json"))

        if not cache_files:
            print(f"\n[记忆库] 在Mod '{mod_id}' 中未找到 translation_cache.json 文件。")
            continue

        print(f"\n[记忆库] 在Mod '{mod_id}' 中找到 {len(cache_files)} 个缓存文件，开始加载...")
        for file_path in cache_files:
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    memory.update(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"  -> 警告: 读取或解析缓存文件失败: {file_path}, 错误: {e}")

    final_count = len(memory)
    print(f"\n构建完成！翻译记忆库包含 {final_count} 个条目。\n")
    return memory


def get_setup_prompt() -> str:
    """构建用于初始化对话历史的系统指令和术语表。"""
    base_system_prompt = """你是一个为游戏《边缘世界》(RimWorld) 设计的专业级翻译引擎。你的任务是将用户提供的JSON对象中的 `source_text` 字段翻译成简体中文，并填入 `translated_text` 字段。
请严格遵守以下规则：
1.  **保持键值不变**: 绝对不要修改 `key` 字段和 `source_text` 字段。
2.  **精准翻译**: 确保翻译内容符合《边缘世界》的语境。
3.  **返回完整JSON**: 你的输出必须是完整的、包含所有原始条目的JSON数组。
4.  **处理换行符标记**: 文本中的 `[BR]` 标记是一个特殊的换行符占位符。在翻译时，必须在对应的位置原封不动地保留 `[BR]` 标记。绝对不能翻译、删除或将其转换成其他形式。"""

    glossary_prompt_part = "5. **术语统一**: 这是最重要的规则。请严格参考以下术语表进行翻译，确保关键词的统一性：\n"
    glossary_items = [f"- '{en.lower()}': '{cn}'" for en, cn in RIMWORLD_GLOSSARY.items()]
    glossary_prompt_part += "\n".join(glossary_items)

    return f"{base_system_prompt}\n\n{glossary_prompt_part}\n\n我明白了这些规则，请开始提供需要翻译的JSON内容。"


def convert_dict_to_json_items(data: Dict[str, str]) -> List[Dict[str, str]]:
    """将Python字典转换为用于JSON输入的列表，并将\n替换为[BR]标记。"""
    return [{"key": k, "source_text": v.replace('\n', '[BR]'), "translated_text": ""} for k, v in data.items()]


def convert_parsed_json_to_dict(parsed_items: List[TranslationItem]) -> Dict[str, str]:
    """将API返回的Pydantic对象列表转换为Python字典，并将所有换行表示统一为字符串'\\n'。"""
    final_dict = {}
    for item in parsed_items:
        # 关键修正：无论AI返回了[BR]还是\n，都统一为字符串"\\n"
        normalized_text = item.translated_text.replace('[BR]', '\\n').replace('\n', '\\n')
        final_dict[item.key] = normalized_text
    return final_dict

def translate_with_json_mode(client: genai.Client, history: List[types.Content],
                             items_to_translate: List[Dict[str, str]]) -> Optional[List[TranslationItem]]:
    """
    在模拟的会话中，使用JSON模式翻译一个批次。
    """
    # 将待翻译内容构建为用户的新消息
    user_prompt = f"请翻译以下JSON数组中的条目:\n{json.dumps(items_to_translate, indent=2, ensure_ascii=False)}"

    # 将新消息加入历史记录
    current_contents = history + [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]

    max_retries = 5
    base_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=CONFIG['system']['gemini_model'],
                contents=current_contents,
                # 这是JSON模式的核心配置
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TranslationResponse,
                    temperature=0.2
                )
            )
            if hasattr(response, 'parsed') and response.parsed is not None:
                return response.parsed.translations
            else:
                print("  -> 警告: API返回了空结果，可能是因为安全设置。")
                return None

        except APIError as e:
            # 专门处理429频率限制错误
            if e.code == 429:  # 使用 .code 属性更准确
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(
                        f"\n  -> 警告: 触发API频率限制。将在 {delay:.1f} 秒后重试 (第 {attempt + 1}/{max_retries} 次)...")
                    time.sleep(delay)
                else:
                    print(f"  -> 错误: 重试 {max_retries} 次后仍触发频率限制。请检查您的配额或开启慢速模式。")
                    return None
            else:
                # 其他API错误直接报告，不重试
                print(f"在JSON模式下调用 Gemini 时发生API错误: {e}")
                return None
        except Exception as e:
            print(f"在JSON模式下调用 Gemini 时发生未知错误: {e}")
            return None
    return None  # 所有重试失败后返回


def translate_and_save(client: genai.Client, history: List[types.Content], targets: Dict[str, str],
                       memory: Dict[str, dict], output_file_path: Path) -> Dict[str, dict]:
    """
    通用翻译和保存逻辑。
    使用三方校对记忆库，并返回为新缓存准备的数据。
    """
    to_translate_dict = {}
    final_translation_dict = {}
    new_cache_data = {}

    for key, new_en_text in targets.items():
        if key in memory:
            old_en_text = memory[key].get('en', '')
            old_cn_text = memory[key].get('cn', '')
            # 如果新旧英文一致，直接使用旧中文
            if new_en_text == old_en_text:
                final_translation_dict[key] = old_cn_text
                new_cache_data[key] = {'en': new_en_text, 'cn': old_cn_text}
            else:
                # 英文原文已更新，需要重翻
                to_translate_dict[key] = new_en_text
        else:
            # 全新条目，需要翻译
            to_translate_dict[key] = new_en_text

    if to_translate_dict:
        json_items_to_translate = convert_dict_to_json_items(to_translate_dict)
        if CONFIG['system'].get('slow_mode', False):
            time.sleep(CONFIG['system'].get('slow_mode_delay', 2))

        parsed_result = translate_with_json_mode(client, history, json_items_to_translate)

        if parsed_result:
            translated_dict = convert_parsed_json_to_dict(parsed_result)
            response_for_history = TranslationResponse(translations=parsed_result)
            history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=json.dumps(json_items_to_translate))]))
            history.append(
                types.Content(role="model", parts=[types.Part.from_text(text=response_for_history.model_dump_json())]))

            for key, original_text in to_translate_dict.items():
                translated_text = translated_dict.get(key)
                if translated_text:
                    final_translation_dict[key] = translated_text
                    new_cache_data[key] = {'en': original_text, 'cn': translated_text}
                else:
                    final_translation_dict[key] = f"【原文】{original_text}"
                    new_cache_data[key] = {'en': original_text, 'cn': f"【原文】{original_text}"}
        else:
            for key, original_text in to_translate_dict.items():
                final_translation_dict[key] = f"【API错误】{original_text}"
                new_cache_data[key] = {'en': original_text, 'cn': f"【API错误】{original_text}"}

    if not final_translation_dict: return {}

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    root = etree.Element("LanguageData")
    for key in targets:
        if key in final_translation_dict:
            node = etree.SubElement(root, key)
            node.text = final_translation_dict[key]
    tree = etree.ElementTree(root)
    tree.write(str(output_file_path), encoding='utf-8', xml_declaration=True, pretty_print=True)

    return new_cache_data


def process_standard_translation(client: genai.Client, history: List[types.Content], mod_path: Path, mod_info: Dict,
                                 memory: Dict, output_path: Path) -> Dict[str, dict]:
    mod_cache = {}
    english_files = find_language_files(mod_path, "English")
    if not english_files: return mod_cache

    print(f"  -> 找到 {len(english_files)} 个标准语言文件，在当前会话中处理...")
    for file_path in english_files:
        targets = load_xml_as_dict(file_path)
        if not targets: continue
        try:
            english_dir = next(p for p in file_path.parents if p.name == 'English')
            output_relative_path = file_path.relative_to(english_dir)
        except StopIteration:
            continue
        safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
        output_file_path = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / output_relative_path

        new_cache_entries = translate_and_save(client, history, targets, memory, output_file_path)
        mod_cache.update(new_cache_entries)
    return mod_cache


def process_def_injection_translation(client: genai.Client, history: List[types.Content], mod_path: Path,
                                      mod_info: Dict, memory: Dict, output_path: Path):
    """处理Defs/和Patches/文件夹中的注入式翻译，采用最终的、兼容复杂结构的扫描逻辑。"""
    mod_cache = {}

    # 1. 按“根目录 -> 版本1 -> 版本2...”的顺序获取所有待扫描文件
    files_to_scan_in_order = []

    # 阶段一: 扫描根目录
    for folder_name in ["Defs", "Patches"]:
        root_path = mod_path / folder_name
        if root_path.is_dir():
            files_to_scan_in_order.extend(root_path.rglob("*.xml"))

    # 阶段二: 按顺序扫描所有版本目录
    for version in CONFIG['versions']['targets']:
        version_root_path = mod_path / version
        if not version_root_path.is_dir():
            continue

        # 在版本目录下，递归查找所有Defs和Patches文件夹
        for sub_folder_name in ["Defs", "Patches"]:
            # 使用rglob可以找到所有深度的匹配项，如 1.5/Common/Defs, 1.5/Mods/SomeMod/Patches
            for folder in version_root_path.rglob(sub_folder_name):
                if folder.is_dir():
                    files_to_scan_in_order.extend(folder.rglob("*.xml"))

    if not files_to_scan_in_order: return

    print(f"  -> 找到 {len(files_to_scan_in_order)} 个定义(Defs/Patches)文件，开始扫描...")

    all_targets_grouped = {}
    parser = etree.XMLParser(remove_blank_text=True, recover=True)

    def find_translatables_in_elements(elements_iterator, source_file_path, group_dict):
        for element in elements_iterator:
            if not isinstance(element.tag, str): continue
            def_type, def_name_node = element.tag, element.find("defName")
            if def_name_node is None or not def_name_node.text: continue
            def_name = def_name_node.text.strip()
            if any(char in def_name for char in ['{', '}', '(', ')', '/']): continue
            for sub_element in element:
                if isinstance(sub_element.tag, str) and sub_element.tag in CONFIG['rules'][
                    'translatable_def_tags'] and sub_element.text:
                    if def_type not in group_dict: group_dict[def_type] = {}
                    source_filename = source_file_path.name
                    if source_filename not in group_dict[def_type]: group_dict[def_type][source_filename] = {}
                    group_dict[def_type][source_filename][f"{def_name}.{sub_element.tag}"] = sub_element.text.strip()

    for file_path in dict.fromkeys(files_to_scan_in_order):  # 使用dict.fromkeys去重，同时保持顺序
        try:
            tree = etree.parse(str(file_path), parser)
            root = tree.getroot()
            if root is None: continue
            find_translatables_in_elements(root, file_path, all_targets_grouped)
            for value_node in root.xpath('//value'):
                if len(value_node): find_translatables_in_elements(value_node, file_path, all_targets_grouped)
        except etree.XMLSyntaxError as e:
            continue

    if not all_targets_grouped:
        print("  -> 未在Defs/Patches中找到可翻译内容。")
        return

    safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()

    for def_type, files in all_targets_grouped.items():
        print(f"    -> 发现Def类型: {def_type}")
        for filename, targets in files.items():
            print(f"      -> 正在处理来自 {filename} 的 {len(targets)} 个条目")
            output_dir = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / "DefInjected" / def_type
            output_file_path = output_dir / filename
            translate_and_save(client, history, targets, memory, output_file_path)
            new_cache_entries = translate_and_save(client, history, targets, memory, output_file_path)
            mod_cache.update(new_cache_entries)

    return mod_cache


def main(config: dict):
    """脚本主入口，采用最终的“三方校对”逻辑。"""
    global CONFIG
    CONFIG = config
    client = setup_environment()
    workshop_path = get_workshop_content_path()
    prev_ids = parse_ids(CONFIG['mod_ids'].get('previous', ''))
    new_ids = parse_ids(CONFIG['mod_ids']['translate'])
    if not new_ids: print("警告: 'translate' 列表为空..."); return
    download_with_steamcmd(list(set(prev_ids + new_ids)))

    mod_info_map = {}
    mod_content_path = workshop_path / CONFIG['system']['rimworld_app_id']
    print("\n--- 正在收集待汉化Mod的元数据 ---")
    for mod_id in new_ids:
        mod_path = mod_content_path / mod_id
        if mod_path.is_dir():
            info = get_mod_info(mod_path)

            if info is None:
                print(f"警告: 无法为Mod {mod_id} 解析元数据，将使用ID作为名称。")
                info = {"name": mod_id, "packageId": mod_id}

            info = info if info else {"name": mod_id, "packageId": mod_id}
            info['id'] = mod_id
            mod_info_map[mod_id] = info
            print(f"  > 找到Mod: {info['name']} (packageId: {info['packageId']})")

    output_path = OUTPUT_PATH / CONFIG['pack_info']['name'].replace(" ", "_")
    output_path.mkdir(exist_ok=True, parents=True)
    print(f"\n汉化包将生成在: {output_path.resolve()}")

    translation_memory = build_translation_memory(prev_ids, workshop_path)

    print("\n--- 开始“三方校对”翻译流程 ---")
    system_prompt = get_setup_prompt()
    for mod_id, mod_info in mod_info_map.items():
        print(f"\n>>> 正在处理 Mod '{mod_info['name']}'...")
        mod_path = mod_content_path / mod_id
        conversation_history = [
            types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)]),
            types.Content(role="model", parts=[types.Part.from_text(text="好的，我明白了...")])
        ]

        # 收集当前Mod的所有新缓存条目
        current_mod_cache = {}

        cache1 = process_standard_translation(client, conversation_history, mod_path, mod_info, translation_memory,
                                              output_path)
        current_mod_cache.update(cache1)

        cache2 = process_def_injection_translation(client, conversation_history, mod_path, mod_info, translation_memory,
                                                   output_path)
        current_mod_cache.update(cache2)

        # --- 新增：为当前处理的Mod写入新的缓存文件 ---
        if current_mod_cache:
            safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
            cache_file_path = output_path / "Cont" / safe_mod_name / "translation_cache.json"
            cache_file_path.parent.mkdir(exist_ok=True, parents=True)
            with cache_file_path.open('w', encoding='utf-8') as f:
                json.dump(current_mod_cache, f, ensure_ascii=False, indent=4)
            print(f"  -> 已为 Mod '{mod_info['name']}' 生成新的翻译缓存。")

        print(f"<<< Mod '{mod_info['name']}' 处理完毕。")

    # --- 在所有翻译完成后，再生成元数据 ---
    print("\n--- 所有翻译任务完成，正在根据实际产出生成最终元数据 ---")
    cont_dir = output_path / "Cont"
    final_mod_info_map = {}
    if cont_dir.is_dir():
        safe_name_to_info_map = {"".join(c for c in info['name'] if c.isalnum() or c in " .-_").strip(): info for info
                                 in mod_info_map.values()}
        for subdir in cont_dir.iterdir():
            if subdir.is_dir() and subdir.name in safe_name_to_info_map:
                original_info = safe_name_to_info_map[subdir.name]
                final_mod_info_map[original_info['id']] = original_info

    if not final_mod_info_map:
        print("警告: 未生成任何有效的翻译内容，将不创建元数据文件。")
    else:
        print(f"检测到 {len(final_mod_info_map)} 个Mod已成功生成翻译，将为它们创建元数据。")
        create_about_file(output_path, final_mod_info_map)
        create_load_folders_file(output_path, final_mod_info_map)
        create_self_translation(output_path)

    print(f"\n汉化包 '{CONFIG['pack_info']['name']}' 已在以下路径生成完毕: \n{output_path.resolve()}")

def load_config(config_path: Path | str) -> Optional[dict]:
    """加载并合并TOML配置文件。"""

    if not isinstance(config_path, Path):
        config_path = Path(config_path)

    print(f"--- 正在从 {config_path} 加载配置 ---")
    try:
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
    except FileNotFoundError:
        print(f"错误: 配置文件不存在于路径: {config_path}"); sys.exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"错误: 配置文件格式无效: {e}"); sys.exit(1)

    if not user_config.get('enabled', True):
        print(f"配置 '{config_path.name}' 已被禁用(enabled=false)，将跳过。")
        return None

    config = DEFAULT_CONFIG.copy()
    if 'system' in user_config:
        config['system'].update(user_config['system'])

    for section in ['pack_info', 'versions', 'mod_ids', 'rules']:
        if section not in user_config:
            print(f"错误: 配置文件中缺少必需的部分: [{section}]")
            sys.exit(1)
        config[section] = user_config[section]

    print("配置加载成功。")
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RimWorld Mod 自动化翻译脚本。可以处理单个.toml文件或一个包含多个.toml文件的目录。"
    )
    parser.add_argument(
        "config_path",
        type=str,
        help="要使用的项目配置文件(.toml)或包含配置文件的目录的路径"
    )
    args = parser.parse_args()

    # --- 智能路径处理 ---
    input_path = Path(args.config_path)
    toml_files_to_process = []

    if not input_path.exists():
        print(f"错误: 提供的路径不存在: {input_path}")
        sys.exit(1)

    if input_path.is_dir():
        print(f"检测到目录输入，将处理该目录下的所有 .toml 文件...")
        toml_files_to_process = sorted(list(input_path.glob("*.toml")))
        if not toml_files_to_process:
            print(f"警告: 在目录 '{input_path}' 中未找到任何 .toml 配置文件。")
    elif input_path.is_file():
        if input_path.suffix.lower() == ".toml":
            toml_files_to_process.append(input_path)
        else:
            print(f"错误:提供的文件不是 .toml 文件: {input_path}")

    if not toml_files_to_process:
        print("没有找到要处理的配置文件，程序退出。")
        sys.exit(0)

    # --- 批量处理循环 ---
    total_files = len(toml_files_to_process)
    print(f"\n准备开始批量处理，共计 {total_files} 个项目。")

    for i, config_file_path in enumerate(toml_files_to_process, 1):
        print(f"\n{'=' * 25} 开始处理项目 {i}/{total_files} {'=' * 25}")
        config_data = load_config(config_file_path)
        if config_data:
            main(config_data)
        else:
            print(f"跳过项目 {config_file_path.name}。")
        print(f"{'=' * 25} 项目 {config_file_path.name} 处理完毕 {'=' * 25}")
