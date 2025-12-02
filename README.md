# Celestia Sovereign NFT (Local Devnet + Docker)

A fully sovereign, smart-contract-free NFT protocol built directly on **Celestia DA**, using:

- **Blob data** (`MsgPayForBlobs`) for on-chain permanence  
- **Python + SQLite** as the off-chain state machine / indexer  
- **FastAPI + HTML frontend** for visualization  
- **Dockerized Celestia devnet** (`celestia-app` validator) as the execution environment  

No EVM, no CosmWasm, no smart contracts — just raw data, a protocol, and your own indexer.

---

## ✨ Features

- **NFT Collections as pure JSON blobs** stored via `MsgPayForBlobs`
- **Mint / Transfer / List / Buy** implemented entirely in Python off-chain logic
- **Deterministic JSON protocol**:
  - `collection_definition`
  - `nft_mint`
  - `nft_transfer`
  - `nft_list`
  - `nft_cancel_list`
  - `nft_buy`
- **Local Docker devnet**:
  - `celestia-app` validator with blob module
- **SQLite indexer**:
  - Rebuilds NFT state from blobs / JSON
- **REST API + frontend**:
  - `/collections`, `/nft`, `/owner`, `/listings`, `/history`, `/stats`
  - Single-page HTML UI (no JS frameworks)

This is essentially a **Sovereign Rollup-style NFT system** on top of Celestia DA.

---

## 🧱 Architecture Overview

### Data Layer (DA)

- **Celestia App (Docker)**  
  - Image: `ghcr.io/celestiaorg/celestia-app:latest`  
  - Chain ID: `private`  
  - We use `celestia-appd tx blob pay-for-blob` to write arbitrary JSON data as **Blobs**.

Each Blob contains a JSON payload conforming to your custom protocol:

```jsonc
// Example: collection_definition
{
  "type": "collection_definition",
  "collection_id": "celestia_dragons_v1",
  "issuer": "celestia1alice...",
  "name": "Celestia Dragons Collection",
  "description": "Dragon NFTs on Celestia DA",
  "created_at_height": 0,
  "nfts": [
    {
      "id": 1,
      "metadata_uri": "ipfs://QmFireDragon",
      "extra": {"name": "Fire Dragon", "rarity": "legendary", "power": 95}
    }
  ],
  "issuer_signature": "PLACEHOLDER"
}
```

### Logic Layer (Off-chain)

- **Python indexer** (`indexer/indexer.py`, `indexer/database.py`)
  - Parses JSON blobs (from local files in this demo)
  - Maintains a SQLite database with:
    - `collections`
    - `nfts`
    - `listings`
    - `transfer_history`

- **NFT operations** (`scripts/nft_operations.py`)
  - `nft_mint`
  - `nft_transfer`
  - `nft_list`, `nft_cancel_list`
  - `nft_buy`
  - All are implemented as JSON payloads written as blobs via `celestia-appd` in Docker.

### Execution / Runtime

- **Docker** (`docker-compose.yml`)
  - `celestia-validator`: celestia-app (consensus + blob module)
    - Ports:
      - `26657`: RPC
      - `19090`: gRPC
      - `1317`: REST API
  - `celestia-bridge`: optional, can be used for DA/light-like access (not strictly required in final design)

### API Layer

- **FastAPI** (`frontend/api.py`)
  - Serves `index.html` (SPA) at `/`
  - JSON endpoints:
    - `GET /collections` — list all collections
    - `GET /collections/{id}` — collection info
    - `GET /collections/{id}/nfts` — NFTs in collection
    - `GET /nft/{collection_id}/{nft_id}` — NFT details
    - `GET /owner/{address}` — NFTs owned by address
    - `GET /listings` — active listings
    - `GET /history/{collection_id}/{nft_id}` — transfer history
    - `GET /stats` — global stats
    - `POST /collections` — create new collection (writes blob + imports to DB)

### Frontend

- `frontend/static/index.html`
  - A simple, modern, single-page UI (HTML + CSS + vanilla JS) that:
    - Shows stats cards: total collections, total NFTs, active listings, indexed height
    - Displays collection cards
    - Shows all NFTs in a grid with emoji art
    - Lists marketplace listings
    - Displays recent transaction history
    - Modal popup for NFT details

---

## 📦 Project Structure
celestia-nft-project/
├── config/
│   └── config.py              # Global config (namespace, DB path, etc.)
├── scripts/
│   ├── docker_blob_client.py  # Docker-based Blob submission client
│   ├── deploy_collection.py   # Deploy initial NFT collection as a blob
│   └── nft_operations.py      # Mint / Transfer / List / Buy operations
├── indexer/
│   ├── database.py            # SQLite schema & access layer
│   ├── indexer.py             # Import & apply blobs to DB
│   └── import_operations.py   # Import test flow results into DB
├── frontend/
│   ├── api.py                 # FastAPI server (API + static index.html)
│   └── static/
│       └── index.html         # SPA frontend
├── data/
│   ├── nft.db                 # SQLite DB
│   ├── deploy_celestia_dragons_v1.json  # Deployment metadata
│   └── test_flow_results.json           # Test operations results
├── logs/
│   ├── indexer.log
│   └── api.log
└── docker-compose.yml         # celestia-app validator + optional bridge

