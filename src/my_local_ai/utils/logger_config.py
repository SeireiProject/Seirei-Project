import logging
import sys

# 一度だけ設定するためのフラグ
_logging_configured = False

def setup_logging(level=logging.INFO):
    """基本的なストリームロギングを設定する。"""
    global _logging_configured
    if _logging_configured:
        return # 既に設定済みなら何もしない

    # ルートロガーを取得し、基本的な設定を行う
    logger = logging.getLogger() # ルートロガー
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # 標準出力へのハンドラ
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    # ハンドラが既に追加されていないか確認してから追加
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
         logger.addHandler(handler)

    logger.setLevel(level)

    # 特定のライブラリのログレベルを調整（任意）
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _logging_configured = True
    print(f"Logging setup complete. Level: {logging.getLevelName(logger.getEffectiveLevel())}") # 設定完了を通知

def get_logger(name: str):
    """指定された名前でロガーインスタンスを取得する。"""
    return logging.getLogger(name)