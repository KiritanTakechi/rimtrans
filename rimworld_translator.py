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
TRANSLATION_MOD_NAME: str = "我的超级汉化包"
TRANSLATION_MOD_AUTHOR: str = "Kiritan"
TRANSLATION_MOD_DESCRIPTION: str = "这是一个自动生成的汉化包，为以下Mod提供简体中文支持：\n\n"
TARGET_RIMWORLD_VERSION: str = "1.5" # 目标RimWorld版本

# 2. 上一个版本的汉化文件 (可选, 可为空)
PREVIOUS_TRANSLATION_IDS: str = ""

# 3. 需要汉化的 Mod (必需)
MODS_TO_TRANSLATE_IDS: str = "3033901359,3033901895,3297307747,3301337278,3400037215,3373064575"

# 4. SteamCMD 配置
STEAMCMD_PATH: str = "./steamcmd/steamcmd.sh"  # macOS/Linux 示例
# STEAMCMD_PATH: str = "C:/steamcmd/steamcmd.exe" # Windows 示例
STEAM_USERNAME: str = "anonymous"
STEAM_PASSWORD: str = ""

# 5. Windows Steam 安装路径 (仅当在 Windows 上运行且 Steam 未安装在默认位置时需要修改)
STEAM_INSTALL_PATH_WINDOWS: str = "/Users/kiritan/Library/Application Support/Steam"

# 6. RimWorld 在 Steam 上的 App ID
RIMWORLD_APP_ID: str = "294100"

# 7. 输出目录
BASE_WORKING_DIR: Path = Path(__file__).parent
OUTPUT_PATH: Path = BASE_WORKING_DIR / "translation_output"

# 8. Gemini API 配置
GEMINI_MODEL: str = "gemini-2.5-flash-lite-preview-06-17"


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
    system_prompt = """
    你是一个为游戏《环世界》(RimWorld) 设计的专业级翻译引擎。
    你的任务是将用户提供的英文 XML 内容翻译成简体中文。
    请严格遵守以下规则：
    1.  **保持结构**: 绝对不要修改任何 XML 标签（例如 `<tag>`）。只翻译标签内的文本。
    2.  **精准翻译**: 确保翻译内容符合《环世界》的语境和常用术语。例如 "pawn" 翻译为 "殖民者" 或 "生物"，"raid" 翻译为 "袭击"。
    3.  **格式一致**: 输出必须是格式良好、可以被程序直接解析的 XML。不要添加任何额外的解释、注释或 ```xml ... ``` 标记。
    4.  **完整性**: 翻译所有提供的条目，不要遗漏。

    这是一个例子：
    输入:
    <ThingDef.label>sandstone block</ThingDef.label>
    <ThingDef.description>Blocks of sandstone. Sandstone is a relatively soft rock that is quick to quarry.</ThingDef.description>

    你的输出应该是:
    <ThingDef.label>砂岩石砖</ThingDef.label>
    <ThingDef.description>砂岩制成的石砖。砂岩是一种相对较软的岩石，开采速度很快。</ThingDef.description>
    """

    prompt = f"请将以下 RimWorld 语言文件内容翻译成简体中文:\n\n{xml_content}"

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system_prompt
            )
        )
        return response.text
    except APIError as e:
        print(f"错误: Gemini API 调用失败: {e.message}")
    except Exception as e:
        print(f"错误: 调用 Gemini 时发生未知错误: {e}")
    return None


def process_mods_translation(client: genai.Client, mod_info_map: Dict[str, dict], memory: Dict[str, str],
                             workshop_path: Path, output_path: Path):
    """处理所有待翻译 Mod 的主流程 (重构版)。"""
    print("--- 开始翻译内容并置入 Cont 文件夹 ---")
    mod_content_path = workshop_path / RIMWORLD_APP_ID

    for mod_id, mod_info in mod_info_map.items():
        print(f"\n>>> 正在处理 Mod: {mod_info['name']} (ID: {mod_id})")
        mod_path = mod_content_path / mod_id

        english_files = find_language_files(mod_path, "English")
        if not english_files:
            print("警告: 在此 Mod 中未找到 'English' 语言文件，跳过。")
            continue

        print(f"找到 {len(english_files)} 个英文语言文件。")
        for file_path in tqdm(english_files, desc=f"翻译 {mod_info['name'][:20]}...", unit="file"):
            process_single_file(client, file_path, mod_info, memory, output_path)


