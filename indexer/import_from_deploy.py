# indexer/import_from_deploy.py

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import NFTDatabase


def import_collection(deploy_file: str):
    """从部署文件导入集合到数据库"""
    db = NFTDatabase()
    
    if not os.path.exists(deploy_file):
        print(f"❌ 文件不存在: {deploy_file}")
        return False
    
    with open(deploy_file, 'r') as f:
        deploy_info = json.load(f)
    
    collection_data = deploy_info['collection_data']
    result = deploy_info['result']
    height = result.get('height', 1)
    txhash = result.get('txhash', '')
    
    print(f"📦 导入集合: {collection_data['collection_id']}")
    print(f"  高度: {height}")
    print(f"  TxHash: {txhash}")
    
    success = db.create_collection(collection_data, height, txhash)
    
    if success:
        print("✅ 导入成功!")
    else:
        print("⚠️ 导入失败（可能已存在）")
    
    return success


def main():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    # 查找所有 deploy_*.json 文件
    deploy_files = [f for f in os.listdir(data_dir) if f.startswith('deploy_') and f.endswith('.json')]
    
    if not deploy_files:
        print("没有找到部署文件")
        return
    
    print(f"找到 {len(deploy_files)} 个部署文件\n")
    
    for filename in deploy_files:
        filepath = os.path.join(data_dir, filename)
        import_collection(filepath)
        print()


if __name__ == "__main__":
    main()