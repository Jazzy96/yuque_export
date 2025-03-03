import sys
import re
import os
from urllib import parse
from pyuque.client import Yuque
import requests
import time
from huepy import *
from prettytable import PrettyTable
import hashlib  # 添加引入用于生成唯一文件名
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "X-Auth-Token": "xxxx"
    }

used_uuids = []
created_dir = {}
# 全局变量：集中的assets目录和资源映射表
centralized_assets_dir = ""
assets_mapping = {}

# 获取仓库列表
def get_repos(user_id):
    repos = {}
    for repo in yuque.user_list_repos(user_id)['data']:
        # 添加更多字段获取
        repos[str(repo['id'])] = {
            'name': repo['name'],
            'namespace': repo['namespace'],  # 命名空间
            'display_name': repo.get('user', {}).get('name', '') + '_' + repo['name']  # 添加显示名称
        }
    return repos

def get_body(repo_id, doc_id):
    try:
        doc = yuque.doc.get(repo_id, doc_id)
        # 添加响应验证
        if not doc or 'data' not in doc:
            print(red(f"错误响应：{doc}"))
            return None
        return doc['data'].get('body', '')
    except Exception as e:
        print(red(f"API请求失败：{str(e)}"))
        return None

def download_md(repo_id, doc_id, doc_title, repo_dir, original_path=""):
    # 添加doc_id验证
    if not doc_id:
        print(red(f"跳过无ID文档：{doc_title}"))
        return
        
    body = get_body(repo_id, doc_id)
    if not body:
        print(red(f"无法获取内容：{doc_title} (ID: {doc_id})"))
        return

    # 生成资源文件的相对路径前缀，用于构建正确的资源引用
    rel_path_prefix = os.path.relpath(centralized_assets_dir, repo_dir)
    
    # 保存图片
    pattern_images = r'(\!\[(.*)\]\((https:\/\/cdn\.nlark\.com\/yuque.*\/(\d+)\/(.*?\.[a-zA-z]+)).*\))'
    images = [index for index in re.findall(pattern_images, body)]
    if images:
        for index, image in enumerate(images):
            image_body = image[0]                                # 图片完整代码
            image_url = image[2]                                 # 图片链接
            image_suffix = image_url.split(".")[-1]              # 图片后缀
            
            # 生成唯一文件名，使用 URL + 路径 + 索引的 hash 值
            unique_id = hashlib.md5(f"{image_url}_{original_path}_{index}".encode()).hexdigest()[:8]
            unique_filename = f"{doc_title}-{unique_id}.{image_suffix}"
            
            # 保存到集中assets目录
            local_abs_path = f"{centralized_assets_dir}/{unique_filename}"                
            local_abs_path = local_abs_path.replace("<", "%3C").replace(">", "%3E")  # 对特殊符号进行编码
            
            # 构建Markdown中引用的相对路径，对文件名进行URL编码处理
            encoded_filename = parse.quote(unique_filename)
            local_md_path = f"![{doc_title}-{unique_id}]({rel_path_prefix}/{encoded_filename})"  
            
            download_images(image_url, local_abs_path)     # 下载图片
            body = body.replace(image_body, local_md_path)       # 替换链接

    # 保存附件
    pattern_annexes = r'(\[(.*)\]\((https:\/\/www\.yuque\.com\/attachments\/yuque.*\/(\d+)\/(.*?\.[a-zA-z]+)).*\))'
    annexes = [index for index in re.findall(pattern_annexes, body)]
    if annexes:
        for index, annex in enumerate(annexes):
            annex_body = annex[0]                                # 附件完整代码 [xxx.zip](https://www.yuque.com/attachments/yuque/.../xxx.zip)
            annex_name = annex[1]                                # 附件名称 xxx.zip
            annex_url = re.findall(r'\((https:\/\/.*?)\)', annex_body)                # 从附件代码中提取附件链接
            annex_url = annex_url[0].replace("/attachments/", "/api/v2/attachments/") # 替换为附件API
            
            # 生成唯一文件名
            unique_id = hashlib.md5(f"{annex_url}_{original_path}_{index}".encode()).hexdigest()[:8]
            unique_filename = f"{annex_name.split('.')[0]}-{unique_id}.{annex_name.split('.')[-1]}"
            
            # 保存到集中assets目录
            local_abs_path = f"{centralized_assets_dir}/{unique_filename}"           
            
            # 构建Markdown中引用的相对路径，对文件名进行URL编码处理
            encoded_filename = parse.quote(unique_filename)
            local_md_path = f"[{annex_name}]({rel_path_prefix}/{encoded_filename})"  
            
            download_annex(annex_url, local_abs_path)         # 下载附件
            body = body.replace(annex_body, local_md_path)          # 替换链接

    # 保存文档
    markdown_path = f"{repo_dir}/{doc_title}.md"
    markdown_path = markdown_path.replace("<", "%3C").replace(">", "%3E")
    with open(markdown_path, "w", encoding="utf-8",errors="ignore") as f:
        f.write(body)

