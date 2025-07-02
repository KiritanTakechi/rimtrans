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

# 1. 上一个版本的汉化文件 (可选, 可为空)
# 如果提供了，脚本会用它作为参考，只翻译新内容。
# 格式: Steam 创意工坊 ID 组成的字符串，用逗号分隔。例如: "2018323521,1541438994"
PREVIOUS_TRANSLATION_IDS: str = ""

# 2. 需要汉化的 Mod (必需)
# 格式: Steam 创意工坊 ID 组成的字符串，用逗号分隔。例如: "294100,2877340190"
MODS_TO_TRANSLATE_IDS: str = "2920751126"  # 例如: "2877340190"

# 3. SteamCMD 可执行文件的完整路径
# Windows 示例: "C:/steamcmd/steamcmd.exe"
# Linux/macOS 示例: "/home/user/steamcmd/steamcmd.sh"
STEAMCMD_PATH: str = "./steamcmd/steamcmd.sh"

# 4. RimWorld 在 Steam 上的 App ID
RIMWORLD_APP_ID: str = "294100"

# 5. 工作目录
# 下载的 Mod 文件会放在 "DOWNLOAD_PATH"
# 生成的汉化文件会放在 "OUTPUT_PATH"
BASE_WORKING_DIR: Path = Path(__file__).parent
DOWNLOAD_PATH: Path = BASE_WORKING_DIR / "workshop_downloads"
OUTPUT_PATH: Path = BASE_WORKING_DIR / "translation_output"

# 6. Gemini API 配置
# 建议通过环境变量设置 API_KEY (os.environ.get('GEMINI_API_KEY'))
# 如果没有设置环境变量，可以直接在这里填写: genai.Client(api_key="你的API密钥")
# 请注意，直接在代码中写入密钥存在安全风险。
GEMINI_MODEL: str = "gemini-2.5-flash-lite-preview-06-17"  # 使用性价比高的 Flash 模型


# --- 脚本核心代码 ---

def setup_environment():
    """初始化环境，检查配置并创建所需目录。"""
    print("--- 环境设置 ---")

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("错误: 找不到环境变量 'GEMINI_API_KEY'。")
        print("请设置环境变量或直接在脚本中配置 genai.Client。")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        print("Gemini API 客户端初始化成功。")
    except Exception as e:
        print(f"错误: Gemini API 客户端初始化失败: {e}")
        sys.exit(1)

    if not Path(STEAMCMD_PATH).is_file():
        print(f"错误: 在路径 '{STEAMCMD_PATH}' 未找到 SteamCMD。")
        print("请检查 STEAMCMD_PATH 配置是否正确。")
        sys.exit(1)

    if not MODS_TO_TRANSLATE_IDS:
        print("错误: 'MODS_TO_TRANSLATE_IDS' 不能为空。")
        print("请输入至少一个需要汉化的 Mod 的工坊 ID。")
        sys.exit(1)

    DOWNLOAD_PATH.mkdir(exist_ok=True)
    OUTPUT_PATH.mkdir(exist_ok=True)
    print(f"下载目录: {DOWNLOAD_PATH}")
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
    command = [STEAMCMD_PATH, "+login", "anonymous"]
    for mod_id in mod_ids:
        print(f"准备下载 Mod ID: {mod_id}")
        command.extend(["+workshop_download_item", RIMWORLD_APP_ID, mod_id])
    command.append("+quit")

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   encoding='utf-8')

        with tqdm(total=100, desc="SteamCMD 下载中", unit="%") as pbar:
            last_update = time.time()
            progress = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if "Success. Downloaded item" in line:
                        progress += 100 / len(mod_ids)
                        pbar.n = min(int(progress), 100)
                        pbar.refresh()
                    # A simple way to show activity
                    if time.time() - last_update > 5.:
                        pbar.set_postfix_str("等待 SteamCMD 响应...", refresh=True)
                        last_update = time.time()
            pbar.n = 100
            pbar.refresh()

        if process.returncode != 0:
            print(f"\n警告: SteamCMD 进程以非零代码 {process.returncode} 退出。可能部分下载失败。")
        else:
            print("\n所有 Mod 下载任务已提交。")

    except FileNotFoundError:
        print(f"错误: 无法执行 SteamCMD。路径 '{STEAMCMD_PATH}' 是否正确？")
        sys.exit(1)
    except Exception as e:
        print(f"SteamCMD 执行时发生未知错误: {e}")
        sys.exit(1)
    print("--- 下载完成 ---\n")


def find_language_files(mod_path: Path, lang_folder: str) -> List[Path]:
    """在 Mod 目录中查找指定语言的 XML 文件。"""
    lang_path = mod_path / "Languages" / lang_folder
    if not lang_path.is_dir():
        # 有些mod结构不标准，例如直接在根目录有 Languages
        common_paths = [p for p in mod_path.glob('**/Languages') if p.is_dir()]
        if common_paths:
            lang_path = common_paths[0] / lang_folder
            if not lang_path.is_dir():
                return []
        else:
            return []

    return sorted(list(lang_path.rglob("*.xml")))


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


