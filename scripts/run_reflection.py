# scripts/run_reflection.py
import os
import sys
from pathlib import Path
import traceback
import logging # Import logging
from dotenv import load_dotenv

# --- Setup Logging First ---
# Need to add src to path BEFORE importing logger_config
try:
    project_root_for_log = Path(__file__).resolve().parent.parent
    src_path_for_log = project_root_for_log / "src"
    sys.path.insert(0, str(src_path_for_log)) # Add src to path
    from my_local_ai.utils.logger_config import setup_logging, get_logger
    setup_logging(level=logging.INFO) # Setup logging for the script
    logger = get_logger(__name__) # Get logger for this script
except Exception as log_setup_e:
    print(f"FATAL: Logging setup failed: {log_setup_e}")
    sys.exit(1)

# --- Path Setup ---
# project_root is already defined for log setup
project_root = project_root_for_log
logger.debug(f"Project root: {project_root}")
# src path already added

# --- Module Import ---
try:
    logger.debug("Attempting to import generate_reflection_from_logs...")
    from my_local_ai.agent.self_awareness import generate_reflection_from_logs
    logger.info("Module 'self_awareness' imported successfully.")
except ModuleNotFoundError as e:
    logger.critical(f"エラー: 'my_local_ai.agent.self_awareness' モジュールが見つかりません。", exc_info=True)
    logger.critical(f"       Project root '{project_root}' が sys.path に正しく追加されているか確認してください。")
    sys.exit(1)
except ImportError as e:
    logger.critical(f"インポートエラー: {e.name}", exc_info=True)
    sys.exit(1)


# --- Environment Variable Loading ---
dotenv_path = project_root / ".env"
if dotenv_path.is_file():
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f".env ファイルを読み込みました: {dotenv_path}")
else:
    logger.warning(f".env ファイルが見つかりません: {dotenv_path}")

# --- API Key Retrieval ---
api_key = os.getenv("GOOGLE_API_KEY")
if api_key is None:
    logger.critical("エラー: 環境変数 'GOOGLE_API_KEY' が未設定です。")
    logger.critical(f"       .env ファイル ({dotenv_path}) を確認するか、環境変数を設定してください。")
    sys.exit(1)
else:
    logger.info("GOOGLE_API_KEY found in environment.")


# --- File Path Definitions ---
log_file_path = project_root / "data" / "stream_logs.json"
identity_file_path = project_root / "config" / "identity.json"


# --- Main Execution Logic ---
if __name__ == "__main__":
    logger.info("内省プロセスを開始します...")
    logger.info(f"  使用するログファイル: {log_file_path}")
    logger.info(f"  使用するアイデンティティファイル: {identity_file_path}")

    if not log_file_path.is_file():
        logger.warning(f"指定されたログファイルが見つかりません: {log_file_path}")
    if not identity_file_path.parent.is_dir():
         logger.critical(f"設定ディレクトリが見つかりません: {identity_file_path.parent}")
         sys.exit(1)

    try:
        generate_reflection_from_logs(
            log_path=log_file_path,
            identity_path=identity_file_path,
            api_key=api_key
        )
        logger.info("内省プロセスが正常に完了しました。")
        # Keep print for user visibility
        print(f"\n結果は {identity_file_path} を確認してください。")

    except Exception as e:
        logger.critical("内省プロセスの実行中に予期せぬエラーが発生しました。", exc_info=True)
        sys.exit(1)