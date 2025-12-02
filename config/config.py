# config/config.py

import os
import subprocess

# Docker 容器名
CONTAINER_NAME = "celestia-validator"

# Namespace (29 bytes = 58 hex)
NAMESPACE_ID = "0000004e46545a4f4e45"

# 数据库路径
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nft.db")

# 索引器配置
START_HEIGHT = 1
INDEXER_POLL_INTERVAL = 3

# 获取 Docker 容器内的账户地址
def get_address(key_name: str) -> str:
    try:
        result = subprocess.run(
            f'docker exec {CONTAINER_NAME} celestia-appd keys show {key_name} -a --keyring-backend test',
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except:
        return f"celestia1{key_name}_placeholder"

# 账户地址（启动时动态获取）
VALIDATOR_ADDRESS = get_address('validator')
ALICE_ADDRESS = get_address('alice')
BOB_ADDRESS = get_address('bob')

ISSUER_ADDRESS = ALICE_ADDRESS

# Gas 配置
GAS_LIMIT = 200000
GAS_FEE = 2000