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
        """在容器内执行命令"""
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
        """提交 JSON 数据作为 Blob"""
        try:
            # 1. 将 JSON 转为 hex
            json_str = json.dumps(data, separators=(',', ':'))
            hex_data = json_str.encode().hex()
            
            print(f"📤 提交 Blob...")
            print(f"  From: {from_account}")
            print(f"  Size: {len(json_str)} bytes")
            
            # 2. 在容器内执行 pay-for-blob
            cmd = f'''celestia-appd tx blob pay-for-blob \\
                {NAMESPACE_ID} \\
                {hex_data} \\
                --from {from_account} \\
                --keyring-backend test \\
                --fees 2000utia \\
                --yes \\
                --output json'''
            
            output = self._docker_exec(cmd)
            
            # 3. 解析输出获取 txhash
            tx_result = json.loads(output)
            txhash = tx_result.get('txhash', '')
            
            if not txhash:
                print("❌ 未获取到 txhash")
                return None
            
            print(f"⏳ TxHash: {txhash}")
            print(f"⏳ 等待交易确认...")
            
            # 4. 等待交易确认（重试机制）
            height = self._wait_for_tx(txhash, max_retries=10, interval=2)
            
            if height:
                print(f"✅ Blob 已上链，高度: {height}")
                return {
                    'txhash': txhash,
                    'height': height,
                    'namespace': NAMESPACE_ID,
                    'data': data,
                    'data_hash': hashlib.sha256(json_str.encode()).hexdigest()
                }
            else:
                # 即使查询失败，交易可能已经成功，返回预估结果
                current_height = self.get_current_height()
                print(f"⚠️ 无法确认交易状态，但交易可能已成功")
                print(f"  当前高度: {current_height}")
                return {
                    'txhash': txhash,
                    'height': current_height,  # 预估
                    'namespace': NAMESPACE_ID,
                    'data': data,
                    'data_hash': hashlib.sha256(json_str.encode()).hexdigest(),
                    'confirmed': False
                }
            
        except Exception as e:
            print(f"❌ 提交失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _wait_for_tx(self, txhash: str, max_retries: int = 10, interval: int = 2) -> int:
        """等待交易被打包，返回区块高度"""
        for i in range(max_retries):
            try:
                query_cmd = f"celestia-appd query tx {txhash} --output json"
                tx_info_str = self._docker_exec(query_cmd)
                tx_info = json.loads(tx_info_str)
                
                if tx_info.get('code', 0) == 0 and tx_info.get('height'):
                    return int(tx_info['height'])
                    
            except RuntimeError as e:
                # 交易还没被索引，继续等待
                if "not found" in str(e).lower():
                    print(f"  等待中... ({i+1}/{max_retries})")
                    time.sleep(interval)
                    continue
                else:
                    raise
            except Exception:
                pass
            
            time.sleep(interval)
        
        return 0
    
    def get_current_height(self) -> int:
        """获取当前链高度"""
        try:
            status = self._docker_exec("celestia-appd status --output json")
            status_json = json.loads(status)
            return int(status_json['sync_info']['latest_block_height'])
        except:
            return 0
    
    def query_tx(self, txhash: str) -> dict:
        """查询交易详情"""
        try:
            cmd = f"celestia-appd query tx {txhash} --output json"
            output = self._docker_exec(cmd)
            return json.loads(output)
        except Exception as e:
            print(f"查询交易失败: {e}")
            return {}


def submit_collection(collection_data: dict):
    """提交 NFT 集合"""
    client = DockerBlobClient()
    if 'type' not in collection_data:
        collection_data['type'] = 'collection_definition'
    return client.submit_blob(collection_data, from_account='alice')


def submit_operation(op: str, collection_id: str, **kwargs):
    """提交 NFT 操作"""
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
    
    # 测试获取高度
    height = client.get_current_height()
    print(f"当前高度: {height}")
    
    # 测试提交 blob
    test_data = {
        'type': 'test',
        'message': 'Hello Celestia Blob!',
        'timestamp': int(time.time())
    }
    
    print("\n" + "="*50)
    result = client.submit_blob(test_data)
    print("="*50)
    
    if result:
        print(f"\n✅ 测试成功!")
        print(f"  TxHash: {result['txhash']}")
        print(f"  Height: {result['height']}")
        print(f"  DataHash: {result['data_hash']}")