# -*- coding: utf-8 -*-
import argparse
import json
import os
import random
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont
import google.genai as genai
from google.genai import types
from google.genai.errors import APIError
from lxml import etree
from pydantic import BaseModel, Field
from tqdm import tqdm

# --- 默认配置 ---
# 这些值会在配置文件缺失相应条目时被使用
DEFAULT_CONFIG = {
    "system": {
        "steamcmd_path": "./steamcmd/steamcmd.sh",
        "steam_user": "anonymous",
        "steam_password": "",
        "windows_steam_path": "C:/Program Files (x86)/Steam",
        "rimworld_app_id": "294100",
        "gemini_model": "gemini-1.2-flash-latest",
        "slow_mode": False,
        "slow_mode_delay": 2,
        "helper_files_root": "ProjectHelpers",
        "output_base_dir": "translation_output"
    },
    "ai_settings": {
        "temperature": 0.2,
        "max_retries": 5,
        "retry_delay": 5
    },
    "image_generation": {
        "background_color_hex": "#334155",
        "text_color_hex": "#F8FAFC",
        "subtitle_template": "简体中文汉化 by {author}"
    },
    "generative_rules": {
        "prediction_pattern": "{base_name}{stuff_defName}"
    }
}

# --- 全局变量 ---
BASE_WORKING_DIR: Path = Path(__file__).parent
CONFIG: Dict = {}  # 将由load_config填充

# RimWorld 核心术语表 (可被配置文件覆盖)
RIMWORLD_GLOSSARY = {
    "Addictiveness": "成瘾性", "AI Kassandra": "AI故事叙述者", "AI Persona Core": "人工智能思维核心",
    "AI Storytellers": "AI故事叙述者",
    "Advanced Weapons": "高级武器", "Agave": "龙舌兰果", "Aiming Time": "瞄准时间", "Allowed area": "许可区域",
    "Alpaca": "羊驼",
    "Alpaca wool": "羊驼毛", "Alpacahide": "豚鼠皮", "Alphabeaver": "阿尔法海狸", "Animal": "动物",
    "Animal bed": "动物床铺",
    "Animal sleeping box": "动物睡眠箱", "Animal sleeping spot": "动物睡眠处", "Animals": "动物",
    "Architect Menu": "建造",
    "Arctic fox": "北极狐", "Arctic foxskin": "北极狐皮", "Arctic wolf": "北极狼", "Arctic wolfskin": "北极狼皮",
    "Arid shrubland": "旱带灌木从", "Armchair": "扶手椅", "Armor": "护甲", "Armor Categories": "护甲种类",
    "Arms": "手臂",
    "Artillery shell": "炮弹", "Assault Rifle": "突击步枪", "Assignment": "委派方案", "Auto-turret": "无人机枪",
    "Autodoor": "自动门",
    "Backstories": "背景故事", "Base": "殖民地", "Base Healing Quality": "医疗能力", "Basics": "基础概念",
    "Battery": "蓄电池",
    "Bearskin": "熊皮", "Beauty": "美观", "Beaverskin": "海狸皮", "Bed": "单人床", "Beer": "啤酒", "Berries": "浆果",
    "Billiards table": "台球桌", "Bionic Arm": "仿生臂", "Bionic Eye": "仿生眼", "Bionic Leg": "仿生腿",
    "Birch Tree": "桦树",
    "Blue carpet": "蓝色地毯", "Boar": "野猪", "Body Parts": "身体部位", "Boomalope": "爆炸羊",
    "Boomalope leather": "爆炸兽皮",
    "Boomrat": "爆炸鼠", "Brewery": "酿造台", "Brewing Speed": "酿造速度", "Bush": "灌木", "Butcher table": "屠宰台",
    "Butchery Efficiency": "屠宰效率", "Butchery Speed": "屠宰速度", "Camelhair": "骆驼毛", "Campfire": "篝火",
    "Capybara": "水豚",
    "Capybaraskin": "水豚皮", "Caribou": "驯鹿", "Carpets": "地毯", "Cassandra Classic": "「经典」卡桑德拉",
    "Cassowary": "鹤驼",
    "Centipede": "机械蜈蚣", "Character Types": "生物", "Characters": "角色属性", "Charge Lance": "电荷标枪",
    "Chess table": "象棋桌",
    "Chicken": "鸡", "Chinchilla": "栗鼠", "Chinchilla fur": "粟鼠皮", "Chocolate": "巧克力", "Chop Wood": "伐木",
    "Claim": "占有",
    "Cloth": "布", "Clothing": "衣服", "Club": "棍棒", "Cobra": "眼镜蛇", "Colonist": "殖民者", "Colonists": "殖民者",
    "Colony": "殖民地", "Combat": "战斗", "Comfort": "舒适", "Comms console": "通讯台",
    "Construction Speed": "建造速度",
    "Controls": "操作控制", "Cook stove": "电动炉灶", "Cooking Speed": "烹饪速度", "Cooler": "制冷机", "Corn": "玉米",
    "Cotton Plant": "棉花（植株）", "Cougar": "美洲豹", "Cover": "掩护", "Cow": "奶牛", "Crafting spot": "加工点",
    "Crematorium": "焚化炉", "Cryptosleep casket": "低温休眠舱", "Damage": "伤害", "Damage Types": "伤害类型",
    "DPS": "DPS",
    "Daylily": "金针莱", "Deadfall trap": "尖刺陷阱", "Debris": "碎石", "Deconstruct": "拆除", "Deer": "鹿",
    "Deterioration": "变质", "Devilstrand": "魔菇布", "Dining chair": "餐椅", "Disease": "疾病", "Door": "门",
    "EMP Grenade": "EMP手榴弹", "Eating Speed": "进食速度", "Electric crematorium": "焚化炉",
    "Electric smelter": "电动熔炼机",
    "Electric smithy": "电动锻造台", "Electric tailoring bench": "电动裁缝台", "Elephant": "大象", "Emu": "鸸鹋",
    "Environment": "环境", "Events": "特殊事件", "Fabric": "纤维", "Fabrics": "纤维", "Feet": "脚部",
    "Fine Meal": "精致食物",
    "Fire": "火", "Firefighting": "灭火", "Firefoam popper": "泡沫灭火器", "Flammability": "易燃性", "Floor": "地板",
    "Food": "食物", "Food Poison Chance": "烹饪生毒几率", "Frag Grenades": "破片手榴弹", "Fueled smithy": "燃料锻造台",
    "Furniture": "家具", "Gameplay": "游戏机制", "Gazelle": "瞪羚", "Geothermal Generator": "地热发电机",
    "Gladius": "短剑",
    "Glitterworld": "闪耀世界", "Glitterworld Medicine": "高级药物", "Global Learning Factor": "全局学习能力",
    "Global Work Speed": "全局工作速度", "Gold": "黄金", "Granite Blocks": "花岗岩砖块", "Grass": "草", "Grave": "坟墓",
    "Great Bow": "长弓", "Grizzly Bear": "灰熊", "Growing Zone": "种植区", "Hand-tailoring bench": "手工缝纫台",
    "Hands": "双手", "Happiness": "幸福", "Hare": "野兔", "Haul Things": "搬运", "Hauling": "搬运", "Hay": "干草",
    "Healing Speed": "医疗速度", "Healroot": "药草", "Health": "健康", "Heart": "心脏", "Heater": "加热器",
    "Heavy SMG": "重型冲锋枪", "Herbal Medicine": "草药", "Home Region": "居住区", "Home Zone": "居住区",
    "Hop Plant": "啤酒花（植株）", "Hopper": "进料口", "Hops": "啤酒花", "Horseshoe pins": "掷马蹄铁",
    "Hospital bed": "病床",
    "Human": "人类", "Human leather": "人皮", "Hunt": "狩猎", "Husky": "哈士奇犬", "Hydroponics basin": "无土栽培皿",
    "Hyperweave": "超织物", "IED trap": "自制炸弹陷阱", "Ibex": "野山羊", "Iguana": "鬣蜥",
    "Immunity Gain Speed": "免疫力获得速度",
    "Improvised Turret": "简易机枪", "Incendiary Mortar": "燃烧弹迫击炮", "Inferno Cannon": "地狱火加农炮",
    "Injury": "伤势",
    "Jade": "翡翠", "Joy": "娱乐", "Kidney": "肾", "Knife": "匕首", "LMG": "轻机枪",
    "Labrador retriever": "拉布拉多猎犬",
    "Large Sculpture": "大雕塑", "Lavish Meal": "奢侈食物", "Leather": "皮革", "Leathers": "皮革", "Legs": "腿部",
    "Limestone Blocks": "石灰岩砖块", "Liver": "肝", "Log wall": "木墙", "Long Sword": "长剑", "Lung": "肺",
    "Machining table": "机械加工台", "Marble Blocks": "大理石砖", "Market Value": "市场价值", "Material": "材质",
    "Materials": "材质", "Max Hit Points": "最大耐久度", "Meal": "熟食", "Meals": "熟食", "Meat": "肉类",
    "Mechanoid": "机械体", "Mechanoid Centipede": "机械蜈蚣", "Mechanoid Scyther": "机械螳螂", "Mechanoids": "机械体",
    "Medical Items": "医疗用品", "Medical Operation Speed": "手术速度", "Medical Potency": "医用效果",
    "Medicine": "药物",
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
    "Zone": "区域", "pawn": "殖民者", "raid": "袭击", "bundle": "捆堆", "pile": "织物"
}

