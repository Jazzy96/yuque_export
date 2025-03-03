# Yuque Export Tool

一个用于导出语雀知识库到 Obsidian 的工具，支持完整的目录结构、图片和附件导出。

## 特性

- 支持多知识库批量导出
- 保持原有目录结构
- 自动下载并本地化图片和附件
- 支持 Obsidian 配置生成
- 灵活的资源目录配置选项
- 友好的命令行交互界面

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/yuque_export.git
cd yuque_export
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置

1. 复制 `.env.example` 为 `.env` 文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置以下内容：
```
# 语雀 Token
YUQUE_TOKEN=your_token_here

# 导出目录路径
EXPORT_PATH=~/Documents/Obsidian Vault
```

获取 Token 方式：语雀 -> 个人设置 -> Token

## 使用方法

1. 运行脚本：
```bash
python yuque_export.py
```

2. 按提示选择要导出的知识库：
   - 输入序号范围（如 `1-5`）
   - 输入多个序号（如 `1,3,5`）
   - 输入 `all` 导出所有知识库
   - 直接输入知识库 ID

3. 选择资源目录配置：
   - `_assets`（默认，在 Obsidian 中可见但被标记为附件）
   - `.assets`（在 Obsidian 中隐藏）
   - `assets`（在 Obsidian 中完全可见）
   - `attachments`（Obsidian 推荐的附件目录名）

## 输出

- 导出到 `EXPORT_PATH` 指定的目录（默认为 `~/Documents/Obsidian Vault`）
- 每个知识库创建独立文件夹
- 保持原有目录结构
- 图片和附件统一存放在资源目录

## 依赖

- pyuque
- python-dotenv
- requests
- huepy
- prettytable

## 注意事项

- 确保有足够的磁盘空间存储导出内容
- 图片和附件下载可能需要一定时间
- 建议在导出前检查网络连接状态

## License

MIT 