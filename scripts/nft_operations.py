# scripts/nft_operations.py

import json
import time
import sys
import os
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docker_blob_client import DockerBlobClient, NAMESPACE_ID


def get_address(key_name: str) -> str:
    """Get account address inside container"""
    result = subprocess.run(
        f'docker exec celestia-validator celestia-appd keys show {key_name} -a --keyring-backend test',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()


# Get addresses
ALICE_ADDRESS = get_address('alice')
BOB_ADDRESS = get_address('bob')
VALIDATOR_ADDRESS = get_address('validator')

print(f"Alice: {ALICE_ADDRESS}")
print(f"Bob: {BOB_ADDRESS}")


def mint_nft(collection_id: str, nft_id: int, to_address: str, 
             metadata_uri: str = "", extra: dict = None, 
             from_account: str = "alice"):
    """
    Mint new NFT
    Only the collection issuer can mint
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
    
    print(f"\n🎨 Minting NFT: {collection_id}#{nft_id}")
    print(f"  To: {to_address[:20]}...")
    
    return client.submit_blob(data, from_account=from_account)


def transfer_nft(collection_id: str, nft_id: int, 
                 from_address: str, to_address: str,
                 from_account: str = "alice"):
    """
    Transfer NFT
    Only the current owner can transfer
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
    
    print(f"\n🔄 Transferring NFT: {collection_id}#{nft_id}")
    print(f"  From: {from_address[:20]}...")
    print(f"  To: {to_address[:20]}...")
    
    return client.submit_blob(data, from_account=from_account)


def list_nft(collection_id: str, nft_id: int, 
             seller_address: str, price_utia: int,
             from_account: str = "alice"):
    """
    List NFT for sale
    Price unit: utia (1 TIA = 1,000,000 utia)
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
    
    print(f"\n💰 Listing NFT: {collection_id}#{nft_id}")
    print(f"  Seller: {seller_address[:20]}...")
    print(f"  Price: {price_utia} utia ({price_utia / 1_000_000} TIA)")
    
    return client.submit_blob(data, from_account=from_account)


def cancel_listing(collection_id: str, nft_id: int,
                   seller_address: str, from_account: str = "alice"):
    """Cancel listing"""
    client = DockerBlobClient()
    
    data = {
        "type": "nft_cancel_list",
        "collection_id": collection_id,
        "nft_id": nft_id,
        "seller": seller_address,
        "timestamp": int(time.time())
    }
    
    print(f"\n❌ Cancelling listing: {collection_id}#{nft_id}")
    
    return client.submit_blob(data, from_account=from_account)


def buy_nft(collection_id: str, nft_id: int,
            buyer_address: str, payment_tx_hash: str = "",
            from_account: str = "bob"):
    """
    Buy NFT
    
    In a real scenario, the buyer needs to first send a transfer to the seller,
    then pass the transfer tx_hash as payment_tx_hash
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
    
    print(f"\n🛒 Buying NFT: {collection_id}#{nft_id}")
    print(f"  Buyer: {buyer_address[:20]}...")
    
    return client.submit_blob(data, from_account=from_account)


# ============ Test Full Flow ============

def test_full_flow():
    """Test complete NFT lifecycle"""
    collection_id = "celestia_dragons_v1"
    
    print("\n" + "="*60)
    print("🧪 Starting complete NFT flow test")
    print("="*60)
    
    results = []
    
    # 1. Mint new NFT #4 to Alice
    print("\n【Step 1】Mint new NFT #4 to Alice")
    result = mint_nft(
        collection_id=collection_id,
        nft_id=4,
        to_address=ALICE_ADDRESS,
        metadata_uri="ipfs://QmShadowDragon",
        extra={"name": "Shadow Dragon", "rarity": "mythic", "power": 99},
        from_account="alice"
    )
    if result:
        print(f"✅ Mint successful, height: {result['height']}")
        results.append(("mint", result))
    
    # 2. Alice lists #1 for sale
    print("\n【Step 2】Alice lists #1 for sale")
    result = list_nft(
        collection_id=collection_id,
        nft_id=1,
        seller_address=ALICE_ADDRESS,
        price_utia=5_000_000,  # 5 TIA
        from_account="alice"
    )
    if result:
        print(f"✅ Listing successful, height: {result['height']}")
        results.append(("list", result))
    
    # 3. Bob buys #1
    print("\n【Step 3】Bob buys #1")
    result = buy_nft(
        collection_id=collection_id,
        nft_id=1,
        buyer_address=BOB_ADDRESS,
        from_account="bob"
    )
    if result:
        print(f"✅ Purchase successful, height: {result['height']}")
        results.append(("buy", result))
    
    # 4. Bob transfers #1 to Validator
    print("\n【Step 4】Bob transfers #1 to Validator")
    result = transfer_nft(
        collection_id=collection_id,
        nft_id=1,
        from_address=BOB_ADDRESS,
        to_address=VALIDATOR_ADDRESS,
        from_account="bob"
    )
    if result:
        print(f"✅ Transfer successful, height: {result['height']}")
        results.append(("transfer", result))
    
    print("\n" + "="*60)
    print("🎉 Test flow completed!")
    print("="*60)
    
    # Save all results
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'test_flow_results.json'), 'w') as f:
        json.dump({
            'results': [(op, r) for op, r in results],
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2, default=str)
    
    print(f"\nResults saved to: data/test_flow_results.json")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NFT Operations Tool')
    parser.add_argument('action', nargs='?', default='test',
                        choices=['mint', 'transfer', 'list', 'buy', 'cancel', 'test'],
                        help='Operation to execute')
    parser.add_argument('--collection', '-c', default='celestia_dragons_v1', help='Collection ID')
    parser.add_argument('--nft-id', '-n', type=int, help='NFT ID')
    parser.add_argument('--to', help='Recipient address')
    parser.add_argument('--price', type=int, help='Price (utia)')
    
    args = parser.parse_args()
    
    if args.action == 'test':
        test_full_flow()
    else:
        print(f"Executing {args.action} operation...")
        # Execute corresponding operation based on arguments
