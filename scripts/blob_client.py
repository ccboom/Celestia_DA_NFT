"""
Celestia Blob Submission Client
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
    """Celestia Blob Operations Client"""
    
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
        """Convert hex namespace to base64"""
        ns_bytes = bytes.fromhex(self.namespace_id)
        return base64.b64encode(ns_bytes).decode()
    
    def submit_blob(self, data: Dict[str, Any]) -> Optional[Dict]:
        """
        Submit Blob to Celestia
        
        Args:
            data: Data to submit (will be JSON serialized)
        
        Returns:
            Submission result or None
        """
        try:
            # 1. Convert data to JSON string, then to base64
            json_str = json.dumps(data, separators=(',', ':'))
            data_base64 = base64.b64encode(json_str.encode()).decode()
            
            # 2. Construct JSON-RPC request
            # Use blob.Submit method
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
                            "commitment": ""  # Will be calculated automatically
                        }
                    ],
                    {
                        "gas_limit": GAS_LIMIT,
                        "fee": GAS_FEE
                    }
                ]
            }
            
            print(f"📤 Submitting Blob...")
            print(f"   Namespace: {self.namespace_id}")
            print(f"   Data size: {len(json_str)} bytes")
            
            # 3. Send request to RPC
            response = requests.post(
                self.rpc_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            result = response.json()
            
            if "error" in result:
                print(f"❌ Submission failed: {result['error']}")
                return None
            
            height = result.get('result', 0)
            print(f"✅ Blob submitted successfully! Block height: {height}")
            
            return {
                "height": height,
                "namespace": self.namespace_id,
                "data": data,
                "data_hash": hashlib.sha256(json_str.encode()).hexdigest()
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
        except Exception as e:
            print(f"❌ Submission failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_blobs_at_height(self, height: int) -> list:
        """
        Get all Blobs at specified height
        
        Args:
            height: Block height
        
        Returns:
            List of Blobs
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
                # Possibly no blob at this height
                return []
            
            blobs = result.get('result', [])
            parsed_blobs = []
            
            for blob in blobs or []:
                try:
                    # Decode base64 data
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
            print(f"❌ Failed to get Blob: {e}")
            return []
    
    def get_current_height(self) -> int:
        """Get current block height"""
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
            print(f"❌ Failed to get height: {e}")
            return 0


# ============ Simplified Operation Functions ============

def submit_collection(collection_data: Dict) -> Optional[Dict]:
    """Submit NFT collection definition"""
    client = CelestiaBlobClient()
    
    # Ensure data format is correct
    if 'type' not in collection_data:
        collection_data['type'] = 'collection_definition'
    
    return client.submit_blob(collection_data)


def submit_operation(operation: str, collection_id: str, **kwargs) -> Optional[Dict]:
    """Submit NFT operation (mint/transfer/list/buy)"""
    client = CelestiaBlobClient()
    
    data = {
        "type": f"nft_{operation}",
        "collection_id": collection_id,
        "timestamp": int(time.time()),
        **kwargs
    }
    
    return client.submit_blob(data)


# Test
if __name__ == "__main__":
    client = CelestiaBlobClient()
    
    # Test get current height
    height = client.get_current_height()
    print(f"📊 Current block height: {height}")
    
    # Test submit Blob
    test_data = {
        "type": "test",
        "message": "Hello Celestia!",
        "timestamp": int(time.time())
    }
    
    result = client.submit_blob(test_data)
    if result:
        print(f"📦 Submission result: {result}")
        
        # Wait a few seconds then query
        time.sleep(3)
        blobs = client.get_blobs_at_height(result['height'])

        print(f"📥 Blobs at this height: {blobs}")