# 基础材质库 (可被配置文件扩展)
VANILLA_STUFFS = {
    "Woody": [
        {"defName": "WoodLog", "label_en": "wooden", "label_cn": "木制"}
    ],
    "Stony": [
        {"defName": "BlocksSandstone", "label_en": "sandstone", "label_cn": "砂岩"},
        {"defName": "BlocksGranite", "label_en": "granite", "label_cn": "花岗岩"},
        {"defName": "BlocksLimestone", "label_en": "limestone", "label_cn": "石灰岩"},
        {"defName": "BlocksSlate", "label_en": "slate", "label_cn": "板岩"},
        {"defName": "BlocksMarble", "label_en": "marble", "label_cn": "大理石"}
    ],
    "Metallic": [
        {"defName": "Steel", "label_en": "steel", "label_cn": "钢铁"},
        {"defName": "Plasteel", "label_en": "plasteel", "label_cn": "玻璃钢"},
        {"defName": "Gold", "label_en": "gold", "label_cn": "黄金"},
        {"defName": "Silver", "label_en": "silver", "label_cn": "白银"},
        {"defName": "Uranium", "label_en": "uranium", "label_cn": "铀"}
    ]
}


# --- Pydantic模型定义 ---
class TranslationItem(BaseModel):
    key: str = Field(description="The original XML tag or injection key. This field MUST NOT be changed or translated.")
    source_text: str = Field(description="The original English text to be translated.")
    translated_text: str = Field(
        description="The translated Simplified Chinese text. This is the field you need to fill.")
    context_info: Optional[str] = Field(None, description="Contextual information for more accurate translation.")


