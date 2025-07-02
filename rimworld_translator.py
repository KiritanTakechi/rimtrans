# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

import google.genai as genai
from google.genai import types
from google.genai.errors import APIError
from tqdm import tqdm

# --- 全局配置 (请根据你的情况修改) ---

# 1. 汉化包 Mod 的信息 (请自定义)
TRANSLATION_MOD_NAME: str = "Adaptive Storage SCN"
TRANSLATION_MOD_AUTHOR: str = "Kiritan"
TRANSLATION_MOD_DESCRIPTION: str = "这是一个自动生成的汉化包，为以下Mod提供简体中文支持：\n\n"
TARGET_RIMWORLD_VERSION: str = "1.5" # 目标RimWorld版本

# 2. 上一个版本的汉化文件 (可选, 可为空)
PREVIOUS_TRANSLATION_IDS: str = ""

# 3. 需要汉化的 Mod (必需)
MODS_TO_TRANSLATE_IDS: str = "3033901359,3033901895,3297307747,3301337278,3400037215,3373064575"

# 4. 可被注入翻译的XML标签列表 (可按需添加)
TRANSLATABLE_DEF_TAGS = [
    'label', 'description', 'jobString', 'reportString', 'verb', 'gerund',
    'notification', 'letterLabel', 'letterText', 'statement', 'beginLetter'
]

# 5. SteamCMD 配置
STEAMCMD_PATH: str = "./steamcmd/steamcmd.sh"  # macOS/Linux 示例
# STEAMCMD_PATH: str = "C:/steamcmd/steamcmd.exe" # Windows 示例
STEAM_USERNAME: str = "anonymous"
STEAM_PASSWORD: str = ""

# 6. Windows Steam 安装路径 (仅当在 Windows 上运行且 Steam 未安装在默认位置时需要修改)
STEAM_INSTALL_PATH_WINDOWS: str = "/Users/kiritan/Library/Application Support/Steam"

# 7. RimWorld 在 Steam 上的 App ID
RIMWORLD_APP_ID: str = "294100"

# 8. 输出目录
BASE_WORKING_DIR: Path = Path(__file__).parent
OUTPUT_PATH: Path = BASE_WORKING_DIR / "translation_output"

# 9. Gemini API 配置
GEMINI_MODEL: str = "gemini-2.5-flash-lite-preview-06-17"

# 10. RimWorld 核心术语表
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

def get_workshop_content_path() -> Path:
    """根据操作系统自动获取 Steam Workshop 内容的基础路径。"""
    platform = sys.platform
    home = Path.home()

    if platform == "win32":
        # Windows: 通常在 Steam 安装目录下
        path = Path(STEAM_INSTALL_PATH_WINDOWS) / "steamapps" / "workshop" / "content"
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

    if not Path(STEAMCMD_PATH).is_file():
        print(f"错误: 在路径 '{STEAMCMD_PATH}' 未找到 SteamCMD。")
        sys.exit(1)

    if not MODS_TO_TRANSLATE_IDS:
        print("错误: 'MODS_TO_TRANSLATE_IDS' 不能为空。")
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
    command = [STEAMCMD_PATH, "+login", STEAM_USERNAME, STEAM_PASSWORD]

    for mod_id in mod_ids:
        print(f"准备下载 Mod ID: {mod_id}")
        command.extend(["+workshop_download_item", RIMWORLD_APP_ID, mod_id])
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
        print(f"错误: 无法执行 SteamCMD。路径 '{STEAMCMD_PATH}' 是否正确？")
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
        tree = ET.parse(about_file)
        root = tree.getroot()
        name_node = root.find("name")
        package_id_node = root.find("packageId")

        # packageId可能不存在，给一个基于作者和名称的备用值
        author_node = root.find("author")
        author = author_node.text.strip().replace(" ",
                                                  "") if author_node is not None and author_node.text else "Unknown"
        name = name_node.text.strip() if name_node is not None and name_node.text else mod_path.name

        package_id = package_id_node.text.strip() if package_id_node is not None and package_id_node.text else f"{author}.{name.replace(' ', '')}"

        return {"name": name, "packageId": package_id.lower()}
    except ET.ParseError:
        return None


