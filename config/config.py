# config/config.py

import os
import subprocess

# Docker container name
CONTAINER_NAME = "celestia-validator"

# Namespace (10 bytes = 20 hex)
NAMESPACE_ID = "0000004e46545a4f4e45"

# Database path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nft.db")

# Indexer configuration
START_HEIGHT = 1
INDEXER_POLL_INTERVAL = 3

# Get account address inside the Docker container
def get_address(key_name: str) -> str:
    try:
        result = subprocess.run(
            f'docker exec {CONTAINER_NAME} celestia-appd keys show {key_name} -a --keyring-backend test',
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except:
        return f"celestia1{key_name}_placeholder"

# Account addresses (retrieved at startup)
VALIDATOR_ADDRESS = get_address('validator')
ALICE_ADDRESS = get_address('alice')
BOB_ADDRESS = get_address('bob')

ISSUER_ADDRESS = ALICE_ADDRESS

# Gas configuration
GAS_LIMIT = 200000

GAS_FEE = 2000