class TranslationResponse(BaseModel):
    translations: List[TranslationItem] = Field(description="A list of all the translated items.")


# --- 核心函数 ---

def get_workshop_content_path() -> Path:
    platform = sys.platform
    home = Path.home()
    steam_path_str = CONFIG['system'].get('windows_steam_path', DEFAULT_CONFIG['system']['windows_steam_path'])

    if platform == "win32":
        path = Path(steam_path_str) / "steamapps" / "workshop" / "content"
    elif platform == "darwin":
        path = home / "Library/Application Support/Steam/steamapps/workshop/content"
    else:  # linux
        path1 = home / ".steam/steam/steamapps/workshop/content"
        path2 = home / ".local/share/Steam/steamapps/workshop/content"
        path = path1 if path1.exists() else path2

    print(f"检测到系统平台: {platform}, 将在此路径查找 Mod: {path}")
    if not path.exists():
        print(f"警告: 自动检测到的 Steam Workshop 路径不存在。请确保 Steam 已安装且路径正确。")
    return path


def setup_environment():
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

    # 输出目录的创建移至main函数，因为它依赖于每个项目的配置
    return client


def parse_ids(id_string: str) -> List[str]:
    if not id_string: return []
    return [item.strip() for item in id_string.split(',') if item.strip()]


def download_with_steamcmd(mod_ids: List[str]):
    if not mod_ids: return
    print(f"--- 开始使用 SteamCMD 下载 {len(mod_ids)} 个 Mod ---")

    steamcmd_path = CONFIG['system']['steamcmd_path']
    steam_user = CONFIG['system']['steam_user']
    steam_password = CONFIG['system']['steam_password']
    rimworld_app_id = CONFIG['system']['rimworld_app_id']

    command = [steamcmd_path, "+login", steam_user, steam_password]
    for mod_id in mod_ids:
        print(f"准备下载 Mod ID: {mod_id}")
        command.extend(["+workshop_download_item", rimworld_app_id, mod_id])
    command.append("+quit")

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   encoding='utf-8')
        with tqdm(total=len(mod_ids), desc="SteamCMD 下载中", unit="item") as pbar:
            for line in process.stdout:
                if "Success. Downloaded item" in line:
                    pbar.update(1)
        process.wait()
        if process.returncode != 0:
            print(f"\n警告: SteamCMD 进程以非零代码 {process.returncode} 退出。")
        else:
            print("\n所有 Mod 下载任务已提交。")
    except FileNotFoundError:
        print(f"错误: 无法执行 SteamCMD。路径 '{steamcmd_path}' 是否正确？")
        sys.exit(1)
    except Exception as e:
        print(f"SteamCMD 执行时发生未知错误: {e}")
        sys.exit(1)
    print("--- 下载完成 ---\n")


def get_mod_info(mod_path: Path) -> Optional[Dict[str, str]]:
    about_file = mod_path / "About" / "About.xml"
    if not about_file.is_file(): return None
    try:
        tree = etree.parse(str(about_file))
        name = tree.findtext("name", default=mod_path.name).strip()
        author = tree.findtext("author", default="UnknownAuthor").strip()
        package_id_text = tree.findtext("packageId")

        def sanitize(text: str) -> str:
            return "".join(c for c in text if c.isalnum() or c == '_')

        if package_id_text:
            package_id = package_id_text.strip().lower()
        else:
            package_id = f"{sanitize(author)}.{sanitize(name)}".lower()

        return {"name": name, "packageId": package_id}
    except etree.XMLSyntaxError:
        return None


def create_placeholder_images(about_dir: Path):
    """根据配置创建占位符图片。"""
    print("正在生成占位符图片...")
    img_config = CONFIG.get('image_generation', DEFAULT_CONFIG['image_generation'])
    author_name = CONFIG['pack_info']['author']
    mod_name = CONFIG['pack_info']['name']

    bg_color = img_config['background_color_hex']
    text_color = img_config['text_color_hex']
    subtitle_template = img_config['subtitle_template']
    subtitle_text = subtitle_template.format(author=author_name)

    font_path = BASE_WORKING_DIR / "assets" / "Inter-Regular.ttf"

    def get_font(size: int, default_size: int = 20):
        try:
            return ImageFont.truetype(str(font_path), size) if font_path.is_file() else ImageFont.load_default(
                size=default_size)
        except Exception:
            return ImageFont.load_default(size=default_size)

    # --- Preview.png ---
    preview_size = (640, 360)
    preview_image = Image.new('RGB', preview_size, bg_color)
    draw = ImageDraw.Draw(preview_image)

    font_size = 60
    padding = 40
    while font_size > 10:
        title_font = get_font(font_size, 30)
        title_bbox = draw.textbbox((0, 0), mod_name, font=title_font)
        if (title_bbox[2] - title_bbox[0]) < preview_size[0] - padding:
            break
        font_size -= 2

    title_bbox = draw.textbbox((0, 0), mod_name, font=title_font)
    title_pos = ((preview_size[0] - (title_bbox[2] - title_bbox[0])) / 2, 140 - ((title_bbox[3] - title_bbox[1]) / 2))
    draw.text(title_pos, mod_name, fill=text_color, font=title_font)

    subtitle_font = get_font(30, 15)
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    subtitle_pos = ((preview_size[0] - (subtitle_bbox[2] - subtitle_bbox[0])) / 2, 220)
    draw.text(subtitle_pos, subtitle_text, fill=(200, 200, 200), font=subtitle_font)
    preview_image.save(about_dir / "Preview.png")

    # --- ModIcon.png ---
    icon_size = (256, 256)
    icon_image = Image.new('RGB', icon_size, bg_color)
    draw = ImageDraw.Draw(icon_image)
    icon_text = "".join([word[0] for word in mod_name.split()[:2]]).upper() or (
        mod_name[0].upper() if mod_name else "T")
    icon_font = get_font(120, 40)
    icon_bbox = draw.textbbox((0, 0), icon_text, font=icon_font)
    icon_pos = ((icon_size[0] - (icon_bbox[2] - icon_bbox[0])) / 2,
                (icon_size[1] - (icon_bbox[3] - icon_bbox[1])) / 2 * 0.9)
    draw.text(icon_pos, icon_text, fill=text_color, font=icon_font)
    icon_image.save(about_dir / "ModIcon.png")
    print("  -> 已根据配置生成 Preview.png 和 ModIcon.png。")


