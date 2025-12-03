# indexer/import_operations.py

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import NFTDatabase


def import_test_flow_results():
    """Import results from the test flow"""
    db = NFTDatabase()
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    # 导入 test_flow_results.json
    results_file = os.path.join(data_dir, 'test_flow_results.json')
    
    if not os.path.exists(results_file):
        print(f"❌ File does not exist: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    print(f"Found {len(results)} operation records\n")
    
    for op_type, result in results:
        if not result:
            continue
            
        blob_data = result.get('data', {})
        height = result.get('height', 0)
        tx_hash = result.get('txhash', '')
        
        print(f"Processing: {op_type} @ height {height}")
        print(f"  Data: {blob_data}")
        
        process_operation(db, blob_data, height, tx_hash)
        print()


def process_operation(db: NFTDatabase, data: dict, height: int, tx_hash: str):
    """Process a single operation"""
    data_type = data.get('type', '')
    
    if data_type == 'nft_mint':
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        to_addr = data.get('to')
        issuer = data.get('issuer')
        metadata_uri = data.get('metadata_uri', '')
        extra = data.get('extra', {})
        
        success = db.mint_nft(
            collection_id=collection_id,
            nft_id=nft_id,
            to_addr=to_addr,
            metadata_uri=metadata_uri,
            extra=extra,
            height=height,
            issuer=issuer,
            tx_hash=tx_hash
        )
        print(f"  Mint result: {'✅' if success else '❌'}")
        
    elif data_type == 'nft_transfer':
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        from_addr = data.get('from')
        to_addr = data.get('to')
        
        success = db.transfer_nft(
            collection_id=collection_id,
            nft_id=nft_id,
            from_addr=from_addr,
            to_addr=to_addr,
            height=height,
            tx_hash=tx_hash,
            tx_type="transfer"
        )
        print(f"  Transfer result: {'✅' if success else '❌'}")
        
    elif data_type == 'nft_list':
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        seller = data.get('seller')
        price = data.get('price')
        
        success = db.create_listing(
            collection_id=collection_id,
            nft_id=nft_id,
            seller=seller,
            price=price,
            height=height,
            tx_hash=tx_hash
        )
        print(f"  List result: {'✅' if success else '❌'}")
        
    elif data_type == 'nft_buy':
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        buyer = data.get('buyer')
        
        # Get listing
        listing = db.get_active_listing(collection_id, nft_id)
        if listing:
            success = db.transfer_nft(
                collection_id=collection_id,
                nft_id=nft_id,
                from_addr=listing['seller'],
                to_addr=buyer,
                height=height,
                tx_hash=tx_hash,
                tx_type="sale",
                price=listing['price']
            )
            print(f"  Buy result: {'✅' if success else '❌'}")
        else:
            print(f"  Buy failed: No active listing found")
    else:
        print(f"  Skipping unknown type: {data_type}")


if __name__ == "__main__":
    print("="*50)
    print("Importing test flow results")
    print("="*50 + "\n")
    import_test_flow_results()
    print("\n" + "="*50)
    print("Import complete!")
    print("="*50)
