"""
Celestia Blob 提交客户端
"""
import requests
import json
import base64
from typing import Optional, Dict, Any
import hashlib
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import (
    NODE_API_URL, NODE_RPC_URL, AUTH_TOKEN, 
    NAMESPACE_ID, GAS_LIMIT, GAS_FEE
)


class CelestiaBlobClient:
    """Celestia Blob 操作客户端"""
    
    def __init__(self, 
                 gateway_url: str = NODE_API_URL,
                 rpc_url: str = NODE_RPC_URL,
                 auth_token: str = AUTH_TOKEN,
                 namespace_id: str = NAMESPACE_ID):
        self.gateway_url = gateway_url.rstrip('/')
        self.rpc_url = rpc_url.rstrip('/')
        self.auth_token = auth_token
        self.namespace_id = namespace_id
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def _namespace_to_base64(self) -> str:
        """将 hex namespace 转为 base64"""
        ns_bytes = bytes.fromhex(self.namespace_id)
        return base64.b64encode(ns_bytes).decode()
    
    def submit_blob(self, data: Dict[str, Any]) -> Optional[Dict]:
        """
        提交 Blob 到 Celestia
        
        Args:
            data: 要提交的数据（会被 JSON 序列化）
        
        Returns:
            提交结果 或 None
        """
        try:
            # 1. 将数据转为 JSON 字符串，再转为 base64
            json_str = json.dumps(data, separators=(',', ':'))
            data_base64 = base64.b64encode(json_str.encode()).decode()
            
            # 2. 构造 JSON-RPC 请求
            # 使用 blob.Submit 方法
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "blob.Submit",
                "params": [
                    [
                        {
                            "namespace": self._namespace_to_base64(),
                            "data": data_base64,
                            "share_version": 0,
                            "commitment": ""  # 会自动计算
                        }
                    ],
                    {
                        "gas_limit": GAS_LIMIT,
                        "fee": GAS_FEE
                    }
                ]
            }
            
            print(f"📤 提交 Blob...")
            print(f"   Namespace: {self.namespace_id}")
            print(f"   Data size: {len(json_str)} bytes")
            
            # 3. 发送请求到 RPC
            response = requests.post(
                self.rpc_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            result = response.json()
            
            if "error" in result:
                print(f"❌ 提交失败: {result['error']}")
                return None
            
            height = result.get('result', 0)
            print(f"✅ Blob 提交成功! 区块高度: {height}")
            
            return {
                "height": height,
                "namespace": self.namespace_id,
                "data": data,
                "data_hash": hashlib.sha256(json_str.encode()).hexdigest()
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 提交失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_blobs_at_height(self, height: int) -> list:
        """
        获取指定高度的所有 Blob
        
        Args:
            height: 区块高度
        
        Returns:
            Blob 列表
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "blob.GetAll",
                "params": [
                    height,
                    [self._namespace_to_base64()]
                ]
            }
            
            response = requests.post(
                self.rpc_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            result = response.json()
            
            if "error" in result:
                # 可能是该高度没有 blob
                return []
            
            blobs = result.get('result', [])
            parsed_blobs = []
            
            for blob in blobs or []:
                try:
                    # 解码 base64 数据
                    data_bytes = base64.b64decode(blob.get('data', ''))
                    data_json = json.loads(data_bytes.decode())
                    parsed_blobs.append({
                        "namespace": blob.get('namespace'),
                        "data": data_json,
                        "commitment": blob.get('commitment'),
                        "share_version": blob.get('share_version')
                    })
                except:
                    continue
            
            return parsed_blobs
            
        except Exception as e:
            print(f"❌ 获取 Blob 失败: {e}")
            return []
    
    def get_current_height(self) -> int:
        """获取当前区块高度"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "header.LocalHead",
                "params": []
            }
            
            response = requests.post(
                self.rpc_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            header = result.get('result', {}).get('header', {})
            height = int(header.get('height', 0))
            return height
            
        except Exception as e:
            print(f"❌ 获取高度失败: {e}")
            return 0


# ============ 简化的操作函数 ============

def submit_collection(collection_data: Dict) -> Optional[Dict]:
    """提交 NFT 集合定义"""
    client = CelestiaBlobClient()
    
    # 确保数据格式正确
    if 'type' not in collection_data:
        collection_data['type'] = 'collection_definition'
    
    return client.submit_blob(collection_data)


def submit_operation(operation: str, collection_id: str, **kwargs) -> Optional[Dict]:
    """提交 NFT 操作 (mint/transfer/list/buy)"""
    client = CelestiaBlobClient()
    
    data = {
        "type": f"nft_{operation}",
        "collection_id": collection_id,
        "timestamp": int(time.time()),
        **kwargs
    }
    
    return client.submit_blob(data)


# 测试
if __name__ == "__main__":
    client = CelestiaBlobClient()
    
    # 测试获取当前高度
    height = client.get_current_height()
    print(f"📊 当前区块高度: {height}")
    
    # 测试提交 Blob
    test_data = {
        "type": "test",
        "message": "Hello Celestia!",
        "timestamp": int(time.time())
    }
    
    result = client.submit_blob(test_data)
    if result:
        print(f"📦 提交结果: {result}")
        
        # 等待几秒后查询
        time.sleep(3)
        blobs = client.get_blobs_at_height(result['height'])
        print(f"📥 该高度的 Blobs: {blobs}")