def create_about_file(output_path: Path, mod_info_map: Dict[str, dict]):
    about_dir = output_path / "About"
    about_dir.mkdir(exist_ok=True, parents=True)
    root = etree.Element("ModMetaData")

    etree.SubElement(root, "name").text = CONFIG['pack_info']['name']
    etree.SubElement(root, "author").text = CONFIG['pack_info']['author']

    supported_versions_node = etree.SubElement(root, "supportedVersions")
    for version in CONFIG['versions']['targets']:
        etree.SubElement(supported_versions_node, "li").text = version

    package_id = f"{CONFIG['pack_info']['author'].replace(' ', '')}.{CONFIG['pack_info']['name'].replace(' ', '')}"
    etree.SubElement(root, "packageId").text = package_id

    supported_mods_list = "\n".join([f"  - {info['name']}" for info in mod_info_map.values()])
    etree.SubElement(root, "description").text = CONFIG['pack_info']['description'] + supported_mods_list

    load_after_node = etree.SubElement(root, "loadAfter")
    for mod_info in mod_info_map.values():
        etree.SubElement(load_after_node, "li").text = mod_info['packageId']

    tree = etree.ElementTree(root)
    tree.write(str(about_dir / "About.xml"), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print("已生成 About/About.xml。")

    published_file_id_path = about_dir / "PublishedFileId.txt"
    prev_ids = parse_ids(CONFIG['mod_ids'].get('previous', ''))
    if prev_ids:
        published_file_id_path.write_text(prev_ids[0].strip())
        print(f"检测到 'previous' ID，已将 {prev_ids[0]} 写入 PublishedFileId.txt 用于更新。")
    else:
        published_file_id_path.touch()
        print("未提供 'previous' ID，已创建空的 PublishedFileId.txt 用于首次上传。")
    create_placeholder_images(about_dir)


def create_load_folders_file(output_path: Path, mod_info_map: Dict[str, dict]):
    root = etree.Element("loadFolders")
    for version in CONFIG['versions']['targets']:
        version_node = etree.SubElement(root, f"v{version}")
        for mod_info in mod_info_map.values():
            safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
            li_node = etree.SubElement(version_node, "li")
            li_node.set("IfModActive", mod_info['packageId'])
            li_node.text = f"Cont/{safe_mod_name}"
    tree = etree.ElementTree(root)
    tree.write(str(output_path / "LoadFolders.xml"), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print("生成 LoadFolders.xml。")


def create_self_translation(output_path: Path):
    lang_dir = output_path / "Languages" / "ChineseSimplified" / "Keyed"
    lang_dir.mkdir(parents=True, exist_ok=True)
    root = etree.Element("LanguageData")
    tag_name = f"{CONFIG['pack_info']['author'].replace(' ', '')}.{CONFIG['pack_info']['name'].replace(' ', '')}.ModName"
    etree.SubElement(root, tag_name).text = CONFIG['pack_info']['name']
    tree = etree.ElementTree(root)
    tree.write(str(lang_dir / "SelfTranslation.xml"), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print("为汉化包创建自翻译文件。")


def load_xml_as_dict(file_path: Path) -> Dict[str, str]:
    translations = {}
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(str(file_path), parser)
        for elem in tree.getroot():
            if isinstance(elem.tag, str) and elem.text:
                translations[elem.tag] = elem.text.strip()
    except etree.XMLSyntaxError as e:
        print(f"警告: lxml解析文件失败: {file_path}, 错误: {e}")
    return translations


def find_source_files(mod_path: Path, target_subfolders: List[str]) -> List[Path]:
    found_files_map = {}
    load_folders_file = mod_path / "LoadFolders.xml"
    content_folders_in_order = []

    if load_folders_file.is_file():
        try:
            tree = etree.parse(str(load_folders_file))
            versions = [""] + CONFIG['versions']['targets']
            for version in versions:
                xpath_query = f'/loadFolders/li/text()' if not version else f'//v{version}/li/text()'
                for path_str in tree.xpath(xpath_query):
                    cleaned_path = path_str.strip().replace('\\', '/')
                    full_path = mod_path if cleaned_path == '/' else mod_path / cleaned_path
                    if full_path not in content_folders_in_order:
                        content_folders_in_order.append(full_path)
        except etree.XMLSyntaxError:
            content_folders_in_order = []

    if not content_folders_in_order:
        print(f"  -> 未找到或无法解析LoadFolders.xml, 将在默认路径中扫描。")
        content_folders_in_order.append(mod_path)
        for version in CONFIG['versions']['targets']:
            version_path = mod_path / version
            if version_path.is_dir():
                content_folders_in_order.append(version_path)

    for content_path in content_folders_in_order:
        if not content_path.is_dir(): continue
        for target in target_subfolders:
            search_path = content_path / target
            if search_path.is_dir():
                for f in search_path.rglob("*.xml"):
                    unique_key = f.relative_to(mod_path)
                    found_files_map[unique_key] = f
    return sorted(list(found_files_map.values()))


def build_translation_memory(prev_ids: List[str], workshop_path: Path) -> Dict[str, dict]:
    if not prev_ids: return {}
    print("--- 正在构建三方校对记忆库 ---")
    memory = {}
    mod_content_path = workshop_path / CONFIG['system']['rimworld_app_id']
    for mod_id in tqdm(prev_ids, desc="扫描旧汉化包"):
        mod_path = mod_content_path / mod_id
        if not mod_path.is_dir():
            print(f"\n警告: 找不到Mod {mod_id}，跳过。")
            continue
        for file_path in mod_path.rglob("translation_cache.json"):
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    memory.update(json.load(f))
            except (json.JSONDecodeError, IOError) as e:
                print(f"  -> 警告: 读取或解析缓存文件失败: {file_path}, 错误: {e}")
    print(f"\n构建完成！翻译记忆库包含 {len(memory)} 个条目。\n")
    return memory


def get_setup_prompt() -> str:
    base_system_prompt = """你是一个为游戏《边缘世界》(RimWorld) 设计的专业级翻译引擎。你的任务是将用户提供的JSON对象中的 `source_text` 字段翻译成简体中文，并填入 `translated_text` 字段。
请严格遵守以下规则：
1.  **保持键值不变**: 绝对不要修改 `key`、`source_text` 或 `context_info` 字段。
2.  **精准翻译**: 确保翻译内容符合《边缘世界》的语境。
3.  **利用上下文**: 如果提供了 `context_info` 字段，你必须参考它来生成更地道的翻译。例如，如果 `source_text` 是 "Bundle A"，而 `context_info` 包含 "Leathery"，你应该倾向于翻译成“A型皮革捆堆”或“A型皮革捆包”，而不是简单的“A型捆堆”。
4.  **返回完整JSON**: 你的输出必须是完整的、包含所有原始条目的JSON数组。
5.  **处理换行符标记**: 文本中的 `[BR]` 标记是换行符占位符，必须在译文中原样保留。"""
    glossary_prompt_part = "6. **术语统一**: 这是最重要的规则。请严格参考以下术语表进行翻译...\n"
    glossary_items = [f"- '{en.lower()}': '{cn}'" for en, cn in RIMWORLD_GLOSSARY.items()]
    glossary_prompt_part += "\n".join(glossary_items)
    return f"{base_system_prompt}\n\n{glossary_prompt_part}\n\n我明白了这些规则，请开始提供需要翻译的JSON内容。"


def convert_dict_to_json_items(data: Dict[str, dict]) -> List[Dict[str, str]]:
    items = []
    for k, v_dict in data.items():
        items.append({
            "key": k,
            "source_text": v_dict['text'].replace('\\n', '[BR]').replace('\n', '[BR]'),
            "translated_text": "",
            "context_info": v_dict.get('context')
        })
    return items


def convert_parsed_json_to_dict(parsed_items: List[TranslationItem]) -> Dict[str, str]:
    final_dict = {}
    for item in parsed_items:
        normalized_text = item.translated_text.replace('[BR]', '\\n').replace('\n', '\\n')
        final_dict[item.key] = normalized_text
    return final_dict


def translate_with_json_mode(client: genai.Client, history: List[types.Content],
                             items_to_translate: List[Dict[str, str]]) -> Optional[List[TranslationItem]]:
    user_prompt = f"请翻译以下JSON数组中的条目:\n{json.dumps(items_to_translate, indent=2, ensure_ascii=False)}"
    current_contents = history + [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]

    ai_config = CONFIG.get('ai_settings', DEFAULT_CONFIG['ai_settings'])
    max_retries = ai_config['max_retries']
    base_delay = ai_config['retry_delay']
    temperature = ai_config['temperature']

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=CONFIG['system']['gemini_model'],
                contents=current_contents,
                # 这是JSON模式的核心配置
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TranslationResponse,
                    temperature=temperature
                )
            )
            if hasattr(response, 'parsed') and response.parsed is not None:
                return response.parsed.translations
            else:
                print("  -> 警告: API返回了空结果，可能是因为安全设置。")
                return None

        except APIError as e:
            if e.code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"\n  -> 警告: 触发API频率限制。将在 {delay:.1f} 秒后重试 (第 {attempt + 1}/{max_retries} 次)...")
                time.sleep(delay)
            else:
                print(f"在JSON模式下调用 Gemini 时发生API错误: {e}")
                return None
        except Exception as e:
            # 捕获和报告解析错误
            print(f"在JSON模式下调用或解析Gemini响应时发生未知错误: {e}")
            return None

    print(f"  -> 错误: 重试 {max_retries} 次后仍失败。")
    return None


