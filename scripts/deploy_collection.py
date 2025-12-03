# scripts/deploy_collection.py

import json
import os
import sys
import time
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.docker_blob_client import submit_collection


def get_alice_address():
    """Get the address of 'alice' inside the container"""
    result = subprocess.run(
        'docker exec celestia-validator celestia-appd keys show alice -a --keyring-backend test',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def main():
    collection_id = "celestia_dragons_v1"
    alice_address = get_alice_address()
    
    print(f"Alice address: {alice_address}")
    
    collection_data = {
        'type': 'collection_definition',
        'collection_id': collection_id,
        'issuer': alice_address,
        'name': 'Celestia Dragons Collection',
        'description': 'Dragon NFTs on Celestia DA',
        'created_at_height': 0,
        'nfts': [
            {
                'id': 1,
                'metadata_uri': 'ipfs://QmFireDragon',
                'extra': {'name': 'Fire Dragon', 'rarity': 'legendary', 'power': 95}
            },
            {
                'id': 2,
                'metadata_uri': 'ipfs://QmIceDragon',
                'extra': {'name': 'Ice Dragon', 'rarity': 'epic', 'power': 88}
            },
            {
                'id': 3,
                'metadata_uri': 'ipfs://QmThunderDragon',
                'extra': {'name': 'Thunder Dragon', 'rarity': 'rare', 'power': 82}
            }
        ],
        'issuer_signature': 'PLACEHOLDER'
    }
    
    print(f"\n📦 Deploying collection: {collection_id}")
    print(f"  NFT count: {len(collection_data['nfts'])}")
    print("="*50)
    
    result = submit_collection(collection_data)
    
    if result:
        print("="*50)
        print("🎉 Collection deployed successfully!")
        print(f"  Collection ID: {collection_id}")
        print(f"  TxHash: {result['txhash']}")
        print(f"  Height: {result['height']}")
        
        # save
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(output_dir, exist_ok=True)
        
        deploy_info = {
            'collection_data': collection_data,
            'result': result,
            'deployed_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        output_file = os.path.join(output_dir, f'deploy_{collection_id}.json')
        with open(output_file, 'w') as f:
            json.dump(deploy_info, f, indent=2)
            
        print(f"  Saved to: {output_file}")
        return result
    else:
        print("❌ Deployment failed")
        return None


if __name__ == "__main__":
    main()
