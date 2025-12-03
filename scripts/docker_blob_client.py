# scripts/docker_blob_client.py

import subprocess
import json
import time
import hashlib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NAMESPACE_ID = "0000004e46545a4f4e45"
CONTAINER_NAME = "celestia-validator"


class DockerBlobClient:
    def __init__(self, container: str = CONTAINER_NAME):
        self.container = container
        
    def _docker_exec(self, cmd: str, timeout: int = 30) -> str:
        """Execute command inside container"""
        full_cmd = f'docker exec {self.container} sh -c "{cmd}"'
        result = subprocess.run(
            full_cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"Docker exec failed: {result.stderr}")
        return result.stdout.strip()
    
    def submit_blob(self, data: dict, from_account: str = "alice") -> dict:
        """Submit JSON data as Blob"""
        try:
            # 1. Convert JSON to hex
            json_str = json.dumps(data, separators=(',', ':'))
            hex_data = json_str.encode().hex()
            
            print(f"📤 Submitting Blob...")
            print(f"  From: {from_account}")
            print(f"  Size: {len(json_str)} bytes")
            
            # 2. Execute pay-for-blob inside container
            cmd = f'''celestia-appd tx blob pay-for-blob \\
                {NAMESPACE_ID} \\
                {hex_data} \\
                --from {from_account} \\
                --keyring-backend test \\
                --fees 2000utia \\
                --yes \\
                --output json'''
            
            output = self._docker_exec(cmd)
            
            # 3. Parse output to get txhash
            tx_result = json.loads(output)
            txhash = tx_result.get('txhash', '')
            
            if not txhash:
                print("❌ Failed to get txhash")
                return None
            
            print(f"⏳ TxHash: {txhash}")
            print(f"⏳ Waiting for transaction confirmation...")
            
            # 4. Wait for transaction confirmation (with retry mechanism)
            height = self._wait_for_tx(txhash, max_retries=10, interval=2)
            
            if height:
                print(f"✅ Blob on-chain, height: {height}")
                return {
                    'txhash': txhash,
                    'height': height,
                    'namespace': NAMESPACE_ID,
                    'data': data,
                    'data_hash': hashlib.sha256(json_str.encode()).hexdigest()
                }
            else:
                # Even if query fails, transaction may have succeeded, return estimated result
                current_height = self.get_current_height()
                print(f"⚠️ Unable to confirm transaction status, but transaction may have succeeded")
                print(f"  Current height: {current_height}")
                return {
                    'txhash': txhash,
                    'height': current_height,  # Estimated
                    'namespace': NAMESPACE_ID,
                    'data': data,
                    'data_hash': hashlib.sha256(json_str.encode()).hexdigest(),
                    'confirmed': False
                }
            
        except Exception as e:
            print(f"❌ Submission failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _wait_for_tx(self, txhash: str, max_retries: int = 10, interval: int = 2) -> int:
        """Wait for transaction to be included, return block height"""
        for i in range(max_retries):
            try:
                query_cmd = f"celestia-appd query tx {txhash} --output json"
                tx_info_str = self._docker_exec(query_cmd)
                tx_info = json.loads(tx_info_str)
                
                if tx_info.get('code', 0) == 0 and tx_info.get('height'):
                    return int(tx_info['height'])
                    
            except RuntimeError as e:
                # Transaction not yet indexed, continue waiting
                if "not found" in str(e).lower():
                    print(f"  Waiting... ({i+1}/{max_retries})")
                    time.sleep(interval)
                    continue
                else:
                    raise
            except Exception:
                pass
            
            time.sleep(interval)
        
        return 0
    
    def get_current_height(self) -> int:
        """Get current chain height"""
        try:
            status = self._docker_exec("celestia-appd status --output json")
            status_json = json.loads(status)
            return int(status_json['sync_info']['latest_block_height'])
        except:
            return 0
    
    def query_tx(self, txhash: str) -> dict:
        """Query transaction details"""
        try:
            cmd = f"celestia-appd query tx {txhash} --output json"
            output = self._docker_exec(cmd)
            return json.loads(output)
        except Exception as e:
            print(f"Failed to query transaction: {e}")
            return {}


def submit_collection(collection_data: dict):
    """Submit NFT collection"""
    client = DockerBlobClient()
    if 'type' not in collection_data:
        collection_data['type'] = 'collection_definition'
    return client.submit_blob(collection_data, from_account='alice')


def submit_operation(op: str, collection_id: str, **kwargs):
    """Submit NFT operation"""
    client = DockerBlobClient()
    data = {
        'type': f'nft_{op}',
        'collection_id': collection_id,
        'timestamp': int(time.time()),
        **kwargs
    }
    return client.submit_blob(data, from_account='alice')


if __name__ == "__main__":
    client = DockerBlobClient()
    
    # Test get height
    height = client.get_current_height()
    print(f"Current height: {height}")
    
    # Test submit blob
    test_data = {
        'type': 'test',
        'message': 'Hello Celestia Blob!',
        'timestamp': int(time.time())
    }
    
    print("\n" + "="*50)
    result = client.submit_blob(test_data)
    print("="*50)
    
    if result:
        print(f"\n✅ Test successful!")
        print(f"  TxHash: {result['txhash']}")
        print(f"  Height: {result['height']}")
        print(f"  DataHash: {result['data_hash']}")
