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

# Set up logging
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
    """NFT Indexer - Rebuild state from on-chain events"""
    
    def __init__(self):
        self.db = NFTDatabase()
        self.client = DockerBlobClient()
        self.running = False
    
    def process_blob(self, data: Dict, height: int, tx_hash: str = None) -> bool:
        """Process a single Blob data"""
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
                logger.debug(f"Skipping unknown type: {data_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process Blob: {e}")
            return False
    
    def _handle_collection_definition(self, data: Dict, height: int, tx_hash: str) -> bool:
       """Handle collection definition"""
        logger.info(f"📦 Found collection definition: {data.get('collection_id')}")
        
        required_fields = ['collection_id', 'issuer', 'name']
        for field in required_fields:
            if field not in data:
                logger.error(f"Collection definition missing field: {field}")
                return False
        
        data['created_at_height'] = height
        return self.db.create_collection(data, height, tx_hash)
    
    def _handle_mint(self, data: Dict, height: int, tx_hash: str) -> bool:
        """Handle mint operation"""
        logger.info(f"🎨 Found mint: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        to_addr = data.get('to')
        issuer = data.get('issuer')
        
        if not all([collection_id, nft_id, to_addr, issuer]):
            logger.error("Mint operation missing required fields")
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
        """Handle transfer operation"""
        logger.info(f"🔄 Found transfer: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        from_addr = data.get('from')
        to_addr = data.get('to')
        
        if not all([collection_id, nft_id, from_addr, to_addr]):
            logger.error("Transfer operation missing required fields")
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
        """Handle listing operation"""
        logger.info(f"💰 Found listing: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        seller = data.get('seller')
        price = data.get('price')
        
        if not all([collection_id, nft_id, seller, price]):
            logger.error("Listing operation missing required fields")
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
        """Handle cancel listing"""
        logger.info(f"❌ Found cancel listing: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        seller = data.get('seller')
        
        if not all([collection_id, nft_id, seller]):
            logger.error("Cancel listing missing required fields")
            return False
        
        return self.db.cancel_listing(
            collection_id=collection_id,
            nft_id=nft_id,
            seller=seller,
            height=height,
            tx_hash=tx_hash
        )
    
    def _handle_buy(self, data: Dict, height: int, tx_hash: str) -> bool:
        """Handle buy operation"""
        logger.info(f"🛒 Found purchase: {data.get('collection_id')}#{data.get('nft_id')}")
        
        collection_id = data.get('collection_id')
        nft_id = data.get('nft_id')
        buyer = data.get('buyer')
        
        if not all([collection_id, nft_id, buyer]):
            logger.error("Buy operation missing required fields")
            return False
        
        # Get current listing
        listing = self.db.get_active_listing(collection_id, nft_id)
        if not listing:
            logger.error(f"NFT {collection_id}#{nft_id} has no active listing")
            return False
        
        # Execute transfer (from seller to buyer)
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
        """Import data from local JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Support two formats: direct blob data, or deployment file containing collection_data
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
            logger.error(f"Failed to import file {filepath}: {e}")
            return False
    
    def import_all_from_data_dir(self):
        """Import all JSON files from data directory"""
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        if not os.path.exists(data_dir):
            logger.warning(f"Data directory does not exist: {data_dir}")
            return
        
        json_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.json')])
        
        logger.info(f"Found {len(json_files)} JSON files")
        
        for filename in json_files:
            filepath = os.path.join(data_dir, filename)
            logger.info(f"Importing: {filename}")
            self.import_from_file(filepath)


def main():
    """Main function"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║     Celestia NFT Indexer (Docker)        ║
    ╚═══════════════════════════════════════════╝
    """)
    
    indexer = NFTIndexer()
    
   # Import all data from local files
    indexer.import_all_from_data_dir()
    
    print("\n✅ Indexing complete!")
    print("You can start the API service to view data:")
    print("  uvicorn frontend.api:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
