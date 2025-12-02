# frontend/api.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indexer.database import NFTDatabase
from pydantic import BaseModel
from typing import List, Optional
from scripts.docker_blob_client import submit_collection
import subprocess

app = FastAPI(
    title="Celestia NFT API",
    description="Sovereign NFT on Celestia DA - No Smart Contract",
    version="1.0.0"
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

db = NFTDatabase()


class NFTItem(BaseModel):
    id: int
    metadata_uri: str
    extra: dict = {}

class CollectionCreateRequest(BaseModel):
    collection_id: str
    name: str
    description: str = ""
    issuer: Optional[str] = None
    nfts: List[NFTItem] = []


# ============ 静态文件路由 ============

@app.get("/")
async def root():
    """返回前端页面"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": "Celestia NFT API",
        "version": "1.0.0",
        "message": "Frontend not found. API is running."
    }


# ============ API 路由 ============

@app.get("/api")
async def api_info():
    return {
        "name": "Celestia NFT API",
        "version": "1.0.0",
        "endpoints": {
            "collections": "/collections/{collection_id}",
            "nft": "/nft/{collection_id}/{nft_id}",
            "owner": "/owner/{address}",
            "listings": "/listings",
            "history": "/history/{collection_id}/{nft_id}",
            "stats": "/stats"
        }
    }


@app.get("/collections/{collection_id}")
async def get_collection(collection_id: str):
    """获取集合信息"""
    collection = db.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {
        "collection_id": collection['collection_id'],
        "issuer": collection['issuer'],
        "name": collection['name'],
        "description": collection['description'],
        "total_supply": collection['total_supply'],
        "created_at_height": collection['created_at_height']
    }


@app.get("/collections/{collection_id}/nfts")
async def get_collection_nfts(collection_id: str):
    """获取集合中的所有 NFT"""
    collection = db.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    nfts = db.get_nfts_by_collection(collection_id)
    return {
        "collection_id": collection_id,
        "total": len(nfts),
        "nfts": nfts
    }


@app.get("/nft/{collection_id}/{nft_id}")
async def get_nft(collection_id: str, nft_id: int):
    """获取 NFT 详情"""
    nft = db.get_nft(collection_id, nft_id)
    if not nft:
        raise HTTPException(status_code=404, detail="NFT not found")
    return nft


@app.get("/owner/{address}")
async def get_nfts_by_owner(address: str):
    """获取某地址拥有的所有 NFT"""
    nfts = db.get_nfts_by_owner(address)
    return {
        "owner": address,
        "total": len(nfts),
        "nfts": nfts
    }


@app.get("/listings")
async def get_all_listings():
    """获取所有活跃挂单"""
    listings = db.get_all_listings()
    return {
        "total": len(listings),
        "listings": listings
    }


@app.get("/listing/{collection_id}/{nft_id}")
async def get_listing(collection_id: str, nft_id: int):
    """获取 NFT 的活跃挂单"""
    listing = db.get_active_listing(collection_id, nft_id)
    if not listing:
        raise HTTPException(status_code=404, detail="No active listing")
    return listing


@app.get("/history/{collection_id}/{nft_id}")
async def get_transfer_history(collection_id: str, nft_id: int):
    """获取 NFT 的转移历史"""
    history = db.get_transfer_history(collection_id, nft_id)
    return {
        "collection_id": collection_id,
        "nft_id": nft_id,
        "total": len(history),
        "history": history
    }


@app.get("/stats")
async def get_stats():
    """获取统计信息"""
    return {
        "last_indexed_height": db.get_last_indexed_height(),
        "total_listings": len(db.get_all_listings()),
        "collections": db.get_all_collections_count(),
        "total_nfts": db.get_total_nfts_count()
    }
    
@app.post("/collections")
async def create_collection(req: CollectionCreateRequest):
    """
    Create a new NFT collection:
    - Sends a Blob with collection_definition JSON via DockerBlobClient
    - Optionally also imports into local DB (if you want immediate availability)
    """
    # 默认 issuer 用 Alice（容器里的 alice 地址）
    issuer = req.issuer
    if not issuer:
        # 获取 docker 容器内 alice 地址
        result = subprocess.run(
            'docker exec celestia-validator celestia-appd keys show alice -a --keyring-backend test',
            shell=True, capture_output=True, text=True
        )
        issuer = result.stdout.strip()
    
    # 构造 collection JSON
    collection_data = {
        "type": "collection_definition",
        "collection_id": req.collection_id,
        "issuer": issuer,
        "name": req.name,
        "description": req.description,
        "created_at_height": 0,
        "nfts": [nft.dict() for nft in req.nfts],
        "issuer_signature": "PLACEHOLDER"
    }
    
    # 通过 Blob 写入链上
    result = submit_collection(collection_data)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to submit blob to Celestia")
    
    # 可选：直接导入 DB，避免还要跑导入脚本
    height = result.get("height", 0)
    tx_hash = result.get("txhash", "")
    db.create_collection(collection_data, height, tx_hash)
    
    return {
        "status": "ok",
        "collection_id": req.collection_id,
        "txhash": result["txhash"],
        "height": result["height"]
    }
    
@app.get("/collections")
async def list_collections():
    """List all NFT collections"""
    collections = db.get_all_collections()
    return {
        "total": len(collections),
        "collections": collections
    }

# ============ 启动服务 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