# 下载图片
def download_images(image, local_name):
    print(good(f"Download {local_name} ..."))
    try:
        re = requests.get(image, headers=headers)
        re.raise_for_status()  # 检查响应状态
        with open(local_name, "wb") as f:
            for chunk in re.iter_content(chunk_size=128):
                f.write(chunk)
    except requests.exceptions.RequestException as e:
        print(f"下载图片 {local_name} 失败: {str(e)}")
        return False
    except IOError as e:
        print(f"保存图片 {local_name} 失败: {str(e)}")
        return False
    return True


# 下载附件
def download_annex(annex, local_name):
    print(good(f"Download {local_name} ..."))
    try:
        re = requests.get(annex, headers=headers)
        re.raise_for_status()  # 检查响应状态
        with open(local_name, "wb") as f:
            for chunk in re.iter_content(chunk_size=128):
                f.write(chunk)
    except requests.exceptions.RequestException as e:
        print(f"下载附件 {local_name} 失败: {str(e)}")
        return False
    except IOError as e:
        print(f"保存附件 {local_name} 失败: {str(e)}")
        return False
    return True

# 目录创建
def create_dir(name, parent_dir):
    # 创建一个新目录并返回其完整路径
    directory = os.path.join(parent_dir, name)
    os.makedirs(directory, exist_ok=True)
    return directory

def process_data(repo_id, data, current_dir, current_path=""):
    # 调试统计
    type_counter = {"DOC": 0, "TITLE": 0}
    for item in data.values():
        type_counter[item["type"]] += 1
    print(bold(cyan(f"类型统计 => DOC: {type_counter['DOC']}, TITLE: {type_counter['TITLE']}")))

    # 先处理所有TITLE创建目录
    for uuid, item in data.items():
        if item["type"] == "TITLE":
            parent_uuid = item.get("parent_uuid", "")
            
            # 获取父目录路径
            parent_path = created_dir.get(parent_uuid, current_dir)
            
            # 清理目录名
            dir_name = re.sub(r'[\\/*?:"<>|]', "_", item["title"])
            
            # 创建目录
            full_dir_path = os.path.join(parent_path, dir_name)
            os.makedirs(full_dir_path, exist_ok=True)
            created_dir[uuid] = full_dir_path
            
            # 对应问题2：如果目录同时也是文档（存在doc_id），创建同名md文件
            if item.get("doc_id"):
                doc_title = dir_name  # 使用目录名作为文档名
                print(cyan(f"处理目录文档：{dir_name} -> {doc_title}.md"))
                doc_path = os.path.join(current_path, dir_name) if current_path else dir_name
                download_md(repo_id, item["doc_id"], doc_title, full_dir_path, doc_path)
            
            print(green(f"创建目录：{full_dir_path}"))

    # 处理DOC文档
    for uuid, item in data.items():
        if item["type"] == "DOC":
            parent_uuid = item.get("parent_uuid", "")
            
            # 确定保存路径
            if parent_uuid in created_dir:
                target_dir = created_dir[parent_uuid]
                doc_path = os.path.join(current_path, re.sub(r'[\\/*?:"<>|]', "_", data[parent_uuid]["title"])) if current_path else re.sub(r'[\\/*?:"<>|]', "_", data[parent_uuid]["title"])
            else:
                target_dir = current_dir
                doc_path = current_path
            
            # 处理文档
            if item["doc_id"]:
                doc_title = re.sub(r'[\\/*?:"<>|]', "_", item["title"])
                print(cyan(f"处理文档：{doc_title}"))
                download_md(repo_id, item["doc_id"], doc_title, target_dir, doc_path)

