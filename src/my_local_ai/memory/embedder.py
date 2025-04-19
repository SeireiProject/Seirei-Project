# src/my_local_ai/memory/embedder.py
# from sentence_transformers import SentenceTransformer # <-- Move import inside _load_model
import time
import os
import logging # logging をインポート

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

# os.environ['SENTENCE_TRANSFORMERS_HOME'] = './.cache/sentence_transformers/' # 必要なら設定

class Embedder:
    def __init__(self):
        self.model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self.model = None
        logger.info(f"Embedder Initialized (Model: {self.model_name}, Status: Not loaded)")

    def _load_model(self):
        logger.debug(f"Attempting to import SentenceTransformer library...")
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model '{self.model_name}' for the first time...")
            start_time = time.time()
            self.model = SentenceTransformer(self.model_name)
            end_time = time.time()
            logger.info(f"Embedding model loaded successfully in {end_time - start_time:.2f} seconds.")
        except ImportError:
             logger.error("Failed to import SentenceTransformer library! Is it installed? (`pip install sentence-transformers`)")
             self.model = None
        except Exception as e:
            logger.exception(f"Failed to load embedding model '{self.model_name}'") # exc_info=True相当
            self.model = None

    def Embed(self, texts):
        if self.model is None:
            self._load_model()
            if self.model is None:
                logger.error("Cannot embed text, model is not loaded.")
                return [[] for _ in (texts if isinstance(texts, list) else [texts])]

        if isinstance(texts, str):
            texts = [texts]
        if not texts: # 空リストの場合
            return []

        try:
            logger.debug(f"Encoding {len(texts)} text(s)...")
            # 以前 .tolist() を使っていたのでそのままにする
            embeddings = self.model.encode(texts, convert_to_tensor=False).tolist()
            logger.debug(f"Encoding complete.")
            return embeddings
        except Exception as e:
            logger.exception("Error during text embedding") # exc_info=True相当
            return [[] for _ in texts] # エラー時は空リストを返す