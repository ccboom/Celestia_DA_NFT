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