def process_single_file(client: genai.Client, file_path: Path, mod_info: Dict[str, str], memory: Dict[str, str],
                        output_path: Path):
    """翻译单个 XML 文件并保存到新的汉化包结构中。"""
    english_dict = load_xml_as_dict(file_path)
    if not english_dict: return

    to_translate_dict, final_translation_dict = {}, {}
    for key, value in english_dict.items():
        if key in memory:
            final_translation_dict[key] = memory[key]
        else:
            to_translate_dict[key] = value

    if to_translate_dict:
        xml_to_translate_str = "\n".join([f"<{key}>{value}</{key}>" for key, value in to_translate_dict.items()])
        time.sleep(1)  # 避免API调用过快
        translated_text = translate_with_gemini(client, xml_to_translate_str)
        if translated_text:
            try:
                translated_root = ET.fromstring(f"<root>{translated_text}</root>")
                for elem in translated_root:
                    final_translation_dict[elem.tag] = elem.text.strip() if elem.text else ""
            except ET.ParseError:
                print(f"\n警告: Gemini 返回XML格式无效, 文件 '{file_path.name}' 部分翻译可能丢失。")
                for key, value in to_translate_dict.items():
                    final_translation_dict[key] = f"【翻译失败】{value}"

    try:
        english_dir = next(p for p in file_path.parents if p.name == 'English')
        output_relative_path = file_path.relative_to(english_dir)
    except StopIteration:
        print(f"错误: 无法在路径中找到 'English' 目录 '{file_path}'，跳过写入。")
        return

    safe_mod_name = "".join(c for c in mod_info['name'] if c.isalnum() or c in " .-_").strip()

    # 新的输出路径逻辑
    output_dir = output_path / "Cont" / safe_mod_name / "Languages" / "ChineseSimplified" / output_relative_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / file_path.name

    root = ET.Element("LanguageData")
    for key in english_dict:
        if key in final_translation_dict:
            node = ET.SubElement(root, key)
            node.text = final_translation_dict[key]

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_file_path, encoding='utf-8', xml_declaration=True)


def main():
    """脚本主入口。"""
    client = setup_environment()
    workshop_path = get_workshop_content_path()

    prev_ids = parse_ids(PREVIOUS_TRANSLATION_IDS)
    new_ids = parse_ids(MODS_TO_TRANSLATE_IDS)

    # 1. 下载所有需要的Mod
    all_ids_to_download = list(set(prev_ids + new_ids))
    download_with_steamcmd(all_ids_to_download)

    # 2. 从待翻译的Mod中收集信息 (名称, packageId)
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
                print(f"  > 找到Mod: {info['name']} (ID: {mod_id}, packageId: {info['packageId']})")
            else:
                print(f"警告: 无法读取Mod {mod_id} 的元数据，将使用ID作为名称。")
                mod_info_map[mod_id] = {"name": mod_id, "packageId": mod_id, "id": mod_id}

    # 3. 创建汉化包的根目录
    output_path = Path.cwd() / TRANSLATION_MOD_NAME.replace(" ", "_")
    if output_path.exists():
        print(f"\n警告: 输出目录 '{output_path}' 已存在，其中的内容可能会被覆盖。")
    else:
        output_path.mkdir()
    print(f"\n汉化包将生成在: {output_path.resolve()}")

    # 4. 创建汉化包的元文件
    create_about_file(output_path, mod_info_map)
    create_load_folders_file(output_path, mod_info_map)
    create_self_translation(output_path)

    # 5. 构建翻译记忆库
    translation_memory = build_translation_memory(prev_ids, workshop_path)

    # 6. 执行翻译并填充到 Cont 目录
    process_mods_translation(client, mod_info_map, translation_memory, workshop_path, output_path)

    print("\n--- 所有任务完成！---")
    print(f"汉化包 '{TRANSLATION_MOD_NAME}' 已在以下路径生成完毕: \n{output_path.resolve()}")
    print("现在您可以将此文件夹移动到您的 RimWorld/Mods 目录进行测试，或上传到Steam创意工坊。")


if __name__ == "__main__":
    main()
