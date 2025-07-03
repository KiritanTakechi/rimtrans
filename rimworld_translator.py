# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import time
import json

import argparse
import tomllib

from PIL import Image, ImageDraw, ImageFont
from lxml import etree
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

import google.genai as genai
from google.genai import types
from tqdm import tqdm

# --- 全局配置 (请根据你的情况修改) ---
DEFAULT_CONFIG = {
    "system": {
        "steamcmd_path": "./steamcmd/steamcmd.sh",
        "steam_user": "anonymous",
        "steam_password": "",
        "windows_steam_path": "C:/Program Files (x86)/Steam",
        "rimworld_app_id": "294100",
        "gemini_model": "gemini-2.5-flash"
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

# --- Pydantic模型定义 (有修改) ---
class TranslationItem(BaseModel):
    """定义单个翻译条目的数据结构"""
    key: str = Field(description="The original XML tag or injection key. This field MUST NOT be changed or translated.")
    source_text: str = Field(description="The original English text to be translated.")
    translated_text: str = Field(description="The translated Simplified Chinese text. This is the field you need to fill.")

# --- 新增: “包装器” Pydantic 模型 ---
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


def create_placeholder_images(about_dir: Path, mod_name: str, author_name: str):
    """使用Pillow库创建占位符Preview.png和ModIcon.png。"""
    print("正在生成占位符图片...")

    # 尝试加载一个通用字体，如果失败则使用Pillow的默认字体
    try:
        title_font = ImageFont.truetype("arial.ttf", 60)
        subtitle_font = ImageFont.truetype("arial.ttf", 30)
        icon_font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        print("  -> 警告: 未找到Arial字体，将使用Pillow默认字体。图片效果可能不佳。")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        icon_font = ImageFont.load_default()

    # --- 生成 Preview.png ---
    preview_size = (640, 360)
    preview_bg_color = (48, 48, 64)  # 深蓝色背景
    text_color = (255, 255, 255)

    preview_image = Image.new('RGB', preview_size, preview_bg_color)
    draw = ImageDraw.Draw(preview_image)

    # 绘制Mod名称
    title_bbox = draw.textbbox((0, 0), mod_name, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_pos = ((preview_size[0] - title_width) / 2, 120)
    draw.text(title_pos, mod_name, fill=text_color, font=title_font)

    # 绘制作者信息
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

    # 截取Mod名的前几个字母作为图标
    icon_text = "".join([word[0] for word in mod_name.split()[:2]]).upper()
    if not icon_text:
        icon_text = mod_name[0].upper() if mod_name else "T"

    icon_bbox = draw.textbbox((0, 0), icon_text, font=icon_font)
    icon_width = icon_bbox[2] - icon_bbox[0]
    icon_height = icon_bbox[3] - icon_bbox[1]
    icon_pos = ((icon_size[0] - icon_width) / 2, (icon_size[1] - icon_height) / 2)
    draw.text(icon_pos, icon_text, fill=text_color, font=icon_font)

    icon_image.save(about_dir / "ModIcon.png")
    print("  -> 已自动生成 Preview.png 和 ModIcon.png。")


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
    (about_dir / "PublishedFileId.txt").touch()
    print("生成 About/About.xml。")

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
    """在 Mod 目录中查找指定语言的 XML 文件，按“根目录 -> 版本”顺序合并。"""
    found_files = {}  # 使用字典去重并实现覆盖

    # 1. 查找根目录
    root_lang_path = mod_path / "Languages" / lang_folder
    if root_lang_path.is_dir():
        for f in root_lang_path.rglob("*.xml"):
            found_files[f.name] = f

    # 2. 查找所有版本目录，后面的会覆盖前面的
    for version in CONFIG['versions']['targets']:
        version_lang_path = mod_path / version / "Languages" / lang_folder
        if version_lang_path.is_dir():
            for f in version_lang_path.rglob("*.xml"):
                found_files[f.name] = f  # 版本化文件覆盖根文件

    if not found_files:
        for p in mod_path.glob('**/Languages'):
            lang_path = p / lang_folder
            if lang_path.is_dir():
                return sorted(list(lang_path.rglob("*.xml")))

    return sorted(list(found_files.values()))


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


def build_translation_memory(mod_ids: List[str], workshop_path: Path) -> Dict[str, str]:
    """从旧汉化文件中构建翻译记忆库。"""
    if not mod_ids:
        return {}

    print("--- 正在构建翻译记忆库 ---")
    memory = {}
    mod_content_path = workshop_path / CONFIG['system']['rimworld_app_id']

    for mod_id in tqdm(mod_ids, desc="处理旧汉化"):
        mod_path = mod_content_path / mod_id
        if not mod_path.is_dir():
            print(f"警告: 找不到 Mod {mod_id} 的下载目录，跳过。")
            continue

        cn_files = find_language_files(mod_path, "ChineseSimplified")
        for file in cn_files:
            memory.update(load_xml_as_dict(file))

    print(f"构建完成！翻译记忆库包含 {len(memory)} 个条目。\n")
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
            # 返回包装器对象内部的列表
            return response.parsed.translations
        else:
            return None
    except Exception as e:
        print(f"在JSON模式下调用 Gemini 时发生错误: {e}")
        return None


def translate_and_save(client: genai.Client, history: List[types.Content], targets: Dict[str, str],
                       memory: Dict[str, str], output_file_path: Path):
    """通用翻译和保存逻辑 (使用“标记-替换”策略)。"""
    to_translate_dict = {k: v for k, v in targets.items() if k not in memory}
    final_translation_dict = {k: memory[k] for k, v in targets.items() if k in memory}

    if to_translate_dict:
        # 预处理：将\n替换为[BR]标记
        json_items_to_translate = convert_dict_to_json_items(to_translate_dict)
        time.sleep(1)

        parsed_result = translate_with_json_mode(client, history, json_items_to_translate)

        if parsed_result:
            # 后处理：将[BR]标记替换回\n
            translated_dict = convert_parsed_json_to_dict(parsed_result)

            response_for_history = TranslationResponse(translations=parsed_result)
            history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=json.dumps(json_items_to_translate))]))
            history.append(
                types.Content(role="model", parts=[types.Part.from_text(text=response_for_history.model_dump_json())]))

            for key, original_text in to_translate_dict.items():
                if key in translated_dict and translated_dict[key]:
                    final_translation_dict[key] = translated_dict[key]
                else:
                    print(f"  -> 警告: 翻译结果中缺少或为空 <{key}>，将保留英文原文。")
                    final_translation_dict[key] = f"【原文】{original_text}"
        else:
            for key, original_text in to_translate_dict.items():
                final_translation_dict[key] = f"【API错误】{original_text}"

    if not final_translation_dict: return

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    root = etree.Element("LanguageData")
    for key in targets:
        if key in final_translation_dict:
            node = etree.SubElement(root, key)
            node.text = final_translation_dict[key]

    tree = etree.ElementTree(root)
    tree.write(str(output_file_path), encoding='utf-8', xml_declaration=True, pretty_print=True)


