"""测试文件上传和分析功能"""
import requests
import json
import os
import sys

# 设置控制台编码
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

def upload_file(file_path):
    """上传文件"""
    url = f"{BASE_URL}/api/files/upload"
    filename = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        files = {'file': (filename, f, 'text/plain')}
        response = requests.post(url, files=files)

    return response.json()

def get_files():
    """获取文件列表"""
    url = f"{BASE_URL}/api/files"
    response = requests.get(url)
    return response.json()

def analyze_files(file_ids):
    """分析文件"""
    url = f"{BASE_URL}/api/analyze"
    data = {"fileIds": file_ids}
    response = requests.post(url, json=data, timeout=300)
    return response.json()

def get_trees():
    """获取思维树列表"""
    url = f"{BASE_URL}/api/trees"
    response = requests.get(url)
    return response.json()

def main():
    question_dir = "d:/claudeCode-project/BrainTree/Question"

    # 测试文件列表
    test_files = [
        "高级问题答案.txt",
        "课堂笔记_JUC(1).txt",
        "课堂笔记_jvm.txt",
        "课堂笔记_mysql.txt",
    ]

    print("=" * 50)
    print("开始测试文件上传")
    print("=" * 50)

    uploaded_ids = []

    for filename in test_files:
        file_path = os.path.join(question_dir, filename)
        if os.path.exists(file_path):
            print(f"\n上传文件: {filename}")
            result = upload_file(file_path)
            if result.get("success"):
                file_id = result["data"]["id"]
                uploaded_ids.append(file_id)
                print(f"  [OK] 上传成功, ID: {file_id[:8]}...")
            else:
                print(f"  [FAIL] 上传失败: {result.get('detail', result.get('error', '未知错误'))}")
        else:
            print(f"  [SKIP] 文件不存在: {file_path}")

    print("\n" + "=" * 50)
    print("测试单文件分析")
    print("=" * 50)

    if uploaded_ids:
        # 测试单文件分析
        print(f"\n分析单个文件: {test_files[0]}")
        result = analyze_files([uploaded_ids[0]])
        if result.get("success"):
            tree = result["data"]
            print(f"  [OK] 分析成功")
            print(f"  - 树名称: {tree['name']}")
            print(f"  - 节点数量: {len(tree['nodes'])}")
            print(f"  - 连接数量: {len(tree['edges'])}")
        else:
            print(f"  [FAIL] 分析失败: {result.get('detail', result.get('error', '未知错误'))}")

    print("\n" + "=" * 50)
    print("测试多文件分析")
    print("=" * 50)

    if len(uploaded_ids) >= 2:
        # 测试多文件分析
        print(f"\n分析多个文件: {len(uploaded_ids)} 个文件")
        result = analyze_files(uploaded_ids)
        if result.get("success"):
            tree = result["data"]
            print(f"  [OK] 分析成功")
            print(f"  - 树名称: {tree['name']}")
            print(f"  - 节点数量: {len(tree['nodes'])}")
            print(f"  - 连接数量: {len(tree['edges'])}")

            # 显示部分节点
            print(f"\n  前5个节点:")
            for node in tree['nodes'][:5]:
                print(f"    - {node['label']} ({node['type']})")
        else:
            print(f"  [FAIL] 分析失败: {result.get('detail', result.get('error', '未知错误'))}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
