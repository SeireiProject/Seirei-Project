# src/my_local_ai/utils/data_loaders.py
import json
from pathlib import Path
import logging # logging をインポート

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

def load_identity_data(identity_path: Path) -> dict:
    """identity.json ファイルを読み込み、辞書として返す。"""
    identity = {}
    logger.debug(f"Attempting to load identity data from: {identity_path}")
    if identity_path.is_file():
        try:
            with identity_path.open('r', encoding='utf-8') as f:
                identity = json.load(f)
            logger.info(f"アイデンティティデータをロードしました: {identity_path.name}")
        except json.JSONDecodeError:
            logger.warning(f"'{identity_path.name}' のJSON形式が不正か空です。デフォルト値を使用します。")
            identity = {}
        except Exception as e:
            logger.warning(f"'{identity_path.name}' の読み込みに失敗しました: {e}", exc_info=True)
            identity = {}
    else:
         logger.warning(f"アイデンティティファイルが見つかりません: {identity_path}。デフォルト値を使用します。")
         identity = {}

    # 基本構造を保証
    identity.setdefault("Beliefs", [])
    identity.setdefault("Values", [])
    identity.setdefault("Reflections", [])
    logger.debug(f"Loaded identity data structure ensured (Keys: {list(identity.keys())})")
    return identity