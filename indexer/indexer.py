# indexer/indexer.py

import time
import json
import sys
import os
import logging
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import NFTDatabase
from scripts.docker_blob_client import DockerBlobClient

# 设置日志
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'logs'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'logs', 'indexer.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NFTIndexer:
    """NFT 索引器 - 从链上事件重建状态"""
    
    def __init__(self):
        self.db = NFTDatabase()
        self.client = DockerBlobClient()
        self.running = False
    
    def process_blob(self, data: Dict, height: int, tx_hash: str = None) -> bool:
        """处理单个 Blob 数据"""
        try:
            data_type = data.get('type', '')
            
            if data_type == 'collection_definition':
                return self._handle_collection_definition(data, height, tx_hash)
            elif data_type == 'nft_mint':
                return self._handle_mint(data, height, tx_hash)
            elif data_type == 'nft_transfer':
                return self._handle_transfer(data, height, tx_hash)
            elif data_type == 'nft_list':
                return self._handle_list(data, height, tx_hash)
            elif data_type == 'nft_cancel_list':
                return self._handle_cancel_list(data, height, tx_hash)
            elif data_type == 'nft_buy':
                return self._handle_buy(data, height, tx_hash)
            else:
                logger.debug(f"跳过未知类型: {data_type}")
                return False
                
        except Exception as e:
            logger.error(f"处理 Blob 失败: {e}")
            return False
    
    def _handle_collection_definition(self, data: Dict, height: int, tx_hash: str) -> bool:
        """处理集合定义"""
        logger.info(f"📦 发现集合定义: {data.get('collection_id')}")
        
        required_fields = ['collection_id', 'issuer', 'name']
        for field in required_fields:
            if field not in data:
                logger.error(f"集合定义缺少字段: {field}")
                return False
        
        data['created_at_height'] = height
        return self.db.create_collection(data, height, tx_hash)
    
    def _handle_mint(self, data: Dict, height: int, tx_hash: str) -> bool:
        """处理铸造操作"""
        logger.info(f"🎨 发现铸造: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        to_addr = data.get('to')
        issuer = data.get('issuer')
        
        if not all([collection_id, nft_id, to_addr, issuer]):
            logger.error("铸造操作缺少必要字段")
            return False
        
        return self.db.mint_nft(
            collection_id=collection_id,
            nft_id=nft_id,
            to_addr=to_addr,
            metadata_uri=data.get('metadata_uri', ''),
            extra=data.get('extra', {}),
            height=height,
            issuer=issuer,
            tx_hash=tx_hash
        )
    
    def _handle_transfer(self, data: Dict, height: int, tx_hash: str) -> bool:
        """处理转移操作"""
        logger.info(f"🔄 发现转移: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        from_addr = data.get('from')
        to_addr = data.get('to')
        
        if not all([collection_id, nft_id, from_addr, to_addr]):
            logger.error("转移操作缺少必要字段")
            return False
        
        return self.db.transfer_nft(
            collection_id=collection_id,
            nft_id=nft_id,
            from_addr=from_addr,
            to_addr=to_addr,
            height=height,
            tx_hash=tx_hash,
            tx_type="transfer"
        )
    
    def _handle_list(self, data: Dict, height: int, tx_hash: str) -> bool:
        """处理挂单操作"""
        logger.info(f"💰 发现挂单: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        seller = data.get('seller')
        price = data.get('price')
        
        if not all([collection_id, nft_id, seller, price]):
            logger.error("挂单操作缺少必要字段")
            return False
        
        return self.db.create_listing(
            collection_id=collection_id,
            nft_id=nft_id,
            seller=seller,
            price=price,
            height=height,
            tx_hash=tx_hash
        )
    
    def _handle_cancel_list(self, data: Dict, height: int, tx_hash: str) -> bool:
        """处理取消挂单"""
        logger.info(f"❌ 发现取消挂单: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        seller = data.get('seller')
        
        if not all([collection_id, nft_id, seller]):
            logger.error("取消挂单缺少必要字段")
            return False
        
        return self.db.cancel_listing(
            collection_id=collection_id,
            nft_id=nft_id,
            seller=seller,
            height=height,
            tx_hash=tx_hash
        )
    
    def _handle_buy(self, data: Dict, height: int, tx_hash: str) -> bool:
        """处理购买操作"""
        logger.info(f"🛒 发现购买: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        buyer = data.get('buyer')
        
        if not all([collection_id, nft_id, buyer]):
            logger.error("购买操作缺少必要字段")
            return False
        
        # 获取当前挂单
        listing = self.db.get_active_listing(collection_id, nft_id)
        if not listing:
            logger.error(f"NFT {collection_id}#{nft_id} 没有活跃挂单")
            return False
        
        # 执行转移（从卖家到买家）
        return self.db.transfer_nft(
            collection_id=collection_id,
            nft_id=nft_id,
            from_addr=listing['seller'],
            to_addr=buyer,
            height=height,
            tx_hash=tx_hash,
            tx_type="sale",
            price=listing['price']
        )
    
    def import_from_file(self, filepath: str) -> bool:
        """从本地 JSON 文件导入数据"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # 支持两种格式：直接的 blob 数据，或包含 collection_data 的部署文件
            if 'collection_data' in data:
                blob_data = data['collection_data']
                result = data.get('result', {})
                height = result.get('height', 1)
                tx_hash = result.get('txhash', '')
            else:
                blob_data = data
                height = data.get('height', 1)
                tx_hash = data.get('txhash', '')
            
            return self.process_blob(blob_data, height, tx_hash)
            
        except Exception as e:
            logger.error(f"导入文件失败 {filepath}: {e}")
            return False
    
    def import_all_from_data_dir(self):
        """从 data 目录导入所有 JSON 文件"""
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        if not os.path.exists(data_dir):
            logger.warning(f"数据目录不存在: {data_dir}")
            return
        
        json_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.json')])
        
        logger.info(f"找到 {len(json_files)} 个 JSON 文件")
        
        for filename in json_files:
            filepath = os.path.join(data_dir, filename)
            logger.info(f"导入: {filename}")
            self.import_from_file(filepath)


def main():
    """主函数"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║     Celestia NFT Indexer (Docker)        ║
    ╚═══════════════════════════════════════════╝
    """)
    
    indexer = NFTIndexer()
    
    # 从本地文件导入所有数据
    indexer.import_all_from_data_dir()
    
    print("\n✅ 索引完成!")
    print("你可以启动 API 服务查看数据:")
    print("  uvicorn frontend.api:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()