def translate_and_save(client: genai.Client, history: List[types.Content], targets: Dict[str, dict],
                       memory: Dict[str, dict], output_file_path: Path) -> Dict[str, dict]:
    ERROR_PREFIX, ORIGINAL_PREFIX = "【API错误】", "【原文】"
    to_translate_dict, final_translation_dict, new_cache_data = {}, {}, {}

    for key, new_data in targets.items():
        new_en_text = new_data['text']
        new_context = new_data.get('context')
        if key in memory:
            old_data = memory[key]
            is_en_text_same = new_en_text == old_data.get('en', '')
            is_context_same = new_context == old_data.get('context')
            is_cn_text_valid = not (isinstance(old_data.get('cn'), str) and (
                        old_data['cn'].startswith(ERROR_PREFIX) or old_data['cn'].startswith(ORIGINAL_PREFIX)))
            if is_en_text_same and is_context_same and is_cn_text_valid:
                final_translation_dict[key] = old_data['cn']
                new_cache_data[key] = {'en': new_en_text, 'cn': old_data['cn'], 'context': new_context}
                continue
        to_translate_dict[key] = new_data

    if to_translate_dict:
        if CONFIG['system'].get('slow_mode', False): time.sleep(CONFIG['system'].get('slow_mode_delay', 2))
        json_items_to_translate = convert_dict_to_json_items(to_translate_dict)
        parsed_result = translate_with_json_mode(client, history, json_items_to_translate)

        if parsed_result:
            translated_dict = convert_parsed_json_to_dict(parsed_result)
            response_for_history = TranslationResponse(translations=parsed_result)
            history.append(types.Content(role="user", parts=[
                types.Part.from_text(text=json.dumps(json_items_to_translate, ensure_ascii=False))]))
            history.append(types.Content(role="model", parts=[
                types.Part.from_text(text=response_for_history.model_dump_json(indent=2))]))

            for key, original_data in to_translate_dict.items():
                translated_text = translated_dict.get(key, f"{ORIGINAL_PREFIX}{original_data['text']}")
                final_translation_dict[key] = translated_text
                new_cache_data[key] = {'en': original_data['text'], 'cn': translated_text,
                                       'context': original_data.get('context')}
        else:  # API call or parsing failed
            for key, original_data in to_translate_dict.items():
                error_text = f"{ERROR_PREFIX}{original_data['text']}"
                final_translation_dict[key] = error_text
                new_cache_data[key] = {'en': original_data['text'], 'cn': error_text,
                                       'context': original_data.get('context')}

    if not final_translation_dict: return {}

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    root = etree.Element("LanguageData")
    for key, value in sorted(final_translation_dict.items()):
        etree.SubElement(root, key).text = value
    tree = etree.ElementTree(root)
    tree.write(str(output_file_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    return new_cache_data


def process_standard_translation(client: genai.Client, history: List[types.Content], mod_path: Path, mod_info: Dict,
                                 memory: Dict, output_path: Path) -> Dict[str, dict]:
    print(f"  -> 开始进行标准接口翻译...")
    mod_cache = {}
    english_files = find_source_files(mod_path, ["Languages/English"])
    if not english_files: return mod_cache

    print(f"  -> 找到 {len(english_files)} 个标准语言文件...")
    for file_path in english_files:
        simple_targets = load_xml_as_dict(file_path)
        if not simple_targets: continue
        nested_targets = {key: {"text": text, "context": None} for key, text in simple_targets.items()}

        try:
            output_relative_path = file_path.relative_to(next(p for p in file_path.parents if p.name == 'English'))
        except StopIteration:
            continue

        safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
        output_file = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / output_relative_path

        new_cache_entries = translate_and_save(client, history, nested_targets, memory, output_file)
        mod_cache.update(new_cache_entries)
    return mod_cache


def process_def_injection_translation(client: genai.Client, history: List[types.Content], mod_path: Path,
                                      mod_info: Dict, memory: Dict, output_path: Path, abstract_defs: Dict,
                                      def_inheritance_map: Dict) -> Dict[str, dict]:
    print(f"  -> 开始进行注入式翻译...")

    helper_dir = CONFIG.get('system', {}).get('helper_files_root', DEFAULT_CONFIG['system']['helper_files_root'])
    files_to_scan = find_source_files(mod_path, ["Defs", "Patches", helper_dir])
    if not files_to_scan: return {}

    print(f"  -> 找到 {len(files_to_scan)} 个定义/补丁/辅助文件, 开始解析...")
    all_targets_grouped = {}
    parser = etree.XMLParser(remove_blank_text=True, recover=True)

    for file_path in files_to_scan:
        try:
            tree = etree.parse(str(file_path), parser)
            for element in tree.xpath('//ThingDef'):
                fields = {}
                for sub in element:
                    if isinstance(sub.tag, str) and sub.tag in CONFIG['rules']['translatable_def_tags'] and sub.text:
                        fields[sub.tag] = sub.text.strip()

                current_parent_name = element.get("ParentName")
                visited_parents = set()
                while current_parent_name and current_parent_name not in visited_parents:
                    visited_parents.add(current_parent_name)
                    if current_parent_name in abstract_defs:
                        for tag, text in abstract_defs[current_parent_name].items():
                            if tag not in fields: fields[tag] = text
                    current_parent_name = def_inheritance_map.get(current_parent_name)

                if not fields: continue

                is_abstract = element.get("Abstract", "False").lower() == 'true'
                stuff_category_names = element.xpath("stuffCategories/li/text()")
                def_type = element.tag
                filename = file_path.name

                if def_type not in all_targets_grouped: all_targets_grouped[def_type] = {}
                if filename not in all_targets_grouped[def_type]: all_targets_grouped[def_type][filename] = {}

                if not is_abstract:
                    def_name_node = element.find("defName")
                    if def_name_node is not None and def_name_node.text:
                        base_name = def_name_node.text.strip()
                        context = None
                        if stuff_category_names:
                            context = f"This is a blueprint for an item that can be made from various materials in categories like {', '.join(stuff_category_names)}. Provide a generic translation for the base item."
                        for tag, text in fields.items():
                            key = f"{base_name}.{tag}"
                            all_targets_grouped[def_type][filename][key] = {"text": text, "context": context}
                elif is_abstract and stuff_category_names:
                    base_name_for_generation = element.get("Name")
                    if not base_name_for_generation: continue

                    pattern = CONFIG.get('generative_rules', {}).get('prediction_pattern',
                                                                     DEFAULT_CONFIG['generative_rules'][
                                                                         'prediction_pattern'])

                    for cat_name in stuff_category_names:
                        cat_name = cat_name.strip()
                        if cat_name in VANILLA_STUFFS:
                            for stuff in VANILLA_STUFFS[cat_name]:
                                generated_def_name = pattern.format(base_name=base_name_for_generation,
                                                                    stuff_defName=stuff['defName'])
                                context = f"An item generated from the abstract base '{base_name_for_generation}', made from material '{stuff['label_en']}'. The Chinese name for the material is '{stuff['label_cn']}'."
                                for tag, text in fields.items():
                                    key = f"{generated_def_name}.{tag}"
                                    all_targets_grouped[def_type][filename][key] = {"text": text, "context": context}
        except etree.XMLSyntaxError:
            continue

    if not all_targets_grouped:
        print("  -> 未找到可供注入翻译的条目。")
        return {}

    safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
    mod_cache = {}
    for def_type, files in all_targets_grouped.items():
        for filename, targets in files.items():
            if not targets: continue
            print(f"    -> 正在处理来自 {filename} 的 {len(targets)} 个 {def_type} 条目")
            output_dir = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / "DefInjected" / def_type
            output_file_path = output_dir / filename
            new_cache_entries = translate_and_save(client, history, targets, memory, output_file_path)
            mod_cache.update(new_cache_entries)
    return mod_cache


def main(config: dict):
    global CONFIG
    CONFIG = config

    # --- 应用自定义配置 ---
    custom_glossary = CONFIG.get('custom_glossary', {})
    if custom_glossary:
        RIMWORLD_GLOSSARY.update(custom_glossary)
        print(f"自定义术语表已加载，共更新/添加 {len(custom_glossary)} 个术语。")

    custom_stuff_list = CONFIG.get('generative_rules', {}).get('custom_stuff', [])
    if custom_stuff_list:
        count = 0
        for stuff in custom_stuff_list:
            category = stuff.get('category')
            if category:
                if category not in VANILLA_STUFFS: VANILLA_STUFFS[category] = []
                VANILLA_STUFFS[category].append(stuff)
                count += 1
        print(f"自定义材质库已加载，共添加 {count} 种新材质。")

    # --- 正常流程 ---
    client = setup_environment()
    workshop_path = get_workshop_content_path()
    prev_ids = parse_ids(CONFIG['mod_ids'].get('previous', ''))
    new_ids = parse_ids(CONFIG['mod_ids']['translate'])
    if not new_ids:
        print("警告: 'translate' 列表为空，无可翻译的Mod。")
        return

    all_mod_ids = list(set(prev_ids + new_ids))
    download_with_steamcmd(all_mod_ids)

    mod_info_map = {}
    mod_content_path = workshop_path / CONFIG['system']['rimworld_app_id']
    print("\n--- 正在收集待汉化Mod的元数据 ---")
    for mod_id in new_ids:
        mod_path = mod_content_path / mod_id
        if mod_path.is_dir():
            info = get_mod_info(mod_path)
            if not info: info = {"name": mod_id, "packageId": mod_id}
            info['id'] = mod_id
            mod_info_map[mod_id] = info
            print(f"  > 找到Mod: {info['name']} (packageId: {info['packageId']})")

    output_base_dir = CONFIG.get('system', {}).get('output_base_dir', 'translation_output')
    output_path = BASE_WORKING_DIR / output_base_dir / CONFIG['pack_info']['name'].replace(" ", "_")
    output_path.mkdir(exist_ok=True, parents=True)
    print(f"\n汉化包将生成在: {output_path.resolve()}")

    # --- 全局学习阶段 ---
    print("\n--- 全局学习阶段: 扫描所有目标Mod以构建知识库 ---")
    abstract_defs, def_inheritance_map = {}, {}
    parser = etree.XMLParser(remove_blank_text=True, recover=True)

    # 获取辅助文件根目录的配置
    helper_root_path_str = CONFIG.get('system', {}).get('helper_files_root')
    helper_root_path = BASE_WORKING_DIR / helper_root_path_str if helper_root_path_str else None

    for mod_id in tqdm(new_ids, desc="构建全局知识库"):
        mod_path = mod_content_path / mod_id

        # 【核心修改】在这里组合来自Mod下载目录和项目辅助目录的文件列表
        files_to_scan = find_source_files(mod_path, ["Defs", "Patches"])

        if helper_root_path and helper_root_path.is_dir():
            mod_helper_path = helper_root_path / mod_id
            if mod_helper_path.is_dir():
                helper_files = list(mod_helper_path.rglob("*.xml"))
                if helper_files:
                    print(f"\n  -> 为Mod {mod_id} 找到 {len(helper_files)} 个辅助文件。")
                    files_to_scan.extend(helper_files)

        for file_path in files_to_scan:
            try:
                tree = etree.parse(str(file_path), parser)
                for element in tree.xpath('//*[self::Defs or self::Patch]/*|//value/*'):
                    if not isinstance(element.tag, str): continue
                    current_name_node = element.find("defName")
                    current_name = current_name_node.text.strip() if current_name_node is not None and current_name_node.text else element.get(
                        "Name")
                    parent_name = element.get("ParentName")
                    if current_name and parent_name:
                        def_inheritance_map[current_name] = parent_name.strip()
                    if element.get("Abstract", "False").lower() == 'true' and element.get("Name"):
                        template_name = element.get("Name")
                        if template_name not in abstract_defs: abstract_defs[template_name] = {}
                        for sub in element:
                            if isinstance(sub.tag, str) and sub.tag in CONFIG['rules'][
                                'translatable_def_tags'] and sub.text:
                                abstract_defs[template_name][sub.tag] = sub.text.strip()
            except etree.XMLSyntaxError:
                continue
    print(f"  -> 全局知识库构建完毕，包含 {len(abstract_defs)} 个抽象模板。")

    translation_memory = build_translation_memory(prev_ids, workshop_path)

    # --- 翻译阶段 ---
    print("\n--- 开始“三方校对”翻译流程 ---")
    system_prompt = get_setup_prompt()
    for mod_id, mod_info in mod_info_map.items():
        print(f"\n>>> 正在处理 Mod '{mod_info['name']}' ({mod_id})...")
        mod_path = mod_content_path / mod_id
        conversation_history = [
            types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)]),
            types.Content(role="model", parts=[types.Part.from_text(text="好的，我明白了，请提供需要翻译的内容。")])
        ]
        current_mod_cache = {}
        cache1 = process_standard_translation(client, conversation_history, mod_path, mod_info, translation_memory,
                                              output_path)
        current_mod_cache.update(cache1)

        # 注意：这里的 process_def_injection_translation 函数现在会处理来自辅助文件的内容了
        cache2 = process_def_injection_translation(client, conversation_history, mod_path, mod_info, translation_memory,
                                                   output_path, abstract_defs, def_inheritance_map)
        current_mod_cache.update(cache2)

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
    final_mod_info_map = {info['id']: info for subdir in cont_dir.iterdir() if subdir.is_dir() for info in
                          mod_info_map.values() if
                          "".join(c for c in info['name'] if c.isalnum() or c in " .-_").strip() == subdir.name}

    if not final_mod_info_map:
        print("警告: 未生成任何有效的翻译内容，将不创建元数据文件。")
    else:
        print(f"检测到 {len(final_mod_info_map)} 个Mod已成功生成翻译，将为它们创建元数据。")
        create_about_file(output_path, final_mod_info_map)
        create_load_folders_file(output_path, final_mod_info_map)
        create_self_translation(output_path)

    print(f"\n汉化包 '{CONFIG['pack_info']['name']}' 已在以下路径生成完毕: \n{output_path.resolve()}")


