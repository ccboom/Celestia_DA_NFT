# scripts/nft_operations.py

import json
import time
import sys
import os
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docker_blob_client import DockerBlobClient, NAMESPACE_ID


def get_address(key_name: str) -> str:
    """获取容器内账户地址"""
    result = subprocess.run(
        f'docker exec celestia-validator celestia-appd keys show {key_name} -a --keyring-backend test',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


# 获取地址
ALICE_ADDRESS = get_address('alice')
BOB_ADDRESS = get_address('bob')
VALIDATOR_ADDRESS = get_address('validator')

print(f"Alice: {ALICE_ADDRESS}")
print(f"Bob: {BOB_ADDRESS}")


def mint_nft(collection_id: str, nft_id: int, to_address: str, 
             metadata_uri: str = "", extra: dict = None, 
             from_account: str = "alice"):
    """
    铸造新 NFT
    只有 collection 的 issuer 才能铸造
    """
    client = DockerBlobClient()
    
    data = {
        "type": "nft_mint",
        "collection_id": collection_id,
        "nft_id": nft_id,
        "to": to_address,
        "issuer": get_address(from_account),
        "metadata_uri": metadata_uri,
        "extra": extra or {},
        "timestamp": int(time.time())
    }
    
    print(f"\n🎨 铸造 NFT: {collection_id}#{nft_id}")
    print(f"  To: {to_address[:20]}...")
    
    return client.submit_blob(data, from_account=from_account)


def transfer_nft(collection_id: str, nft_id: int, 
                 from_address: str, to_address: str,
                 from_account: str = "alice"):
    """
    转移 NFT
    只有当前拥有者才能转移
    """
    client = DockerBlobClient()
    
    data = {
        "type": "nft_transfer",
        "collection_id": collection_id,
        "nft_id": nft_id,
        "from": from_address,
        "to": to_address,
        "timestamp": int(time.time())
    }
    
    print(f"\n🔄 转移 NFT: {collection_id}#{nft_id}")
    print(f"  From: {from_address[:20]}...")
    print(f"  To: {to_address[:20]}...")
    
    return client.submit_blob(data, from_account=from_account)


def list_nft(collection_id: str, nft_id: int, 
             seller_address: str, price_utia: int,
             from_account: str = "alice"):
    """
    挂单出售 NFT
    价格单位: utia (1 TIA = 1,000,000 utia)
    """
    client = DockerBlobClient()
    
    data = {
        "type": "nft_list",
        "collection_id": collection_id,
        "nft_id": nft_id,
        "seller": seller_address,
        "price": price_utia,
        "timestamp": int(time.time())
    }
    
    print(f"\n💰 挂单 NFT: {collection_id}#{nft_id}")
    print(f"  Seller: {seller_address[:20]}...")
    print(f"  Price: {price_utia} utia ({price_utia / 1_000_000} TIA)")
    
    return client.submit_blob(data, from_account=from_account)


def cancel_listing(collection_id: str, nft_id: int,
                   seller_address: str, from_account: str = "alice"):
    """取消挂单"""
    client = DockerBlobClient()
    
    data = {
        "type": "nft_cancel_list",
        "collection_id": collection_id,
        "nft_id": nft_id,
        "seller": seller_address,
        "timestamp": int(time.time())
    }
    
    print(f"\n❌ 取消挂单: {collection_id}#{nft_id}")
    
    return client.submit_blob(data, from_account=from_account)


def buy_nft(collection_id: str, nft_id: int,
            buyer_address: str, payment_tx_hash: str = "",
            from_account: str = "bob"):
    """
    购买 NFT
    
    在真实场景中，buyer 需要先发送一笔转账给 seller，
    然后把转账的 tx_hash 作为 payment_tx_hash 传入
    """
    client = DockerBlobClient()
    
    data = {
        "type": "nft_buy",
        "collection_id": collection_id,
        "nft_id": nft_id,
        "buyer": buyer_address,
        "payment_tx_hash": payment_tx_hash or f"PAYMENT_{int(time.time())}",
        "timestamp": int(time.time())
    }
    
    print(f"\n🛒 购买 NFT: {collection_id}#{nft_id}")
    print(f"  Buyer: {buyer_address[:20]}...")
    
    return client.submit_blob(data, from_account=from_account)


# ============ 测试完整流程 ============

def test_full_flow():
    """测试完整的 NFT 生命周期"""
    collection_id = "celestia_dragons_v1"
    
    print("\n" + "="*60)
    print("🧪 开始测试完整 NFT 流程")
    print("="*60)
    
    results = []
    
    # 1. 铸造新 NFT #4 给 Alice
    print("\n【步骤 1】铸造新 NFT #4 给 Alice")
    result = mint_nft(
        collection_id=collection_id,
        nft_id=4,
        to_address=ALICE_ADDRESS,
        metadata_uri="ipfs://QmShadowDragon",
        extra={"name": "Shadow Dragon", "rarity": "mythic", "power": 99},
        from_account="alice"
    )
    if result:
        print(f"✅ 铸造成功，高度: {result['height']}")
        results.append(("mint", result))
    
    # 2. Alice 挂单出售 #1
    print("\n【步骤 2】Alice 挂单出售 #1")
    result = list_nft(
        collection_id=collection_id,
        nft_id=1,
        seller_address=ALICE_ADDRESS,
        price_utia=5_000_000,  # 5 TIA
        from_account="alice"
    )
    if result:
        print(f"✅ 挂单成功，高度: {result['height']}")
        results.append(("list", result))
    
    # 3. Bob 购买 #1
    print("\n【步骤 3】Bob 购买 #1")
    result = buy_nft(
        collection_id=collection_id,
        nft_id=1,
        buyer_address=BOB_ADDRESS,
        from_account="bob"
    )
    if result:
        print(f"✅ 购买成功，高度: {result['height']}")
        results.append(("buy", result))
    
    # 4. Bob 转移 #1 给 Validator
    print("\n【步骤 4】Bob 转移 #1 给 Validator")
    result = transfer_nft(
        collection_id=collection_id,
        nft_id=1,
        from_address=BOB_ADDRESS,
        to_address=VALIDATOR_ADDRESS,
        from_account="bob"
    )
    if result:
        print(f"✅ 转移成功，高度: {result['height']}")
        results.append(("transfer", result))
    
    print("\n" + "="*60)
    print("🎉 测试流程完成!")
    print("="*60)
    
    # 保存所有结果
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'test_flow_results.json'), 'w') as f:
        json.dump({
            'results': [(op, r) for op, r in results],
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2, default=str)
    
    print(f"\n结果已保存到: data/test_flow_results.json")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NFT 操作工具')
    parser.add_argument('action', nargs='?', default='test',
                        choices=['mint', 'transfer', 'list', 'buy', 'cancel', 'test'],
                        help='要执行的操作')
    parser.add_argument('--collection', '-c', default='celestia_dragons_v1', help='集合 ID')
    parser.add_argument('--nft-id', '-n', type=int, help='NFT ID')
    parser.add_argument('--to', help='接收地址')
    parser.add_argument('--price', type=int, help='价格 (utia)')
    
    args = parser.parse_args()
    
    if args.action == 'test':
        test_full_flow()
    else:
        print(f"执行 {args.action} 操作...")
        # 根据参数执行相应操作