# src/my_local_ai/interfaces/streaming.py
import time
from pathlib import Path
import json
import traceback
import logging # logging をインポート

# --- このモジュール用のロガー ---
logger = logging.getLogger(__name__)

# --- コアコンポーネントのインポート ---
try:
    from my_local_ai.memory import Retriever
    from my_local_ai.agent.prompts import BuildPrompt
    from my_local_ai.llm.ollama import OllamaClient # ストリーミングもOllamaと仮定
    from my_local_ai.agent.personality import PersonalityManager
    # identity ローダー (utilsからインポート)
    from my_local_ai.utils.data_loaders import load_identity_data
except ImportError as e:
    logger.critical(f"Error importing core components in streaming.py: {e}", exc_info=True)
    raise # 起動時に必須モジュールがない場合は停止させる

# --- StreamingInterface クラス ---
class StreamingInterface:
    """
    ストリーミング配信向けの対話インターフェース。
    配信用に分離されたログと記憶を使用し、AIのアイデンティティも考慮する。
    """
    def __init__(self, model_name="elyza:jp8b"):
        logger.info("Initializing StreamingInterface...")
        self.model_name = model_name

        # --- Path Definitions ---
        try:
            self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        except NameError:
            self.project_root = Path.cwd().parent
            logger.warning(f"__file__ not defined, guessed project root: {self.project_root}")

        self.stream_memory_path = self.project_root / "data" / "stream_memories.json"
        self.stream_log_path = self.project_root / "data" / "stream_logs.json"
        self.config_path = self.project_root / "config" / "personality.json"
        self.identity_path = self.project_root / "config" / "identity.json"

        # Ensure data directory exists
        data_dir = self.project_root / "data"
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create data directory {data_dir}: {e}")
            # Handle appropriately, maybe raise error

        logger.info(f"  Stream Memory Path: {self.stream_memory_path}")
        logger.info(f"  Stream Log Path:    {self.stream_log_path}")
        logger.info(f"  Config Path:      {self.config_path}")
        logger.info(f"  Identity Path:    {self.identity_path}")

        # --- Initialize Components ---
        try:
            logger.info("  Initializing Retriever for streaming...")
            self.RetrieverInstance = Retriever(
                memory_path=str(self.stream_memory_path),
                log_path=str(self.stream_log_path)
            )

            logger.info(f"  Initializing Executor ({self.model_name})...")
            self.Executor = OllamaClient(model=self.model_name) # Use Ollama for streaming response

            logger.info("  Initializing PersonalityManager...")
            self.Personality = PersonalityManager(configPath=str(self.config_path))

            logger.info("  Loading Identity Data...")
            self.IdentityData = load_identity_data(self.identity_path) # Use loader from utils

            logger.info("StreamingInterface initialization complete.")

        except Exception as e:
            logger.critical("FATAL: Error during StreamingInterface initialization", exc_info=True)
            raise

    def RespondToComment(self, Username: str, comment: str) -> str:
        """Processes a single comment/message and returns the AI's response."""
        logger.info(f"Processing comment from '{Username}': '{comment[:50]}...'")
        if not comment:
             logger.warning("Received empty comment.")
             return "(コメントが空です)"

        try:
            start_time = time.time()
            # 1. Retrieve relevant info
            memories, logs = self.RetrieverInstance.RetrieveRelevantInfo(comment)
            retrieve_time = time.time() - start_time
            logger.info(f"Retrieved info in {retrieve_time:.2f}s (Memories: {len(memories)}, Logs: {len(logs)})")

            # 2. Build prompt
            personality_data = self.Personality.GetAll()
            prompt = BuildPrompt(
                UserInput=comment, Memories=memories, Logs=logs,
                Personality=personality_data, IdentityData=self.IdentityData
            )
            logger.debug(f"Prompt built (length: {len(prompt)}).")

            # 3. Generate response
            logger.info("Executing LLM prompt...")
            start_llm_time = time.time()
            response = self.Executor.ExecutePrompt(prompt)
            llm_time = time.time() - start_llm_time
            logger.info(f"LLM execution time: {llm_time:.2f}s.")

            # 4. Save log
            start_log_time = time.time()
            self.RetrieverInstance.LogManager.SaveLog(comment, response, Username=Username)
            log_time = time.time() - start_log_time
            logger.info(f"Log saved in {log_time:.2f}s.")

            logger.info(f"Generated response: '{response[:50]}...'")
            return response

        except Exception as e:
            logger.exception("Error during RespondToComment")
            return "(エラーが発生したため応答できません)"

    # --- Memory Management Methods ---
    def SaveStreamMemory(self, content: str):
        if not content: logger.warning("Attempted to save empty stream memory."); return
        logger.info(f"Saving stream memory: '{content[:50]}...'")
        try:
            self.RetrieverInstance.MemoryManager.SaveMemory(content)
            # Consider adding self.PersistStreamMemory() here if needed
        except Exception as e: logger.exception("Error saving stream memory")

    def EditStreamMemory(self, index: int, new_content: str):
        if not new_content: logger.warning("Attempted to edit stream memory with empty content."); return
        logger.info(f"Editing stream memory index {index}")
        try:
            self.RetrieverInstance.MemoryManager.EditMemoryByIndex(index, new_content)
        except IndexError: logger.warning(f"Invalid index {index} for editing stream memory.")
        except Exception as e: logger.exception("Error editing stream memory")

    def DeleteStreamMemory(self, index: int):
        logger.info(f"Deleting stream memory index {index}")
        try:
            self.RetrieverInstance.MemoryManager.DeleteMemoryByIndex(index)
        except IndexError: logger.warning(f"Invalid index {index} for deleting stream memory.")
        except Exception as e: logger.exception("Error deleting stream memory")

    def ShowStreamMemories(self):
        logger.info("Getting all stream memories")
        try:
            return self.RetrieverInstance.MemoryManager.GetAllMemories()
        except Exception as e:
            logger.exception("Error getting stream memories")
            return []

    def PersistStreamMemory(self):
         logger.info(f"Persisting stream memory to {self.stream_memory_path}...")
         try:
            self.RetrieverInstance.MemoryManager.SaveToFile()
            logger.info("Stream memory saved successfully.")
         except Exception as e:
            logger.exception("Error saving stream memory file")


# --- Example Usage (if run directly) ---
if __name__ == '__main__':
    # Setup logging for standalone execution
    from my_local_ai.utils.logger_config import setup_logging
    setup_logging(level=logging.DEBUG) # Use DEBUG level for testing this module

    logger_main = logging.getLogger(__name__) # Get logger for this block
    logger_main.info("--- Testing StreamingInterface Basic Initialization & Response ---")

    try:
        streaming_interface = StreamingInterface()
        logger_main.info("\n--- Simulating Interaction ---")
        user = "TestViewer"
        comment = "テストコメントです"
        response = streaming_interface.RespondToComment(user, comment)

        logger_main.info("\n--- Simulating Memory Operation ---")
        streaming_interface.SaveStreamMemory("テスト記憶")
        memories = streaming_interface.ShowStreamMemories()
        logger_main.info("Current Stream Memories:")
        if memories: [logger_main.info(f"  {i}: {mem.Content}") for i, mem in enumerate(memories)]
        else: logger_main.info("  (No memories)")

        streaming_interface.PersistStreamMemory()

    except Exception as main_e:
        logger_main.critical("\n--- Test Execution Failed ---", exc_info=True)

    logger_main.info("\n--- Test Finished ---")