# 🚀 Getting Started

## 1. Prerequisites

- Linux / WSL / macOS  
- Docker & Docker Compose  
- Python 3.10+ & virtualenv  

**Install Docker & Compose (Ubuntu example):**

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Re-login or `newgrp docker` to apply group change

## 2. Clone & Setup Python Environment

**环境克隆与 Python 环境配置**

```bash
git clone <this-repo-url> celestia-nft-project
cd celestia-nft-project

python3 -m venv venv
source venv/bin/activate

# 如果项目有 requirements.txt，可以使用：
# pip install -r requirements.txt

pip install fastapi uvicorn aiosqlite requests


## 3. Start Local Celestia Devnet (Docker)

```bash
cd ~/celestia-local-devnet   # or wherever your docker-compose.yml is
docker-compose up -d

docker-compose ps
docker-compose logs celestia-validator | tail -n 20

```markdown
Verify endpoints:
```bash
# Consensus RPC
curl -s http://localhost:26657/status | jq '.result.sync_info.latest_block_height'

# REST API
curl -s http://localhost:1317/cosmos/base/tendermint/v1beta1/node_info | jq '.node_info.network'
```markdown

## 4. Test Blob Client
```bash
cd ~/celestia-nft-project
source venv/bin/activate

python scripts/docker_blob_client.py
```markdown
You should see a blob submitted and included in a block.
## 5. Deploy Initial Collection
```bash
python scripts/deploy_collection.py

```markdown
This submits a `collection_definition` blob and saves deployment info under `data/deploy_celestia_dragons_v1.json`.
## 6. Run Test Flow (Mint / List / Buy / Transfer)
```bash
python scripts/nft_operations.py test

```markdown
This will:

- Mint NFT `#4` to Alice  
- List NFT `#1` for sale  
- Bob buys NFT `#1`  
- Bob transfers NFT `#1` to Validator
Results are saved in `data/test_flow_results.json`.
## 7. Import Data into SQLite
```bash
# Import test flow operations into DB
python indexer/import_operations.py

```markdown
This populates `data/nft.db` with:

- Collections  
- NFTs  
- Listings  
- Transfer history
## 8. Start API Server
```bash
uvicorn frontend.api:app --host 0.0.0.0 --port 8000

```markdown
Now you can:

- Visit <http://localhost:8000> for the frontend
Query API:
```bash
curl http://localhost:8000/stats
curl http://localhost:8000/collections
curl http://localhost:8000/collections/celestia_dragons_v1
curl http://localhost:8000/collections/celestia_dragons_v1/nfts
curl http://localhost:8000/nft/celestia_dragons_v1/1
curl http://localhost:8000/listings

```markdown
## 🧪 How to Add a New Collection
You can add a new collection via HTTP:
```bash
curl -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "celestia_robots_v1",
    "name": "Celestia Robots",
    "description": "Robots on Celestia DA",
    "nfts": [
      {
        "id": 1,
        "metadata_uri": "ipfs://QmRobot1",
        "extra": {"name": "Robot Alpha", "rarity": "epic"}
      },
      {
        "id": 2,
        "metadata_uri": "ipfs://QmRobot2",
        "extra": {"name": "Robot Beta", "rarity": "rare"}
      }
    ]
  }'
```bash
curl -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "celestia_robots_v1",
    "name": "Celestia Robots",
    "description": "Robots on Celestia DA",
    "nfts": [
      {
        "id": 1,
        "metadata_uri": "ipfs://QmRobot1",
        "extra": {"name": "Robot Alpha", "rarity": "epic"}
      },
      {
        "id": 2,
        "metadata_uri": "ipfs://QmRobot2",
        "extra": {"name": "Robot Beta", "rarity": "rare"}
      }
    ]
  }'
## 🔮 Extensions & Ideas
### Signature verification

- Extract actual signer from tx (`/cosmos.tx.v1beta1.Tx`)  
- Enforce mint/transfer/list/buy permissions based on real on-chain signatures
### Multi-namespace support

Use different Celestia namespaces for:

- Different collections  
- Different protocol versions
### Indexer from live chain

Instead of importing from JSON files, parse txs directly from:

- `celestia-appd query txs --events ...`  
- `celestia.blob.v1.EventPayForBlobs` events
### Front-end improvements

- Add “Create Collection” form in UI  
- Direct mint & transfer from browser via calling your API
## 🤝 Contributing
This project is intentionally minimal and “geeky” — it shows how you can:

- Build a complete NFT protocol purely as data + off-chain logic on Celestia.
PRs, ideas and extensions are welcome, especially around:

- Better validation / signature checking  
- Cleaner devnet / Docker setup  
- Alternative frontends (React/Vue/Svelte)  
- Indexer performance & robustness improvements