def create_about_file(output_path: Path, mod_info_map: Dict[str, dict]):
    """创建汉化包的About/About.xml文件。"""
    about_dir = output_path / "About"
    about_dir.mkdir(exist_ok=True)

    supported_mods_list = "\n".join([f"  - {info['name']}" for info in mod_info_map.values()])
    full_description = TRANSLATION_MOD_DESCRIPTION + supported_mods_list

    about_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
    <name>{TRANSLATION_MOD_NAME}</name>
    <author>{TRANSLATION_MOD_AUTHOR}</author>
    <supportedVersions>
        <li>{TARGET_RIMWORLD_VERSION}</li>
    </supportedVersions>
    <packageId>{TRANSLATION_MOD_AUTHOR.replace(" ", "")}.{TRANSLATION_MOD_NAME.replace(" ", "")}</packageId>
    <description>{full_description}</description>
    <modDependencies>
"""
    for mod_info in mod_info_map.values():
        about_content += f"""
        <li>
            <packageId>{mod_info['packageId']}</packageId>
            <displayName>{mod_info['name']}</displayName>
            <steamWorkshopUrl>steam://url/CommunityFilePage/{mod_info['id']}</steamWorkshopUrl>
        </li>"""
    about_content += """
    </modDependencies>
    <loadAfter>
"""
    for mod_info in mod_info_map.values():
        about_content += f"""        <li>{mod_info['packageId']}</li>\n"""
    about_content += """    </loadAfter>
</ModMetaData>
"""
    (about_dir / "About.xml").write_text(about_content, encoding='utf-8')
    (about_dir / "PublishedFileId.txt").touch()
    print("生成 About/About.xml。请手动添加 Preview.png 和 ModIcon.png 到 About 文件夹。")


def create_load_folders_file(output_path: Path, mod_info_map: Dict[str, dict]):
    """创建LoadFolders.xml文件。"""
    items_str = ""
    for mod_info in mod_info_map.values():
        # 使用Mod的真实名称作为文件夹名，移除非法字符
        safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
        items_str += f"        <li IfModActive=\"{mod_info['packageId']}\">Cont/{safe_mod_name}</li>\n"

    load_folders_content = f"""<loadFolders>
    <v{TARGET_RIMWORLD_VERSION}>
{items_str}    </v{TARGET_RIMWORLD_VERSION}>
</loadFolders>
"""
    (output_path / "LoadFolders.xml").write_text(load_folders_content, encoding='utf-8')
    print("生成 LoadFolders.xml。")


def create_self_translation(output_path: Path):
    """为汉化包自身创建简体中文翻译。"""
    lang_dir = output_path / "Languages" / "ChineseSimplified" / "Keyed"
    lang_dir.mkdir(parents=True, exist_ok=True)

    self_translation_content = f"""<?xml version="1.0" encoding="utf-8" ?>
<LanguageData>
    <{TRANSLATION_MOD_AUTHOR.replace(" ", "")}.{TRANSLATION_MOD_NAME.replace(" ", "")}.ModName>{TRANSLATION_MOD_NAME}</{TRANSLATION_MOD_AUTHOR.replace(" ", "")}.{TRANSLATION_MOD_NAME.replace(" ", "")}.ModName>
