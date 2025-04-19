# src/my_local_ai/memory/memory_manager.py
import json
import os
from dataclasses import dataclass, field, asdict # asdict を追加
from typing import List, Optional, Dict # 型ヒント用
from pathlib import Path
import logging # logging をインポート

# 関連モジュール
try:
    # from .embedder import Embedder # 相対インポート
    from my_local_ai.memory.embedder import Embedder # 絶対インポート
    from sentence_transformers import util # 類似度計算用
except ImportError as e:
    print(f"FATAL Error importing dependencies in MemoryManager: {e}")
    raise

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    Id: int
    Content: str
    Embedding: Optional[List[float]] = field(default=None, repr=False) # repr=Falseでログ出力時に省略

    def to_dict(self):
        # asdict を使って dataclass を辞書に変換
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        # 辞書から dataclass インスタンスを作成 (後方互換性や柔軟性のため)
        return cls(
            Id=data.get("Id", -1), # IDがない場合のデフォルト値
            Content=data.get("Content", ""),
            Embedding=data.get("Embedding") # なければ None
        )

class MemoryManager:
    def __init__(self, memory_path: str, embedder: Embedder):
        self.memory_path = Path(memory_path)
        self.Embedder = embedder
        self.Memories: List[MemoryEntry] = []
        self.NextId = 0
        logger.info(f"MemoryManager initialized. Memory file path: {self.memory_path}")
        self.LoadFromFile()

    def LoadFromFile(self):
        logger.info(f"Attempting to load memories from {self.memory_path}...")
        self.Memories = []
        self.NextId = 0
        if not self.memory_path.exists():
            logger.warning(f"Memory file not found at {self.memory_path}. Starting with empty memory.")
            return

        memories_to_embed = [] # Embedding がない記憶のインデックスとテキスト
        try:
            with self.memory_path.open("r", encoding="utf-8") as f:
                try:
                    # ファイル全体が単一のJSONリストであると想定
                    memories_data = json.load(f)
                    if not isinstance(memories_data, list):
                         logger.warning(f"Memory file {self.memory_path} is not a valid JSON list. Starting empty.")
                         return

                    max_id = -1
                    for i, data in enumerate(memories_data):
                        if isinstance(data, dict):
                            # from_dict を使って柔軟に読み込み
                            entry = MemoryEntry.from_dict(data)
                            if entry.Id >= 0: # 有効なIDを持つエントリのみ追加
                                self.Memories.append(entry)
                                max_id = max(max_id, entry.Id)
                                if entry.Embedding is None and entry.Content:
                                     memories_to_embed.append((len(self.Memories) - 1, entry.Content))
                            else:
                                logger.warning(f"Skipping memory entry with invalid or missing Id at index {i}.")
                        else:
                            logger.warning(f"Skipping invalid (non-dict) memory entry at index {i}.")

                    self.NextId = max_id + 1 # 次のIDを設定
                    logger.info(f"Loaded {len(self.Memories)} memories. Next ID set to {self.NextId}.")

                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from {self.memory_path}. Memory might be corrupted.")
                    # Optionally, try to load line by line if it might be JSONL?
                    # For now, treat as corrupted and start empty.
                    self.Memories = []
                    self.NextId = 0

            # Embedding がなかった記憶に Embedding を追加
            if memories_to_embed:
                logger.info(f"Calculating embeddings for {len(memories_to_embed)} memory entries...")
                indices, texts = zip(*memories_to_embed)
                try:
                    new_embeddings = self.Embedder.Embed(list(texts))
                    if len(new_embeddings) == len(indices):
                        for idx, embedding in zip(indices, new_embeddings):
                             if embedding: self.Memories[idx].Embedding = embedding
                        logger.info("Embeddings recalculated for missing entries.")
                        # ここでファイルに保存し直すか検討 (SaveToFile)
                    else:
                         logger.error("Mismatch between number of embeddings and texts.")
                except Exception as e:
                    logger.exception("Error during embedding calculation for memories.")

        except IOError as e:
            logger.error(f"Failed to read memory file {self.memory_path}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during LoadFromFile")


    def SaveToFile(self):
        logger.info(f"Saving {len(self.Memories)} memories to {self.memory_path}...")
        try:
            # dataディレクトリが存在しない場合は作成
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            # 各MemoryEntryを辞書に変換してからリストとして保存
            memory_list = [entry.to_dict() for entry in self.Memories]
            with self.memory_path.open("w", encoding="utf-8") as f:
                json.dump(memory_list, f, ensure_ascii=False, indent=2) # インデント追加
            logger.info("Memories saved successfully.")
        except IOError as e:
            logger.error(f"Failed to write memories to {self.memory_path}: {e}")
        except Exception as e:
            logger.exception("Unexpected error during SaveToFile")

    def SaveMemory(self, Content: str):
        if not Content:
            logger.warning("Attempted to save empty memory content.")
            return

        logger.info(f"Saving new memory: '{Content[:50]}...'")
        embedding = None
        try:
            embedding_list = self.Embedder.Embed(Content)
            if embedding_list: embedding = embedding_list[0]
        except Exception as e:
             logger.exception("Failed to generate embedding for new memory.")
             # Embedding がなくても保存は続行する（Load時に再計算されるため）

        memory_entry = MemoryEntry(
            Id=self.NextId,
            Content=Content,
            Embedding=embedding
        )
        self.Memories.append(memory_entry)
        logger.debug(f"Memory entry created with ID {self.NextId}")
        self.NextId += 1
        # 注意: ここではファイルへの自動保存はしない。SaveToFileを別途呼び出す必要がある。

    def EditMemoryByIndex(self, Index: int, NewContent: str):
        logger.info(f"Attempting to edit memory at index {Index}...")
        if not NewContent:
            logger.warning("Attempted to edit memory with empty content.")
            return # 空の内容での更新は許可しない、または別途処理

        if 0 <= Index < len(self.Memories):
            logger.debug(f"Updating memory ID {self.Memories[Index].Id} content and embedding.")
            self.Memories[Index].Content = NewContent
            new_embedding = None
            try:
                embedding_list = self.Embedder.Embed(NewContent)
                if embedding_list: new_embedding = embedding_list[0]
            except Exception as e:
                 logger.exception(f"Failed to generate embedding for edited memory (Index {Index}).")
                 # Embedding の更新に失敗しても内容は更新する
            self.Memories[Index].Embedding = new_embedding
            logger.info(f"Memory at index {Index} updated successfully.")
            # SaveToFile() をここで呼ぶか検討
        else:
            logger.warning(f"Invalid index ({Index}) for editing memory. Max index is {len(self.Memories) - 1}.")

    def DeleteMemoryByIndex(self, Index: int):
        logger.info(f"Attempting to delete memory at index {Index}...")
        if 0 <= Index < len(self.Memories):
            deleted_memory = self.Memories.pop(Index)
            logger.info(f"Memory ID {deleted_memory.Id} (at index {Index}) deleted successfully.")
            # SaveToFile() をここで呼ぶか検討
        else:
            logger.warning(f"Invalid index ({Index}) for deleting memory. Max index is {len(self.Memories) - 1}.")

    def GetAllMemories(self) -> List[MemoryEntry]:
        logger.debug(f"GetAllMemories called. Returning {len(self.Memories)} entries.")
        return self.Memories

    def SearchMemory(self, query: str, topK=3, similarity_threshold=0.5) -> List[MemoryEntry]:
        logger.info(f"Searching memory for query: '{query[:50]}...', topK={topK}, threshold={similarity_threshold}")
        if not self.Memories:
            logger.warning("SearchMemory called but no memories available.")
            return []

        try:
            query_embedding_list = self.Embedder.Embed(query)
            if not query_embedding_list or not query_embedding_list[0]:
                 logger.error("Failed to generate query embedding. Cannot search memory.")
                 return []
            queryEmbedding = query_embedding_list[0]
        except Exception as e:
            logger.exception("Error generating query embedding for memory search.")
            return []

        scores = []
        valid_memory_count = 0
        for i, mem in enumerate(self.Memories):
            if mem.Embedding: # Embedding が存在する記憶のみを対象
                valid_memory_count += 1
                try:
                    score = util.cos_sim(queryEmbedding, mem.Embedding)[0][0].item()
                    if score >= similarity_threshold:
                        scores.append((mem, score))
                        logger.debug(f"  Memory {i} (ID {mem.Id}) similarity: {score:.4f} (Above threshold)")
                    # else:
                        # logger.debug(f"  Memory {i} (ID {mem.Id}) similarity: {score:.4f} (Below threshold)")
                except Exception as e:
                    logger.warning(f"Could not calculate similarity for memory index {i}: {e}")
            # else:
                # logger.debug(f"  Memory {i} (ID {mem.Id}) skipped (no embedding).")

        if not scores:
            logger.info(f"No memories found above similarity threshold {similarity_threshold}.")
            return []

        scores.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Found {len(scores)} memories above threshold. Returning top {min(topK, len(scores))}.")

        return [mem for mem, score in scores[:topK]]