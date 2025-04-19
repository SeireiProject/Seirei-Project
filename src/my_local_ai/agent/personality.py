# src/my_local_ai/agent/personality.py
import json
from pathlib import Path
import logging # logging をインポート

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

class PersonalityManager:
    def __init__(self, configPath: str): # パスは文字列で受け取る
        self.configPath = Path(configPath)
        self.personality = {} # 初期化
        logger.info(f"PersonalityManager initialized. Config path: {self.configPath}")
        self.LoadPersonality() # __init__でロードを実行

    def LoadPersonality(self):
        logger.info(f"Attempting to load personality from {self.configPath}...")
        if not self.configPath.is_file():
            logger.error(f"Personality config file not found at: {self.configPath}")
            # Provide default empty structure? Or raise error?
            self.personality = {} # Return empty if file not found
            return # Or raise FileNotFoundError?

        try:
            with self.configPath.open("r", encoding="utf-8") as file:
                self.personality = json.load(file)
            logger.info(f"Personality loaded successfully from {self.configPath.name}.")
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON from personality file {self.configPath}: {e}")
             self.personality = {} # Use empty on error
        except IOError as e:
             logger.error(f"Failed to read personality file {self.configPath}: {e}")
             self.personality = {} # Use empty on error
        except Exception as e:
             logger.exception(f"Unexpected error loading personality")
             self.personality = {} # Use empty on error


    def GetProfile(self) -> dict:
        # .get() を使ってキーが存在しない場合も安全にデフォルト値を返す
        profile_data = self.personality.get("profile", {})
        logger.debug(f"GetProfile called. Returning: {profile_data}")
        return profile_data

    def GetSpeechExamples(self) -> list:
        examples = self.personality.get("speechExamples", [])
        logger.debug(f"GetSpeechExamples called. Returning {len(examples)} examples.")
        return examples

    def GetAll(self) -> dict:
        logger.debug("GetAll called.")
        return self.personality