</LanguageData>
"""
    (lang_dir / "SelfTranslation.xml").write_text(self_translation_content, encoding='utf-8')
    print("为汉化包创建自翻译文件。")


def find_language_files(mod_path: Path, lang_folder: str) -> List[Path]:
    """
    在 Mod 目录中查找指定语言的 XML 文件，按以下优先级顺序：
    1. /<版本号>/Languages/
    2. /Languages/
    3. 任意子目录下的 /Languages/ (作为备用)
    """
    # 优先级 1: 版本特定路径 (e.g., /1.5/Languages/)
    version_lang_path = mod_path / TARGET_RIMWORLD_VERSION / "Languages" / lang_folder
    if version_lang_path.is_dir():
        return sorted(list(version_lang_path.rglob("*.xml")))

    # 优先级 2: Mod 根路径 (e.g., /Languages/)
    root_lang_path = mod_path / "Languages" / lang_folder
    if root_lang_path.is_dir():
        return sorted(list(root_lang_path.rglob("*.xml")))

    # 优先级 3: 备用方案，递归查找任意位置的 Languages 文件夹 (e.g., /Common/Languages)
    for p in mod_path.glob('**/Languages'):
        lang_path = p / lang_folder
        if lang_path.is_dir():
            # 找到第一个就返回，因为glob的结果是无序的
            return sorted(list(lang_path.rglob("*.xml")))

    return []


def load_xml_as_dict(file_path: Path) -> Dict[str, str]:
    """将 RimWorld 语言 XML 文件解析为字典。"""
    translations = {}
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for elem in root.findall('./*'):
            if elem.text and elem.text.strip():
                translations[elem.tag] = elem.text.strip()
    except ET.ParseError:
        print(f"警告: 解析 XML 文件失败: {file_path}")
    return translations


def build_translation_memory(mod_ids: List[str], workshop_path: Path) -> Dict[str, str]:
    """从旧汉化文件中构建翻译记忆库。"""
    if not mod_ids:
        return {}

    print("--- 正在构建翻译记忆库 ---")
    memory = {}
    mod_content_path = workshop_path / RIMWORLD_APP_ID

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


def translate_with_gemini(client: genai.Client, xml_content: str) -> Optional[str]:
    """使用 Gemini API 翻译 XML 内容。"""
    # 1. 基础系统指令定义了模型的角色和基本规则
    base_system_prompt = """
    你是一个为游戏《环世界》(RimWorld) 设计的专业级翻译引擎。
    你的任务是将用户提供的英文 XML 内容翻译成简体中文。
    请严格遵守以下规则：
    1.  **保持结构**: 绝对不要修改任何 XML 标签（例如 `<tag>`）。只翻译标签内的文本。
    2.  **格式一致**: 输出必须是格式良好、可以被程序直接解析的 XML。不要添加任何额外的解释、注释或 ```xml ... ``` 标记。
    3.  **完整性**: 翻译所有提供的条目，不要遗漏。

    这是一个例子：
    输入:
    <ThingDef.label>sandstone block</ThingDef.label>
    <ThingDef.description>Blocks of sandstone. Sandstone is a relatively soft rock that is quick to quarry.</ThingDef.description>

    你的输出应该是:
    <ThingDef.label>砂岩石砖</ThingDef.label>
    <ThingDef.description>砂岩制成的石砖。砂岩是一种相对较软的岩石，开采速度很快。</ThingDef.description>
    """

    # 2. 从全局字典动态构建术语表提示部分
    glossary_prompt_part = "4. **术语统一**: 这是最重要的规则。请严格参考以下术语表进行翻译，确保关键词的统一性。如果术语表中的词汇出现，必须使用对应的翻译：\n"
    # 使用 .items() 遍历字典
    glossary_items = [f"- '{en.lower()}': '{cn}'" for en, cn in RIMWORLD_GLOSSARY.items()]
    glossary_prompt_part += "\n".join(glossary_items)

    # 3. 组合成最终的、强大的系统指令
    final_system_prompt = f"{base_system_prompt}\n\n{glossary_prompt_part}"

    # 4. 主提示（保持简洁，因为所有指令都在 system_instruction 中）
    prompt = f"请将以下 RimWorld 语言文件内容翻译成简体中文:\n\n{xml_content}"

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=final_system_prompt
            )
        )
        return response.text
    except APIError as e:
        print(f"错误: Gemini API 调用失败: {e.message}")
    except Exception as e:
        print(f"错误: 调用 Gemini 时发生未知错误: {e}")
    return None


def translate_and_save(client: genai.Client, targets: Dict[str, str], memory: Dict[str, str], output_file_path: Path):
    """通用翻译和保存逻辑。"""
    to_translate_dict = {k: v for k, v in targets.items() if k not in memory}
    final_translation_dict = {k: memory[k] for k, v in targets.items() if k in memory}

    if to_translate_dict:
        xml_to_translate_str = "\n".join([f"<{key}>{value}</{key}>" for key, value in to_translate_dict.items()])
        time.sleep(1)
        translated_text = translate_with_gemini(client, xml_to_translate_str)
        if translated_text:
            try:
                translated_root = ET.fromstring(f"<root>{translated_text}</root>")
                for elem in translated_root:
                    final_translation_dict[elem.tag] = elem.text.strip() if elem.text else ""
            except ET.ParseError:
                print(f"\n警告: Gemini 返回XML格式无效, 文件 '{output_file_path.name}' 部分翻译可能丢失。")
                for key in to_translate_dict: final_translation_dict[key] = f"【翻译失败】{targets[key]}"

    if not final_translation_dict: return

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("LanguageData")
    for key in targets:  # 按原始顺序写入
        if key in final_translation_dict:
            node = ET.SubElement(root, key);
            node.text = final_translation_dict[key]
    tree = ET.ElementTree(root);
    ET.indent(tree, space="  ", level=0)
    tree.write(output_file_path, encoding='utf-8', xml_declaration=True)


def process_standard_translation(client: genai.Client, mod_path: Path, mod_info: Dict, memory: Dict, output_path: Path):
    """处理 Languages/English 文件夹中的标准翻译。"""
    english_files = find_language_files(mod_path, "English")
    if not english_files: return

    print(f"  -> 找到 {len(english_files)} 个标准语言文件，开始处理...")
    for file_path in english_files:
        targets = load_xml_as_dict(file_path)
        if not targets: continue

        try:
            english_dir = next(p for p in file_path.parents if p.name == 'English')
            output_relative_path = file_path.relative_to(english_dir)
        except StopIteration:
            print(f"错误: 无法在路径中找到 'English' 目录 '{file_path}'，跳过。")
            continue

        safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
        output_file_path = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / output_relative_path

        translate_and_save(client, targets, memory, output_file_path)


def process_def_injection_translation(client: genai.Client, mod_path: Path, mod_info: Dict, memory: Dict,
                                      output_path: Path):
    """处理 Defs/ 文件夹中的注入式翻译 (新功能)。"""
    def_files = list(mod_path.rglob("Defs/**/*.xml"))
    if not def_files: return

    print(f"  -> 找到 {len(def_files)} 个定义(Defs)文件，扫描注入点...")
    for file_path in def_files:
        targets = {}
        try:
            tree = ET.parse(file_path)
            for element in tree.getroot().findall("./*"):
                def_name_node = element.find("defName")
                if def_name_node is None or not def_name_node.text: continue
                def_name = def_name_node.text.strip()

                for sub_element in element:
                    if sub_element.tag in TRANSLATABLE_DEF_TAGS and sub_element.text:
                        injection_key = f"{def_name}.{sub_element.tag}"
                        targets[injection_key] = sub_element.text.strip()
        except ET.ParseError:
            continue  # 跳过无法解析的XML

        if not targets: continue

        print(f"    -> 在 {file_path.name} 中发现 {len(targets)} 个可注入字段。")

        relative_def_path = file_path.relative_to(mod_path)
        safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()
        output_file_path = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / "DefInjected" / relative_def_path

        translate_and_save(client, targets, memory, output_file_path)


def main():
    """脚本主入口。"""
    client = setup_environment()
    workshop_path = get_workshop_content_path()

    prev_ids = parse_ids(PREVIOUS_TRANSLATION_IDS)
    new_ids = parse_ids(MODS_TO_TRANSLATE_IDS)

    download_with_steamcmd(list(set(prev_ids + new_ids)))

    print("\n--- 正在收集待汉化Mod的元数据 ---")
    mod_content_path = workshop_path / RIMWORLD_APP_ID
    mod_info_map = {}
    for mod_id in new_ids:
        mod_path = mod_content_path / mod_id
        if mod_path.is_dir():
            info = get_mod_info(mod_path)
            if info:
                info['id'] = mod_id
                mod_info_map[mod_id] = info
                print(f"  > 找到Mod: {info['name']} (packageId: {info['packageId']})")
            else:
                mod_info_map[mod_id] = {"name": mod_id, "packageId": mod_id, "id": mod_id}

    output_path = Path.cwd() / TRANSLATION_MOD_NAME.replace(" ", "_")
    output_path.mkdir(exist_ok=True)
    print(f"\n汉化包将生成在: {output_path.resolve()}")

    create_about_file(output_path, mod_info_map)
    create_load_folders_file(output_path, mod_info_map)
    create_self_translation(output_path)

    translation_memory = build_translation_memory(prev_ids, workshop_path)

    print("\n--- 开始双模式翻译 ---")
    for mod_id, mod_info in mod_info_map.items():
        print(f"\n>>> 正在处理 Mod: {mod_info['name']} (ID: {mod_id})")
        mod_path = mod_content_path / mod_id

        # 模式一：标准翻译
        process_standard_translation(client, mod_path, mod_info, translation_memory, output_path)

        # 模式二：注入式翻译
        process_def_injection_translation(client, mod_path, mod_info, translation_memory, output_path)

    print("\n--- 所有任务完成！---")
    print(f"汉化包 '{TRANSLATION_MOD_NAME}' 已在以下路径生成完毕: \n{output_path.resolve()}")
    print("现在您可以将此文件夹移动到您的 RimWorld/Mods 目录进行测试，或上传到Steam创意工坊。")


if __name__ == "__main__":
    main()
