# src/my_local_ai/memory/retriever.py
from typing import List, Tuple # 型ヒント用
import logging # logging をインポート

# 関連モジュール (絶対/相対インポート選択)
try:
    from my_local_ai.memory.memory_manager import MemoryManager, MemoryEntry
    from my_local_ai.memory.log_manager import LogManager, LogEntry
    from my_local_ai.memory.embedder import Embedder
except ImportError as e:
    print(f"FATAL Error importing dependencies in Retriever: {e}")
    raise

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, memory_path: str, log_path: str):
        logger.info("Initializing Retriever...")
        # Embedder は内部で1つだけ作成し、各 Manager に渡すのが効率的
        self.Embedder = Embedder()
        logger.info("Initializing MemoryManager...")
        self.MemoryManager = MemoryManager(memory_path, self.Embedder)
        logger.info("Initializing LogManager...")
        self.LogManager = LogManager(log_path, self.Embedder)
        logger.info("Retriever initialized successfully.")

    def RetrieveRelevantInfo(self, query: str, topK_memories=3, topK_logs=5, memory_threshold=0.5, log_threshold=0.5) -> Tuple[List[MemoryEntry], List[LogEntry]]:
        """
        クエリに関連する長期記憶と短期記憶（ログ）を検索して返す。

        Args:
            query (str): ユーザーの入力クエリ。
            topK_memories (int): 取得する長期記憶の最大数。
            topK_logs (int): 取得する短期記憶（ログ）の最大数。
            memory_threshold (float): 長期記憶の類似度閾値。
            log_threshold (float): 短期記憶（ログ）の類似度閾値。

        Returns:
            Tuple[List[MemoryEntry], List[LogEntry]]: 関連する記憶とログのタプル。
        """
        logger.info(f"Retrieving relevant info for query: '{query[:50]}...'")
        try:
            relevant_memories = self.MemoryManager.SearchMemory(
                query, topK=topK_memories, similarity_threshold=memory_threshold
            )
            logger.info(f"Retrieved {len(relevant_memories)} relevant memories.")

            relevant_logs = self.LogManager.SearchRelevantLogs(
                query, topK=topK_logs, similarity_threshold=log_threshold
            )
            logger.info(f"Retrieved {len(relevant_logs)} relevant logs.")

            return relevant_memories, relevant_logs

        except Exception as e:
            logger.exception("Error during information retrieval.")
            return [], [] # エラー時は空リストを返す