def load_config(config_path: Path | str) -> Optional[dict]:
    if not isinstance(config_path, Path): config_path = Path(config_path)

    print(f"--- 正在从 {config_path} 加载配置 ---")
    try:
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
    except FileNotFoundError:
        print(f"错误: 配置文件不存在于路径: {config_path}")
        sys.exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"错误: 配置文件格式无效: {e}")
        sys.exit(1)

    if not user_config.get('enabled', True):
        print(f"配置 '{config_path.name}' 已被禁用(enabled=false)，将跳过。")
        return None

    # 深拷贝默认配置，避免修改原始字典
    config = json.loads(json.dumps(DEFAULT_CONFIG))

    # 递归合并配置
    def merge_configs(base, new):
        for k, v in new.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                merge_configs(base[k], v)
            else:
                base[k] = v

    merge_configs(config, user_config)

    # 检查必需部分
    for section in ['pack_info', 'versions', 'mod_ids', 'rules']:
        if section not in config:
            print(f"错误: 配置文件中缺少必需的部分: [{section}]")
            sys.exit(1)

    print("配置加载成功。")
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RimWorld Mod 自动化翻译脚本。")
    parser.add_argument("config_path", type=str, help="要使用的项目配置文件(.toml)或包含配置文件的目录的路径")
    args = parser.parse_args()

    input_path = Path(args.config_path)
    if not input_path.exists():
        print(f"错误: 提供的路径不存在: {input_path}")
        sys.exit(1)

    toml_files_to_process = []
    if input_path.is_dir():
        print(f"检测到目录输入，将处理该目录下的所有 .toml 文件...")
        toml_files_to_process = sorted(list(input_path.glob("*.toml")))
        if not toml_files_to_process:
            print(f"警告: 在目录 '{input_path}' 中未找到任何 .toml 配置文件。")
    elif input_path.is_file() and input_path.suffix.lower() == ".toml":
        toml_files_to_process.append(input_path)
    else:
        print(f"错误: 输入路径既不是目录，也不是 .toml 文件: {input_path}")

    if not toml_files_to_process:
        print("没有找到要处理的配置文件，程序退出。")
        sys.exit(0)

    total_files = len(toml_files_to_process)
    print(f"\n准备开始批量处理，共计 {total_files} 个项目。")

    for i, config_file_path in enumerate(toml_files_to_process, 1):
        print(f"\n{'=' * 25} 开始处理项目 {i}/{total_files}: {config_file_path.name} {'=' * 25}")
        config_data = load_config(config_file_path)
        if config_data:
            try:
                main(config_data)
            except Exception as e:
                print(f"\n{'!' * 10} 在处理项目 {config_file_path.name} 时发生严重错误: {e} {'!' * 10}")
                import traceback

                traceback.print_exc()
        else:
            print(f"跳过项目 {config_file_path.name}。")
        print(f"{'=' * 25} 项目 {config_file_path.name} 处理完毕 {'=' * 25}")