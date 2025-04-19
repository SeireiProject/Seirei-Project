# src/my_local_ai/memory/log_manager.py
import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict # asdict を追加
from typing import List, Optional, Dict # 型ヒント用
from pathlib import Path
import logging # logging をインポート

# 関連モジュールをインポート
try:
    # from .embedder import Embedder # 相対インポートを使う場合
    from my_local_ai.memory.embedder import Embedder # または絶対インポート
    from sentence_transformers import util # 類似度計算用
except ImportError as e:
    print(f"FATAL Error importing dependencies in LogManager: {e}")
    raise

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    Timestamp: str
    UserInput: str
    AssistantResponse: str
    Username: str = "Unknown"
    Embedding: Optional[List[float]] = field(default=None, repr=False) # repr=Falseでログ出力時に省略

    def to_dict(self):
        # asdict を使って dataclass を辞書に変換 (Embedding も含む)
        return asdict(self)

class LogManager:
    def __init__(self, log_path: str, embedder: Embedder):
        self.log_path = Path(log_path)
        self.Embedder = embedder
        self.Logs: List[LogEntry] = []
        logger.info(f"LogManager initialized. Log file path: {self.log_path}")
        self.LoadLogs()

    def LoadLogs(self):
        logger.info(f"Attempting to load logs from {self.log_path}...")
        self.Logs = []
        if not self.log_path.exists():
            logger.warning(f"Log file not found at {self.log_path}. Starting with empty logs.")
            return

        logs_to_embed = [] # Embedding がないログのインデックスとテキストを保持
        try:
            with self.log_path.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line: continue
                    try:
                        log_data = json.loads(line)
                        # キーの存在確認とデフォルト値
                        timestamp = log_data.get("Timestamp", datetime.now().isoformat())
                        user_input = log_data.get("UserInput", "")
                        assistant_response = log_data.get("AssistantResponse", "")
                        username = log_data.get("Username", "Unknown")
                        embedding = log_data.get("Embedding") # なければ None

                        entry = LogEntry(
                            Timestamp=timestamp,
                            UserInput=user_input,
                            AssistantResponse=assistant_response,
                            Username=username,
                            Embedding=embedding
                        )
                        self.Logs.append(entry)

                        # Embedding がない場合は後で計算するために記録
                        if embedding is None and user_input: # ユーザー入力がないログはEmbedしない
                            logs_to_embed.append((len(self.Logs) - 1, user_input)) # インデックスとテキスト

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from line {i+1} in {self.log_path}. Skipping line.")
                    except Exception as e:
                         logger.warning(f"Error processing line {i+1} in {self.log_path}: {e}. Skipping line.")

            logger.info(f"Loaded {len(self.Logs)} log entries.")

            # Embedding がなかったログに Embedding を追加
            if logs_to_embed:
                logger.info(f"Calculating embeddings for {len(logs_to_embed)} log entries without embeddings...")
                indices, texts = zip(*logs_to_embed)
                try:
                    new_embeddings = self.Embedder.Embed(list(texts))
                    if len(new_embeddings) == len(indices):
                        for idx, embedding in zip(indices, new_embeddings):
                            if embedding: # Embedderが空リストを返さないか確認
                                self.Logs[idx].Embedding = embedding
                        logger.info("Embeddings calculated and added for missing entries.")
                        # Optional: ここでログファイルを上書き保存する (欠損を埋めた状態で)
                        # self.SaveAllLogsToFile() # 新しいメソッドが必要
                    else:
                         logger.error("Number of generated embeddings does not match number of texts.")
                except Exception as e:
                    logger.exception("Error during embedding calculation for logs.")

        except IOError as e:
            logger.error(f"Failed to read log file {self.log_path}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during LoadLogs")

    def SaveLog(self, UserInput: str, AssistantResponse: str, Username: str = "User"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 以前のフォーマットに合わせる場合
        # timestamp = datetime.now().isoformat() # ISO形式の場合
        logger.debug(f"Saving log: User='{Username}', Input='{UserInput[:50]}...'")
        embedding = None
        if UserInput: # ユーザー入力があればEmbeddingを計算
            try:
                embedding_list = self.Embedder.Embed(UserInput)
                if embedding_list:
                    embedding = embedding_list[0] # 最初の要素を取得
            except Exception as e:
                logger.exception("Failed to generate embedding for log entry.")

        log_entry = LogEntry(
            Timestamp=timestamp,
            UserInput=UserInput,
            AssistantResponse=AssistantResponse,
            Username=Username,
            Embedding=embedding
        )
        self.Logs.append(log_entry)

        # ファイルに追記 (JSON Lines形式)
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                # LogEntry を辞書に変換してから JSON 文字列に
                f.write(json.dumps(log_entry.to_dict(), ensure_ascii=False) + "\n")
            logger.info(f"Log entry saved to {self.log_path}.")
        except IOError as e:
            logger.error(f"Failed to append log to {self.log_path}: {e}")
        except Exception as e:
             logger.exception("Unexpected error during SaveLog file operation.")

    def GetAllLogs(self) -> List[LogEntry]:
        logger.debug(f"GetAllLogs called. Returning {len(self.Logs)} entries.")
        return self.Logs

    def SearchRelevantLogs(self, query: str, topK=5, similarity_threshold=0.5) -> List[LogEntry]:
        logger.info(f"Searching relevant logs for query: '{query[:50]}...', topK={topK}, threshold={similarity_threshold}")
        if not self.Logs:
            logger.warning("SearchRelevantLogs called but no logs available.")
            return []

        try:
            query_embedding_list = self.Embedder.Embed(query)
            if not query_embedding_list or not query_embedding_list[0]:
                 logger.error("Failed to generate query embedding. Cannot search logs.")
                 return []
            queryEmbedding = query_embedding_list[0]
        except Exception as e:
            logger.exception("Error generating query embedding for log search.")
            return []

        scores = []
        valid_log_count = 0
        for i, log in enumerate(self.Logs):
            if log.Embedding: # Embedding が存在するログのみを対象
                valid_log_count += 1
                try:
                    score = util.cos_sim(queryEmbedding, log.Embedding)[0][0].item()
                    if score >= similarity_threshold:
                        scores.append((log, score))
                        logger.debug(f"  Log {i} similarity: {score:.4f} (Above threshold)")
                    # else:
                        # logger.debug(f"  Log {i} similarity: {score:.4f} (Below threshold)")
                except Exception as e:
                    logger.warning(f"Could not calculate similarity for log index {i}: {e}")
            # else:
                # logger.debug(f"  Log {i} skipped (no embedding).")


        if not scores:
            logger.info(f"No logs found above similarity threshold {similarity_threshold}.")
            return []

        # スコアでソート
        scores.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Found {len(scores)} logs above threshold. Returning top {min(topK, len(scores))}.")

        # 上位K件を返す
        return [log for log, score in scores[:topK]]