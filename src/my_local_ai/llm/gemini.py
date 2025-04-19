# src/my_local_ai/llm/gemini.py
import logging # logging をインポート
import traceback

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    # Configure safety settings (optional, example to block harmful content)
    # safety_settings = [
    #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    # ]
except ImportError:
    logger.error("google-generativeai library not found. Install with `pip install google-generativeai`")
    genai = None
    # safety_settings = None


class GeminiClient:
    """Google Gemini APIと通信するためのクライアントクラス。"""
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"): # default model
        logger.info(f"Initializing GeminiClient with model: {model_name}")
        if genai is None:
            raise ImportError("google-generativeai library is not available.")

        try:
            # APIキーの設定
            genai.configure(api_key=api_key)
            # モデルの準備 (世代設定や安全設定もここで指定可能)
            # generation_config = genai.types.GenerationConfig(...)
            self.model = genai.GenerativeModel(
                model_name,
                # safety_settings=safety_settings, # Apply safety settings if defined
                # generation_config=generation_config
            )
            logger.info("Gemini model initialized successfully.")
        except Exception as e:
            logger.exception(f"Failed to configure Gemini or initialize model '{model_name}'")
            # Raise a more specific error? Or handle downstream?
            raise # Re-raise the exception to signal init failure

    def generate(self, prompt: str) -> str:
        """
        指定されたプロンプトを使用してGemini APIから応答を生成する。

        Args:
            prompt (str): LLMに渡すプロンプト文字列。

        Returns:
            str: 生成された応答テキスト。エラー時は特定の文字列を返す。
        """
        logger.info(f"Generating response from Gemini for prompt (length {len(prompt)})...")
        logger.debug(f"Prompt snippet: {prompt[:100]}...")
        try:
            # ストリーミングではなく、単純な応答生成
            response = self.model.generate_content(prompt)
            # エラーやブロックがないか確認 (より詳細なハンドリングが可能)
            if not response.candidates:
                 logger.warning("Gemini response has no candidates.")
                 # Try accessing prompt_feedback for block reason
                 try:
                      feedback = response.prompt_feedback
                      logger.warning(f"Prompt Feedback: {feedback}")
                      block_reason = feedback.block_reason_message if feedback else "Unknown reason"
                      return f"（応答がブロックされました：{block_reason}）"
                 except Exception:
                      return "（応答候補がありませんでした）"

            # 最初の候補のテキストを取得 (通常はこれでOK)
            # response.text は内部でパートを結合してくれるヘルパープロパティ
            generated_text = response.text.strip()
            logger.info(f"Gemini response received (length {len(generated_text)}).")
            logger.debug(f"Response snippet: {generated_text[:100]}...")
            return generated_text

        except Exception as e:
            # google.generativeai.types.generation_types.BlockedPromptException などを捕捉しても良い
            logger.exception("[GeminiClient Error] Failed to generate content")
            return "（内省の生成に失敗しました）" # 以前のエラーメッセージを踏襲