def build_translation_memory(mod_ids: List[str]) -> Dict[str, str]:
    """从旧汉化文件中构建翻译记忆库。"""
    if not mod_ids:
        return {}

    print("--- 正在构建翻译记忆库 ---")
    memory = {}
    mod_content_path = DOWNLOAD_PATH / "content" / RIMWORLD_APP_ID

    for mod_id in tqdm(mod_ids, desc="处理旧汉化"):
        mod_path = mod_content_path / mod_id
        if not mod_path.is_dir():
            print(f"警告: 找不到 Mod {mod_id} 的下载目录，跳过。")
            continue

        # 目标语言文件夹通常是 ChineseSimplified
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


def process_mods_translation(client: genai.Client, mod_ids: List[str], memory: Dict[str, str]):
    """处理所有待翻译 Mod 的主流程。"""
    print("--- 开始翻译新的 Mod ---")
    mod_content_path = DOWNLOAD_PATH / "content" / RIMWORLD_APP_ID

    for mod_id in mod_ids:
        print(f"\n>>> 正在处理 Mod ID: {mod_id}")
        mod_path = mod_content_path / mod_id

        if not mod_path.is_dir():
            print(f"错误: 找不到 Mod {mod_id} 的目录，跳过。")
            continue

        english_files = find_language_files(mod_path, "English")
        if not english_files:
            print("警告: 在此 Mod 中未找到 'English' 语言文件，跳过。")
            continue

        print(f"找到 {len(english_files)} 个英文语言文件。")

        for file_path in tqdm(english_files, desc=f"翻译 Mod {mod_id}", unit="file"):
            process_single_file(client, file_path, mod_id, mod_path, memory)


def process_single_file(client: genai.Client, file_path: Path, mod_id: str, mod_path: Path, memory: Dict[str, str]):
    """翻译单个 XML 文件。"""
    english_dict = load_xml_as_dict(file_path)
    if not english_dict:
        return

    to_translate_dict = {}
    final_translation_dict = {}

    # 1. 分离需要翻译和已存在的内容
    for key, value in english_dict.items():
        if key in memory:
            final_translation_dict[key] = memory[key]
        else:
            to_translate_dict[key] = value

    # 2. 如果有需要翻译的内容，调用 API
    if to_translate_dict:
        # 将待翻译内容打包成一个 XML 字符串
        xml_to_translate_str = "\n".join([f"<{key}>{value}</{key}>" for key, value in to_translate_dict.items()])

        # 暂停一下，避免API调用过于频繁
        time.sleep(1)

        translated_text = translate_with_gemini(client, xml_to_translate_str)

        if translated_text:
            # 解析返回的 XML 并更新到最终字典中
            try:
                # 为了鲁棒性，将返回的文本包裹在根标签中再解析
                translated_root = ET.fromstring(f"<root>{translated_text}</root>")
                for elem in translated_root:
                    if elem.text:
                        final_translation_dict[elem.tag] = elem.text.strip()
                    else:
                        # 处理空标签 <tag/>
                        final_translation_dict[elem.tag] = ""
            except ET.ParseError:
                print(f"\n警告: Gemini 返回的 XML 格式无效，文件 '{file_path.name}' 的部分翻译可能丢失。")
                # 即使解析失败，也保留原文，避免数据丢失
                for key, value in to_translate_dict.items():
                    final_translation_dict[key] = f"【翻译失败】{value}"

    # 3. 按原始顺序写入新文件
    output_relative_path = file_path.relative_to(mod_path / "Languages" / "English")
    output_dir = OUTPUT_PATH / mod_id / "Languages" / "ChineseSimplified" / output_relative_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / file_path.name

    root = ET.Element("LanguageData")
    # 保证输出顺序和原文一致
    for key in english_dict:
        if key in final_translation_dict:
            node = ET.SubElement(root, key)
            node.text = final_translation_dict[key]

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)  # 格式化输出，使其美观
    tree.write(output_file_path, encoding='utf-8', xml_declaration=True)


def main():
    """脚本主入口。"""
    client = setup_environment()

    prev_ids = parse_ids(PREVIOUS_TRANSLATION_IDS)
    new_ids = parse_ids(MODS_TO_TRANSLATE_IDS)

    all_ids_to_download = list(set(prev_ids + new_ids))
    download_with_steamcmd(all_ids_to_download)

    translation_memory = build_translation_memory(prev_ids)

    process_mods_translation(client, new_ids, translation_memory)

    print("\n--- 所有任务完成！---")
    print(f"翻译好的文件已生成在: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()