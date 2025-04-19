# src/my_local_ai/llm/ollama.py
import requests
import json
import logging # logging をインポート

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

class OllamaClient:
    """Ollama APIと通信するためのクライアントクラス。"""
    def __init__(self, host: str = "http://localhost:11434", model: str = "elyza:jp8b"):
        # デフォルトのエンドポイントURLとモデル名
        self.endpoint = f"{host}/api/generate"
        self.model = model
        logger.info(f"OllamaClient initialized. Endpoint: {self.endpoint}, Model: {self.model}")
        # TODO: Consider adding a check here to see if Ollama server is reachable

    def ExecutePrompt(self, prompt: str) -> str:
        """
        Ollama APIにプロンプトを送信し、生成された応答を返す。

        Args:
            prompt (str): Ollamaモデルに渡すプロンプト文字列。

        Returns:
            str: 生成された応答テキスト。エラー時は特定の文字列を返す。
        """
        logger.info(f"Executing prompt with Ollama model '{self.model}' (prompt length {len(prompt)})...")
        logger.debug(f"Prompt snippet: {prompt[:100]}...")
        try:
            # Ollama APIへのリクエストデータ
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False, # ストリーミングは無効にする
                # "options": { # 必要ならオプション追加
                #     "temperature": 0.7,
                #     "num_predict": 512
                # }
            }
            # ヘッダー指定
            headers = {'Content-Type': 'application/json'}

            # POSTリクエストを送信 (タイムアウトを設定)
            response = requests.post(self.endpoint, headers=headers, data=json.dumps(data), timeout=120) # 長めのタイムアウト
            response.raise_for_status() # HTTPエラーチェック

            # レスポンスをJSONとしてパース
            response_data = response.json()

            # 応答テキストを取得
            generated_text = response_data.get('response', '').strip()
            logger.info(f"Ollama response received (length {len(generated_text)}).")
            logger.debug(f"Response snippet: {generated_text[:100]}...")

            # TODO: Add more context from response_data if needed (e.g., context array for follow-up)
            # self.last_context = response_data.get('context')

            return generated_text

        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to connect to Ollama endpoint: {self.endpoint}. Is Ollama running?")
            return "（Ollamaサーバーへの接続に失敗しました）"
        except requests.exceptions.Timeout:
            logger.error(f"Request to Ollama endpoint timed out.")
            return "（Ollamaサーバーからの応答がタイムアウトしました）"
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during request to Ollama endpoint: {e}")
            if e.response is not None:
                 logger.error(f"  Status: {e.response.status_code}, Body: {e.response.text[:200]}...")
            return "（Ollamaサーバーとの通信中にエラーが発生しました）"
        except json.JSONDecodeError:
             logger.error(f"Failed to decode JSON response from Ollama. Response: {response.text[:200]}...")
             return "（Ollamaサーバーからの応答形式が不正です）"
        except Exception as e:
            logger.exception("Unexpected error executing Ollama prompt")
            return "（応答の生成中に予期せぬエラーが発生しました）"