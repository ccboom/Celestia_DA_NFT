# indexer/import_operations.py

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import NFTDatabase


def import_test_flow_results():
    """导入测试流程的结果"""
    db = NFTDatabase()
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    # 导入 test_flow_results.json
    results_file = os.path.join(data_dir, 'test_flow_results.json')
    
    if not os.path.exists(results_file):
        print(f"❌ 文件不存在: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    print(f"找到 {len(results)} 条操作记录\n")
    
    for op_type, result in results:
        if not result:
            continue
            
        blob_data = result.get('data', {})
        height = result.get('height', 0)
        tx_hash = result.get('txhash', '')
        
        print(f"处理: {op_type} @ 高度 {height}")
        print(f"  数据: {blob_data}")
        
        process_operation(db, blob_data, height, tx_hash)
        print()


def process_operation(db: NFTDatabase, data: dict, height: int, tx_hash: str):
    """处理单条操作"""
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
        print(f"  Mint 结果: {'✅' if success else '❌'}")
        
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
        print(f"  Transfer 结果: {'✅' if success else '❌'}")
        
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
        print(f"  List 结果: {'✅' if success else '❌'}")
        
    elif data_type == 'nft_buy':
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        buyer = data.get('buyer')
        
        # 获取挂单
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
            print(f"  Buy 结果: {'✅' if success else '❌'}")
        else:
            print(f"  Buy 失败: 没有找到活跃挂单")
    else:
        print(f"  跳过未知类型: {data_type}")


if __name__ == "__main__":
    print("="*50)
    print("导入测试流程结果")
    print("="*50 + "\n")
    import_test_flow_results()
    print("\n" + "="*50)
    print("导入完成!")
    print("="*50)
