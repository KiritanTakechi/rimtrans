# 边缘世界自动化汉化脚本

## 使用说明

### 第1步：克隆本项目

`git clone https://github.com/KiritanTakechi/rimtrans`

### 第2步：环境准备 (一次性设置)

在首次使用脚本前，请确保您的系统环境已准备就绪。
安装 uv

macOS / Linux:
`curl -LsSf https://astral.sh/uv/install.sh | sh`


Windows (Powershell):
`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`


创建虚拟环境并安装依赖
打开您的终端（命令行工具），进入您打算存放本脚本的工作目录，然后执行以下命令：

#### 1. 使用 uv 创建一个名为 .venv 的虚拟环境
`uv venv`

#### 2. 激活虚拟环境
#### macOS / Linux
`source .venv/bin/activate`
#### Windows
`.venv\Scripts\activate`

#### 3. 在虚拟环境中安装所有必需的Python库
`uv sync`

#### 4. 准备 SteamCMD
从Valve官方文档下载并解压SteamCMD。
记下其可执行文件的绝对路径，例如：
Windows: C:/steamcmd/steamcmd.exe
macOS/Linux: /Users/yourname/steamcmd/steamcmd.sh
您需要在后续的配置文件中填入这个路径。

#### 5. 获取 Gemini API 密钥
访问 Google AI Studio 并获取您的API密钥。
macOS / Linux: 在您的 .zshrc 或 .bash_profile 文件中添加 export GEMINI_API_KEY='你的API密钥'。
Windows: 通过“编辑系统环境变量”界面添加一个名为 GEMINI_API_KEY 的新变量。

### 第3步：项目配置 (为每个汉化包进行配置)

脚本现在由.toml配置文件驱动。您可以为您想制作的每一个汉化包都创建一个独立的配置文件。
创建配置文件
在一个您喜欢的位置（例如，在脚本同级的 mod_configs/ 文件夹内），创建一个新的文本文件，并将其命名为 my_project.toml。
填写配置
将以下模板复制到您的.toml文件中，并根据您的项目需求进行修改。
```toml
# my_project.toml -- 我的汉化项目配置文件

# [1] 汉化包本身的信息
[pack_info]
name = "我的超级汉化包"
author = "你的名字"
description = """
这是一个多行描述。
为以下Mod提供汉化支持：
"""

# [2] 目标环世界版本 (可以有一个或多个)
[versions]
targets = ["1.5", "1.6"]

# [3] Mod的Steam Workshop ID
[mod_ids]
# 需要汉化的Mod ID列表，用逗号分隔
translate = "2877340190,294100"
# 作为翻译记忆库的旧汉化Mod ID列表 (可选, 用于更新)
# 如果是更新您自己的汉化包，请在此处填入您旧版汉化包的ID
previous = "1234567890"

# [4] 翻译规则
[rules]
# 可被注入翻译的XML标签
translatable_def_tags = [
    'label', 'description', 'jobString', 'reportString', 'verb', 'gerund',
    'notification', 'letterLabel', 'letterText', 'statement', 'beginLetter',
]

# [5] 系统级配置 (可选, 如果不填，脚本会使用内置的默认值)
[system]
# steamcmd_path = "/path/to/your/steamcmd.sh"
# gemini_model = "gemini-1.5-pro-latest"
# 慢速模式：在每次API调用后增加2秒延迟，以避免触发频率限制
slow_mode = true
```


### 第4步：运行脚本

激活虚拟环境
确保您的终端已激活之前创建的.venv环境。
执行命令
脚本支持两种运行模式：
处理单个项目:

`python rimworld_translator.py /path/to/your/my_project.toml`

批量处理整个目录:

`python rimworld_translator.py ./mod_configs/`

耐心等待
脚本会自动执行下载、扫描、翻译、打包的全过程。根据Mod数量和大小，这可能需要几分钟到几十分钟不等。请观察终端输出的进度条和日志。

### 第5步：后续步骤

检查输出
脚本执行完毕后，会在其当前运行的目录下生成一个与您汉化包同名的新文件夹（例如 我的超级汉化包/）。这里面就是所有生成的文件。
本地测试
将这个生成的文件夹完整地复制到您的环世界本地Mods目录，然后在游戏中启动并测试汉化效果是否正确。
上传至创意工坊
确认无误后，参考之前提供的游戏内上传指南，将您的汉化包发布到Steam创意工坊。

常见问题 (FAQ)

遇到429 RESOURCE_EXHAUSTED错误怎么办?

这是API频率限制。请在您的.toml文件中找到[system]部分，添加或确保slow_mode = true，然后重新运行脚本。

提示FileNotFoundError: steamcmd?

请检查您.toml文件中steamcmd_path的路径是否正确，建议使用绝对路径。