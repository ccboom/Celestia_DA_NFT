# indexer/import_from_deploy.py

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import NFTDatabase


def import_collection(deploy_file: str):
    """Import collection from deploy file into the database"""
    db = NFTDatabase()
    
    if not os.path.exists(deploy_file):
        print(f"❌ File does not exist: {deploy_file}")
        return False
    
    with open(deploy_file, 'r') as f:
        deploy_info = json.load(f)
    
    collection_data = deploy_info['collection_data']
    result = deploy_info['result']
    height = result.get('height', 1)
    txhash = result.get('txhash', '')
    
    print(f"📦 Importing collection: {collection_data['collection_id']}")
    print(f"  Height: {height}")
    print(f"  TxHash: {txhash}")
    
    success = db.create_collection(collection_data, height, txhash)
    
    if success:
        print("✅ Import succeeded!")
    else:
        print("⚠️ Import failed (might already exist)")
    
    return success


def main():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    # Find all deploy_*.json files
    deploy_files = [f for f in os.listdir(data_dir) if f.startswith('deploy_') and f.endswith('.json')]
    
    if not deploy_files:
        print("No deployment files found")
        return
    
    print(f"Found {len(deploy_files)} deployment files\n")
    
    for filename in deploy_files:
        filepath = os.path.join(data_dir, filename)
        import_collection(filepath)
        print()


if __name__ == "__main__":
    main()
