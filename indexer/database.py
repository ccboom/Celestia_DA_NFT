"""
SQLite Database Operations Module
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
        """Initialize database tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Collections table
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
        
        # NFT table
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
        
        # Listings table
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
        
        # Transfer history table
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
        
        # Indexer state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexer_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Processed transactions table (prevent duplicate processing)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_txs (
                tx_hash TEXT PRIMARY KEY,
                block_height INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Database initialized: {self.db_path}")
    
    # ================== Collection Operations ==================
    
    def create_collection(self, collection_data: Dict, height: int, tx_hash: str = None) -> bool:
        """Create NFT collection"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Check if already exists
            cursor.execute(
                "SELECT collection_id FROM collections WHERE collection_id = ?",
                (collection_data['collection_id'],)
            )
            if cursor.fetchone():
                print(f"⚠️ Collection already exists: {collection_data['collection_id']}")
                return False
            
            # Insert collection
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
            
            # If contains initial NFTs, create them
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
                    collection_data['issuer'],  # Initial owner is the issuer
                    height,
                    tx_hash
                ))
                
                # Record mint history
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
            
            # Update total supply
            cursor.execute('''
                UPDATE collections SET total_supply = ? WHERE collection_id = ?
            ''', (len(nfts), collection_data['collection_id']))
            
            conn.commit()
            print(f"✅ Collection created successfully: {collection_data['collection_id']}, NFT count: {len(nfts)}")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to create collection: {e}")
            return False
        finally:
            conn.close()
    
    def get_collection(self, collection_id: str) -> Optional[Dict]:
        """Get collection info"""
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
    
    # ================== NFT Operations ==================
    
    def get_nft(self, collection_id: str, nft_id: int) -> Optional[Dict]:
        """Get NFT info"""
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
        """Get NFT owner"""
        nft = self.get_nft(collection_id, nft_id)
        return nft['owner'] if nft else None
    
    def transfer_nft(self, collection_id: str, nft_id: int, 
                     from_addr: str, to_addr: str, 
                     height: int, tx_hash: str = None,
                     tx_type: str = "transfer", price: int = None) -> bool:
        """Transfer NFT ownership"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Verify current owner
            current_owner = self.get_nft_owner(collection_id, nft_id)
            if current_owner != from_addr:
                print(f"❌ Transfer failed: {from_addr} is not the owner of NFT #{nft_id} (current: {current_owner})")
                return False
            
            # Update owner
            cursor.execute('''
                UPDATE nfts SET owner = ?, status = 'active' 
                WHERE collection_id = ? AND nft_id = ?
            ''', (to_addr, collection_id, nft_id))
            
            # If there's a listing, cancel it
            cursor.execute('''
                UPDATE listings SET status = 'sold' 
                WHERE collection_id = ? AND nft_id = ? AND status = 'active'
            ''', (collection_id, nft_id))
            
            # Record transfer history
            cursor.execute('''
                INSERT INTO transfer_history
                (collection_id, nft_id, from_address, to_address, tx_type, price, block_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, from_addr, to_addr, tx_type, price, height, tx_hash))
            
            conn.commit()
            print(f"✅ NFT transfer successful: {collection_id}#{nft_id} {from_addr[:20]}... -> {to_addr[:20]}...")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Transfer failed: {e}")
            return False
        finally:
            conn.close()
    
    def mint_nft(self, collection_id: str, nft_id: int, to_addr: str,
                 metadata_uri: str, extra: Dict, height: int, 
                 issuer: str, tx_hash: str = None) -> bool:
        """Mint new NFT"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Verify collection exists and issuer is correct
            collection = self.get_collection(collection_id)
            if not collection:
                print(f"❌ Mint failed: Collection does not exist {collection_id}")
                return False
            
            if collection['issuer'] != issuer:
                print(f"❌ Mint failed: {issuer} is not the collection issuer")
                return False
            
            # Check if NFT ID already exists
            if self.get_nft(collection_id, nft_id):
                print(f"❌ Mint failed: NFT #{nft_id} already exists")
                return False
            
            # Insert NFT
            cursor.execute('''
                INSERT INTO nfts 
                (collection_id, nft_id, metadata_uri, extra, owner, created_at_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, metadata_uri, json.dumps(extra), to_addr, height, tx_hash))
            
            # Update total supply
            cursor.execute('''
                UPDATE collections SET total_supply = total_supply + 1 WHERE collection_id = ?
            ''', (collection_id,))
            
            # Record history
            cursor.execute('''
                INSERT INTO transfer_history
                (collection_id, nft_id, from_address, to_address, tx_type, block_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, "MINT", to_addr, "mint", height, tx_hash))
            
            conn.commit()
            print(f"✅ NFT minted successfully: {collection_id}#{nft_id} -> {to_addr[:20]}...")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Mint failed: {e}")
            return False
        finally:
            conn.close()
    
    # ================== Listing Operations ==================
    
    def create_listing(self, collection_id: str, nft_id: int, 
                       seller: str, price: int, height: int, 
                       tx_hash: str = None) -> bool:
        """Create listing"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Verify seller is the owner
            current_owner = self.get_nft_owner(collection_id, nft_id)
            if current_owner != seller:
                print(f"❌ Listing failed: {seller} is not the owner of NFT #{nft_id}")
                return False
            
            # Check if there's already an active listing
            cursor.execute('''
                SELECT id FROM listings 
                WHERE collection_id = ? AND nft_id = ? AND status = 'active'
            ''', (collection_id, nft_id))
            if cursor.fetchone():
                print(f"⚠️ NFT #{nft_id} already has an active listing, cancelling old listing")
                cursor.execute('''
                    UPDATE listings SET status = 'cancelled' 
                    WHERE collection_id = ? AND nft_id = ? AND status = 'active'
                ''', (collection_id, nft_id))
            
            # Create new listing
            cursor.execute('''
                INSERT INTO listings 
                (collection_id, nft_id, seller, price, created_at_height, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (collection_id, nft_id, seller, price, height, tx_hash))
            
            # Update NFT status
            cursor.execute('''
                UPDATE nfts SET status = 'listed' 
                WHERE collection_id = ? AND nft_id = ?
            ''', (collection_id, nft_id))
            
            conn.commit()
            print(f"✅ Listing successful: {collection_id}#{nft_id} @ {price} utia")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Listing failed: {e}")
            return False
        finally:
            conn.close()
    
    def get_active_listing(self, collection_id: str, nft_id: int) -> Optional[Dict]:
        """Get active listing"""
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
    
    # ================== Query Methods ==================
    
    def get_nfts_by_owner(self, owner: str) -> List[Dict]:
        """Get all NFTs owned by an address"""
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
        """Get all active listings"""
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
    
    # ================== Indexer State ==================
    
    def get_last_indexed_height(self) -> int:
        """Get last indexed block height"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM indexer_state WHERE key = 'last_height'")
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row else 0
    
    def set_last_indexed_height(self, height: int):
        """Set last indexed block height"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO indexer_state (key, value, updated_at)
            VALUES ('last_height', ?, CURRENT_TIMESTAMP)
        ''', (str(height),))
        conn.commit()
        conn.close()
    
    def is_tx_processed(self, tx_hash: str) -> bool:
        """Check if transaction has been processed"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT tx_hash FROM processed_txs WHERE tx_hash = ?", (tx_hash,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def mark_tx_processed(self, tx_hash: str, height: int):
        """Mark transaction as processed"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO processed_txs (tx_hash, block_height) VALUES (?, ?)
        ''', (tx_hash, height))
        conn.commit()
        conn.close()


# Test
if __name__ == "__main__":
    db = NFTDatabase()
    
    # Test create collection
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
    
    # Query
    print("\n📦 Collection info:", db.get_collection("test_collection_001"))
    print("\n🎨 NFT #1:", db.get_nft("test_collection_001", 1))
    print("\n👤 Issuer's NFTs:", db.get_nfts_by_owner("celestia1testissuer"))