# 新增函数：创建Obsidian配置
def create_obsidian_config(base_dir, assets_dir_name):
    """创建Obsidian配置文件，设置附件文件夹"""
    obsidian_dir = os.path.join(base_dir, ".obsidian")
    os.makedirs(obsidian_dir, exist_ok=True)
    
    # 创建app.json配置文件
    app_config = {
        "attachmentFolderPath": assets_dir_name,
        "showUnsupportedFiles": False,
        "alwaysUpdateLinks": True
    }
    
    with open(os.path.join(obsidian_dir, "app.json"), "w", encoding="utf-8") as f:
        json.dump(app_config, f, indent=2, ensure_ascii=False)
    
    print(bold(green(f"已创建Obsidian配置，附件目录设置为: {assets_dir_name}")))

def main(assets_dir_name="_assets"):
    # 获取用户ID
    user = yuque.user.get()
    user_id = user['data']['id']
    user_login = user['data']['login']  # 获取用户唯一标识
    user_name = user['data'].get('name', user_login)  # 获取用户显示名，如果没有则使用登录名

    # 获取知识库列表
    all_repos = get_repos(user_id)
    repos_table = PrettyTable(["序号", "ID", "Name", "Namespace", "Display Name"])
    
    # 为了方便用户选择，添加序号
    repo_list = list(all_repos.items())
    for idx, (repo_id, repo_info) in enumerate(repo_list, 1):
        repos_table.add_row([
            idx, 
            repo_id, 
            repo_info['name'], 
            repo_info['namespace'], 
            repo_info.get('display_name', repo_info['name'])
        ])
    
    print(repos_table)
    print(bold(yellow("选择方式：")))
    print(yellow("1. 输入序号范围，如 1-5 表示导出1到5号笔记本"))
    print(yellow("2. 输入多个序号，用逗号分隔，如 1,3,5 表示导出1、3、5号笔记本"))
    print(yellow("3. 输入 all 导出所有笔记本"))
    print(yellow("4. 也可以直接输入知识库ID，用逗号分隔，如 12345,67890"))

    # 输入处理
    input_selection = input(lcyan("请选择要导出的笔记本 (例如: 1-3,5,7 或 all): "))
    
    # 解析用户输入
    temp_ids = []
    if input_selection.lower() == 'all':
        # 导出所有笔记本
        temp_ids = list(all_repos.keys())
    else:
        # 分割用户输入
        parts = [p.strip() for p in input_selection.split(',')]
        for part in parts:
            if '-' in part:  # 处理范围选择
                try:
                    start, end = map(int, part.split('-'))
                    if 1 <= start <= len(repo_list) and 1 <= end <= len(repo_list):
                        for i in range(start, end + 1):
                            repo_id = repo_list[i-1][0]
                            if repo_id not in temp_ids:  # 避免重复
                                temp_ids.append(repo_id)
                    else:
                        print(yellow(f"警告：序号 {part} 超出范围，已忽略"))
                except ValueError:
                    # 可能是直接输入的知识库ID
                    if part in all_repos:
                        temp_ids.append(part)
                    else:
                        print(yellow(f"警告：无法解析 '{part}'，已忽略"))
            else:  # 处理单个选择
                try:
                    idx = int(part)
                    if 1 <= idx <= len(repo_list):
                        repo_id = repo_list[idx-1][0]
                        if repo_id not in temp_ids:  # 避免重复
                            temp_ids.append(repo_id)
                    else:
                        print(yellow(f"警告：序号 {part} 超出范围，已忽略"))
                except ValueError:
                    # 可能是直接输入的知识库ID
                    if part in all_repos:
                        temp_ids.append(part)
                    else:
                        print(yellow(f"警告：无法解析 '{part}'，已忽略"))

    # 知识库ID验证和显示选中的库
    if not temp_ids:
        print(bad(red("未选择任何知识库，程序退出")))
        sys.exit(0)
        
    print(bold(green("\n选择导出的知识库：")))
    selected_table = PrettyTable(["ID", "Name"])
    for temp_id in temp_ids:
        selected_table.add_row([temp_id, all_repos[temp_id]['name']])
    print(selected_table)
    
    confirm = input(lcyan("确认导出以上知识库? (y/n): ")).lower()
    if confirm != 'y':
        print(red("已取消导出操作"))
        sys.exit(0)

    # 处理每个知识库
    for temp_id in temp_ids:
        print(bold(cyan(f"\n处理知识库: {all_repos[temp_id]['name']} (ID: {temp_id})")))
        
        # 重置状态变量
        global used_uuids, created_dir
        used_uuids = []
        created_dir = {}

        # 获取目录结构（关键修改）
        uuid_dict = {}
        toc_data = yuque.repo_toc(temp_id)['data']
        
        # 调试打印原始数据结构
        print(bold(yellow("\n原始API数据结构:")))
        print(json.dumps(toc_data, indent=2, ensure_ascii=False))
        
        # 构建带类型识别的目录结构
        for item in toc_data:
            new_item = {
                'uuid': item['uuid'],
                'title': item['title'],
                'parent_uuid': item.get('parent_uuid', ''),
                # 强化doc_id验证
                'doc_id': str(item['id']) if item.get('id') else None,
                'type': "TITLE" if item.get('child_uuid') else "DOC"
            }
            # 添加警告日志
            if new_item['type'] == "DOC" and not new_item['doc_id']:
                print(yellow(f"警告：检测到无ID文档 [{new_item['title']}]"))
            uuid_dict[new_item['uuid']] = new_item

        # 创建根目录，使用仓库的中文名称
        repo_name = all_repos[temp_id]['name']
        # 清理目录名中的非法字符
        repo_name = re.sub(r'[\\/*?:"<>|]', "_", repo_name)
        parent_dir = create_dir(repo_name, base_dir)
        
        # 为每个知识库创建自己的资源目录
        global centralized_assets_dir
        centralized_assets_dir = create_dir(assets_dir_name, parent_dir)
        print(bold(green(f"创建知识库资源目录：{centralized_assets_dir}")))

        # 处理数据
        process_data(temp_id, uuid_dict, parent_dir)

        # 打印处理结果
        print(bold(green(f"\n处理完成！保存路径：{parent_dir}")))
        print(cyan("生成目录结构："))
        os.system(f"tree {parent_dir}")  # Linux/Mac
        
        # 询问是否创建Obsidian配置
        create_config = input(lcyan("\n是否创建Obsidian配置文件? (y/n，默认y): ") or "y").lower()
        if create_config == 'y':
            create_obsidian_config(base_dir, assets_dir_name)

if __name__ == '__main__':
    token = os.getenv('YUQUE_TOKEN')
    if not token:
        print(red("错误: 未找到 YUQUE_TOKEN 环境变量。请确保 .env 文件中设置了 YUQUE_TOKEN。"))
        sys.exit(1)
    yuque = Yuque(token)
    base_dir = os.path.expanduser("~/Documents/Obsidian Vault")
    
    # 资源目录配置
    print(bold(cyan("资源目录配置：")))
    print(yellow("1. _assets (默认，在Obsidian中可见但被标记为附件)"))
    print(yellow("2. .assets (在Obsidian中隐藏，但可能无法识别图片)"))
    print(yellow("3. assets (在Obsidian中完全可见)"))
    print(yellow("4. attachments (Obsidian推荐的附件目录名)"))
    assets_dir_choice = input(lcyan("请选择资源目录类型 [1-4，默认1]: ") or "1")
    
    # 设置资源目录名称
    assets_dir_names = {
        "1": "_assets",
        "2": ".assets",
        "3": "assets",
        "4": "attachments"
    }
    assets_dir_name = assets_dir_names.get(assets_dir_choice, "_assets")
    print(green(f"将使用 {assets_dir_name} 作为资源目录名称"))
    
    main(assets_dir_name)