def process_standard_translation(client: genai.Client, history: List[types.Content], mod_path: Path, mod_info: Dict, memory: Dict, output_path: Path):
    english_files = find_language_files(mod_path, "English")
    if not english_files: return
    print(f"  -> 找到 {len(english_files)} 个标准语言文件，在当前会话中处理...")
    for file_path in english_files:
        targets = load_xml_as_dict(file_path)
        if not targets: continue
        try:
            english_dir = next(p for p in file_path.parents if p.name == 'English')
            output_relative_path = file_path.relative_to(english_dir)
        except StopIteration: continue
        safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
        output_file_path = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / output_relative_path
        translate_and_save(client, history, targets, memory, output_file_path)


def process_def_injection_translation(client: genai.Client, history: List[types.Content], mod_path: Path,
                                      mod_info: Dict, memory: Dict, output_path: Path):
    """处理Defs/和Patches/文件夹中的注入式翻译。"""

    root_files = []
    version_files = []
    for folder_name in ["Defs", "Patches"]:
        root_path = mod_path / folder_name
        if root_path.is_dir():
            root_files.extend(root_path.rglob("*.xml"))
        # --- 关键修改: 循环所有目标版本 ---
        for version in CONFIG['versions']['targets']:
            version_path = mod_path / version / folder_name
            if version_path.is_dir():
                version_files.extend(version_path.rglob("*.xml"))

    files_to_scan_in_order = root_files + version_files
    if not files_to_scan_in_order: return

    print(f"  -> 找到 {len(files_to_scan_in_order)} 个定义(Defs/Patches)文件，扫描注入点...")

    all_targets_grouped = {}
    parser = etree.XMLParser(remove_blank_text=True, recover=True)

    def find_translatables_in_elements(elements_iterator, source_file_path, group_dict):
        for element in elements_iterator:
            if not isinstance(element.tag, str): continue

            def_type = element.tag
            def_name_node = element.find("defName")
            if def_name_node is None or not def_name_node.text: continue
            def_name = def_name_node.text.strip()

            invalid_chars = ['{', '}', '(', ')', '/']
            if any(char in def_name for char in invalid_chars): continue

            for sub_element in element:
                if isinstance(sub_element.tag, str) and sub_element.tag in CONFIG['rules']['translatable_def_tags'] and sub_element.text:
                    if def_type not in group_dict: group_dict[def_type] = {}
                    source_filename = source_file_path.name
                    if source_filename not in group_dict[def_type]: group_dict[def_type][source_filename] = {}

                    injection_key = f"{def_name}.{sub_element.tag}"
                    group_dict[def_type][source_filename][injection_key] = sub_element.text.strip()

    for file_path in files_to_scan_in_order:
        try:
            tree = etree.parse(str(file_path), parser)
            root = tree.getroot()
            if root is None: continue

            # 对每个文件都统一应用两种解析策略
            # 策略1: 直接解析根节点的子元素 (用于Defs文件)
            find_translatables_in_elements(root, file_path, all_targets_grouped)

            # 策略2: 深度解析<value>节点的子元素 (用于Patches文件)
            for value_node in root.xpath('//value'):
                # 正确的逻辑是遍历<value>的子节点，而不是其.text
                if len(value_node):  # 检查是否存在子节点
                    find_translatables_in_elements(value_node, file_path, all_targets_grouped)

        except etree.XMLSyntaxError as e:
            print(f"警告: lxml解析文件失败，已跳过: {file_path}，错误: {e}")
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


