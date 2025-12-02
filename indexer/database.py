"""
SQLite 数据库操作模块
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DATABASE_PATH



class NFTDatabase:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_dir()
        self._init_tables()
    
    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
    
    def _init_tables(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 集合表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collections (
                collection_id TEXT PRIMARY KEY,
                issuer TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at_height INTEGER NOT NULL,
                total_supply INTEGER DEFAULT 0,
                raw_json TEXT NOT NULL,
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # NFT 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nfts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id TEXT NOT NULL,
                nft_id INTEGER NOT NULL,
                metadata_uri TEXT,
                extra TEXT,
                owner TEXT NOT NULL,
                status TEXT DEFAULT 'active',  -- active, listed, burned
                created_at_height INTEGER NOT NULL,
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(collection_id, nft_id),
                FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
            )
        ''')
        
        # 挂单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id TEXT NOT NULL,
                nft_id INTEGER NOT NULL,
                seller TEXT NOT NULL,
                price INTEGER NOT NULL,  -- utia
                status TEXT DEFAULT 'active',  -- active, sold, cancelled
                created_at_height INTEGER NOT NULL,
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
            )
        ''')
        
        # 交易历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transfer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id TEXT NOT NULL,
                nft_id INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                tx_type TEXT NOT NULL,  -- mint, transfer, sale
                price INTEGER,
                block_height INTEGER NOT NULL,
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 索引器状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexer_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 处理过的交易表 (防止重复处理)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_txs (
                tx_hash TEXT PRIMARY KEY,
                block_height INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ 数据库初始化完成: {self.db_path}")
    
    # ================== 集合操作 ==================
    
    def create_collection(self, collection_data: Dict, height: int, tx_hash: str = None) -> bool:
        """创建 NFT 集合"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 检查是否已存在
            cursor.execute(
                "SELECT collection_id FROM collections WHERE collection_id = ?",
                (collection_data['collection_id'],)
            )
            if cursor.fetchone():
                print(f"⚠️ 集合已存在: {collection_data['collection_id']}")
                return False
            
            # 插入集合
            cursor.execute('''
                INSERT INTO collections 
                (collection_id, issuer, name, description, created_at_height, raw_json, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                collection_data['collection_id'],
                collection_data['issuer'],
                collection_data['name'],
                collection_data.get('description', ''),
                height,
                json.dumps(collection_data),
                tx_hash
            ))
            
            # 如果包含初始 NFT，则创建它们
            nfts = collection_data.get('nfts', [])
            for nft in nfts:
                cursor.execute('''
                    INSERT INTO nfts 
                    (collection_id, nft_id, metadata_uri, extra, owner, created_at_height, tx_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    collection_data['collection_id'],
                    nft['id'],
                    nft.get('metadata_uri', ''),
                    json.dumps(nft.get('extra', {})),
                    collection_data['issuer'],  # 初始拥有者是发行者
                    height,
                    tx_hash
                ))
                
                # 记录铸造历史
                cursor.execute('''
                    INSERT INTO transfer_history
                    (collection_id, nft_id, from_address, to_address, tx_type, block_height, tx_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    collection_data['collection_id'],
                    nft['id'],
                    "GENESIS",
                    collection_data['issuer'],
                    "mint",
                    height,
                    tx_hash
                ))
            
            # 更新总供应量
            cursor.execute('''
                UPDATE collections SET total_supply = ? WHERE collection_id = ?
            ''', (len(nfts), collection_data['collection_id']))
            
            conn.commit()
            print(f"✅ 集合创建成功: {collection_data['collection_id']}, NFT数量: {len(nfts)}")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 创建集合失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_collection(self, collection_id: str) -> Optional[Dict]:
        """获取集合信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM collections WHERE collection_id = ?",
            (collection_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'collection_id': row[0],
                'issuer': row[1],
                'name': row[2],
                'description': row[3],
                'created_at_height': row[4],
                'total_supply': row[5],
                'raw_json': json.loads(row[6]),
                'tx_hash': row[7],
                'created_at': row[8]
            }
        return None
        
    def get_all_collections(self) -> List[Dict]:
        """Get all collections"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT collection_id, issuer, name, description, created_at_height, total_supply FROM collections ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "collection_id": row[0],
                "issuer": row[1],
                "name": row[2],
                "description": row[3],
                "created_at_height": row[4],
                "total_supply": row[5],
            }
            for row in rows
        ]
    
    # ================== NFT 操作 ==================
    
    def get_nft(self, collection_id: str, nft_id: int) -> Optional[Dict]:
        """获取 NFT 信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM nfts WHERE collection_id = ? AND nft_id = ?",
            (collection_id, nft_id)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'collection_id': row[1],
                'nft_id': row[2],
                'metadata_uri': row[3],
                'extra': json.loads(row[4]) if row[4] else {},
                'owner': row[5],
                'status': row[6],
                'created_at_height': row[7],
                'tx_hash': row[8],
                'created_at': row[9]
            }
        return None
        
    def get_nfts_by_collection(self, collection_id: str) -> List[Dict]:
        """Get all NFTs in a collection"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM nfts WHERE collection_id = ? ORDER BY nft_id",
            (collection_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        nfts = []
        for row in rows:
            nfts.append({
                'id': row[0],
                'collection_id': row[1],
                'nft_id': row[2],
                'metadata_uri': row[3],
                'extra': json.loads(row[4]) if row[4] else {},
                'owner': row[5],
                'status': row[6],
                'created_at_height': row[7],
                'tx_hash': row[8],
                'created_at': row[9],
            })
        return nfts
        
        
    def get_all_collections_count(self) -> int:
        """Get total number of collections"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM collections")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_total_nfts_count(self) -> int:
        """Get total number of NFTs"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nfts")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_nft_owner(self, collection_id: str, nft_id: int) -> Optional[str]:
        """获取 NFT 拥有者"""
        nft = self.get_nft(collection_id, nft_id)
        return nft['owner'] if nft else None
    
    def transfer_nft(self, collection_id: str, nft_id: int, 
                     from_addr: str, to_addr: str, 
                     height: int, tx_hash: str = None,
                     tx_type: str = "transfer", price: int = None) -> bool:
        """转移 NFT 所有权"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 验证当前拥有者
            current_owner = self.get_nft_owner(collection_id, nft_id)
            if current_owner != from_addr:
                print(f"❌ 转移失败: {from_addr} 不是 NFT #{nft_id} 的拥有者 (当前: {current_owner})")
                return False
            
            # 更新拥有者
            cursor.execute('''
                UPDATE nfts SET owner = ?, status = 'active' 
                WHERE collection_id = ? AND nft_id = ?
            ''', (to_addr, collection_id, nft_id))
            
            # 如果有挂单，取消它
            cursor.execute('''
                UPDATE listings SET status = 'sold' 
                WHERE collection_id = ? AND nft_id = ? AND status = 'active'
            ''', (collection_id, nft_id))
            
            # 记录转移历史
            cursor.execute('''
                INSERT INTO transfer_history
                (collection_id, nft_id, from_address, to_address, tx_type, price, block_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, from_addr, to_addr, tx_type, price, height, tx_hash))
            
            conn.commit()
            print(f"✅ NFT 转移成功: {collection_id}#{nft_id} {from_addr[:20]}... -> {to_addr[:20]}...")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 转移失败: {e}")
            return False
        finally:
            conn.close()
    
    def mint_nft(self, collection_id: str, nft_id: int, to_addr: str,
                 metadata_uri: str, extra: Dict, height: int, 
                 issuer: str, tx_hash: str = None) -> bool:
        """铸造新 NFT"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 验证集合存在且发行者正确
            collection = self.get_collection(collection_id)
            if not collection:
                print(f"❌ 铸造失败: 集合不存在 {collection_id}")
                return False
            
            if collection['issuer'] != issuer:
                print(f"❌ 铸造失败: {issuer} 不是集合发行者")
                return False
            
            # 检查 NFT ID 是否已存在
            if self.get_nft(collection_id, nft_id):
                print(f"❌ 铸造失败: NFT #{nft_id} 已存在")
                return False
            
            # 插入 NFT
            cursor.execute('''
                INSERT INTO nfts 
                (collection_id, nft_id, metadata_uri, extra, owner, created_at_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, metadata_uri, json.dumps(extra), to_addr, height, tx_hash))
            
            # 更新总供应量
            cursor.execute('''
                UPDATE collections SET total_supply = total_supply + 1 WHERE collection_id = ?
            ''', (collection_id,))
            
            # 记录历史
            cursor.execute('''
                INSERT INTO transfer_history
                (collection_id, nft_id, from_address, to_address, tx_type, block_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, "MINT", to_addr, "mint", height, tx_hash))
            
            conn.commit()
            print(f"✅ NFT 铸造成功: {collection_id}#{nft_id} -> {to_addr[:20]}...")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 铸造失败: {e}")
            return False
        finally:
            conn.close()
    
    # ================== 挂单操作 ==================
    
    def create_listing(self, collection_id: str, nft_id: int, 
                       seller: str, price: int, height: int, 
                       tx_hash: str = None) -> bool:
        """创建挂单"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 验证卖家是拥有者
            current_owner = self.get_nft_owner(collection_id, nft_id)
            if current_owner != seller:
                print(f"❌ 挂单失败: {seller} 不是 NFT #{nft_id} 的拥有者")
                return False
            
            # 检查是否已有活跃挂单
            cursor.execute('''
                SELECT id FROM listings 
                WHERE collection_id = ? AND nft_id = ? AND status = 'active'
            ''', (collection_id, nft_id))
            if cursor.fetchone():
                print(f"⚠️ NFT #{nft_id} 已有活跃挂单，取消旧挂单")
                cursor.execute('''
                    UPDATE listings SET status = 'cancelled' 
                    WHERE collection_id = ? AND nft_id = ? AND status = 'active'
                ''', (collection_id, nft_id))
            
            # 创建新挂单
            cursor.execute('''
                INSERT INTO listings 
                (collection_id, nft_id, seller, price, created_at_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, seller, price, height, tx_hash))
            
            # 更新 NFT 状态
            cursor.execute('''
                UPDATE nfts SET status = 'listed' 
                WHERE collection_id = ? AND nft_id = ?
            ''', (collection_id, nft_id))
            
            conn.commit()
            print(f"✅ 挂单成功: {collection_id}#{nft_id} @ {price} utia")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 挂单失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_active_listing(self, collection_id: str, nft_id: int) -> Optional[Dict]:
        """获取活跃挂单"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM listings 
            WHERE collection_id = ? AND nft_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        ''', (collection_id, nft_id))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'collection_id': row[1],
                'nft_id': row[2],
                'seller': row[3],
                'price': row[4],
                'status': row[5],
                'created_at_height': row[6],
                'tx_hash': row[7],
                'created_at': row[8]
            }
        return None
    
    # ================== 查询方法 ==================
    
    def get_nfts_by_owner(self, owner: str) -> List[Dict]:
        """获取某地址拥有的所有 NFT"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nfts WHERE owner = ?", (owner,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'collection_id': row[1],
            'nft_id': row[2],
            'metadata_uri': row[3],
            'extra': json.loads(row[4]) if row[4] else {},
            'owner': row[5],
            'status': row[6]
        } for row in rows]
    
    def get_all_listings(self) -> List[Dict]:
        """获取所有活跃挂单"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT l.*, n.metadata_uri 
            FROM listings l
            JOIN nfts n ON l.collection_id = n.collection_id AND l.nft_id = n.nft_id
            WHERE l.status = 'active'
            ORDER BY l.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'collection_id': row[1],
            'nft_id': row[2],
            'seller': row[3],
            'price': row[4],
            'metadata_uri': row[9]
        } for row in rows]
    
    # ================== 索引器状态 ==================
    
    def get_last_indexed_height(self) -> int:
        """获取最后索引的区块高度"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM indexer_state WHERE key = 'last_height'")
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row else 0
    
    def set_last_indexed_height(self, height: int):
        """设置最后索引的区块高度"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO indexer_state (key, value, updated_at)
            VALUES ('last_height', ?, CURRENT_TIMESTAMP)
        ''', (str(height),))
        conn.commit()
        conn.close()
    
    def is_tx_processed(self, tx_hash: str) -> bool:
        """检查交易是否已处理"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT tx_hash FROM processed_txs WHERE tx_hash = ?", (tx_hash,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def mark_tx_processed(self, tx_hash: str, height: int):
        """标记交易已处理"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO processed_txs (tx_hash, block_height) VALUES (?, ?)
        ''', (tx_hash, height))
        conn.commit()
        conn.close()


# 测试
if __name__ == "__main__":
    db = NFTDatabase()
    
    # 测试创建集合
    test_collection = {
        "type": "collection_definition",
        "collection_id": "test_collection_001",
        "issuer": "celestia1testissuer",
        "name": "Test NFT Collection",
        "description": "A test collection",
        "nfts": [
            {"id": 1, "metadata_uri": "ipfs://test1", "extra": {}},
            {"id": 2, "metadata_uri": "ipfs://test2", "extra": {"rarity": "rare"}}
        ]
    }
    
    db.create_collection(test_collection, 100, "test_tx_hash")
    
    # 查询
    print("\n📦 集合信息:", db.get_collection("test_collection_001"))
    print("\n🎨 NFT #1:", db.get_nft("test_collection_001", 1))
    print("\n👤 issuer 的 NFT:", db.get_nfts_by_owner("celestia1testissuer"))