def main(loaded_config: dict):
    """脚本主入口，采用“每Mod一会话(通过手动历史记录)”+“JSON结构化输出”模式。"""
    global CONFIG
    CONFIG = loaded_config

    client = setup_environment()
    workshop_path = get_workshop_content_path()
    prev_ids = parse_ids(CONFIG['mod_ids']['previous'])
    new_ids = parse_ids(CONFIG['mod_ids']['translate'])
    download_with_steamcmd(list(set(prev_ids + new_ids)))

    mod_info_map = {}
    mod_content_path = workshop_path / CONFIG['system']['rimworld_app_id']
    print("\n--- 正在收集待汉化Mod的元数据 ---")
    for mod_id in new_ids:
        mod_path = mod_content_path / mod_id
        if mod_path.is_dir():
            info = get_mod_info(mod_path)
            info = info if info else {"name": mod_id, "packageId": mod_id}
            info['id'] = mod_id
            mod_info_map[mod_id] = info
            print(f"  > 找到Mod: {info['name']} (packageId: {info['packageId']})")

    output_path = OUTPUT_PATH / CONFIG['pack_info']['name'].replace(" ", "_")
    output_path.mkdir(exist_ok=True, parents=True)
    print(f"\n汉化包将生成在: {output_path.resolve()}")

    create_about_file(output_path, mod_info_map)
    create_load_folders_file(output_path, mod_info_map)
    create_self_translation(output_path)

    translation_memory = build_translation_memory(prev_ids, workshop_path)

    print("\n--- 开始“JSON模式+模拟会话”翻译 ---")
    # 系统指令现在只用于构建历史记录的开头
    system_prompt = get_setup_prompt()

    for mod_id, mod_info in mod_info_map.items():
        print(f"\n>>> 正在为 Mod '{mod_info['name']}' 创建新的翻译会话历史...")
        mod_path = mod_content_path / mod_id

        # 为每个Mod创建一个新的、干净的对话历史记录
        # 第一条是系统指令，第二条是模型的确认，模拟对话的开始
        conversation_history = [
            types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)]),
            types.Content(role="model",
                          parts=[types.Part.from_text(text="好的，我明白了这些规则，并已准备好接收JSON格式的翻译请求。")])
        ]

        process_standard_translation(client, conversation_history, mod_path, mod_info, translation_memory, output_path)
        process_def_injection_translation(client, conversation_history, mod_path, mod_info, translation_memory,
                                          output_path)
        print(f"<<< Mod '{mod_info['name']}' 的会话处理完毕。")

    print("\n--- 所有任务完成！---")
    print(f"汉化包 '{CONFIG['pack_info']['name']}' 已在以下路径生成完毕: \n{output_path.resolve()}")
    print("现在您可以将此文件夹移动到您的 RimWorld/Mods 目录进行测试，或上传到Steam创意工坊。")


def load_config(config_path: str) -> dict:
    """加载并合并TOML配置文件。"""
    print(f"--- 正在从 {config_path} 加载配置 ---")
    try:
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
    except FileNotFoundError:
        print(f"错误: 配置文件不存在于路径: {config_path}"); sys.exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"错误: 配置文件格式无效: {e}"); sys.exit(1)

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

    # --- 核心修改：智能路径处理 ---
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
            print(f"跳过项目 {config_file_path.name}，因为配置加载失败。")
        print(f"{'=' * 25} 项目 {config_file_path.name} 处理完毕 {'=' * 25}")
