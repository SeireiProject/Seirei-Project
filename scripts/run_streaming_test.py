# scripts/run_streaming_test.py
import sys
import os
from pathlib import Path
import traceback
import time
import logging # Import logging

# --- Setup Logging and Paths ---
try:
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    from my_local_ai.utils.logger_config import setup_logging, get_logger
    setup_logging(level=logging.INFO) # Setup logging for this script
    logger = get_logger(__name__) # Get logger for this script
    logger.debug(f"Project root: {project_root}")
except Exception as setup_e:
    print(f"FATAL: Initial setup failed: {setup_e}")
    sys.exit(1)

# --- Core Interface and Utility Imports ---
try:
    logger.debug("Importing StreamingInterface...")
    from my_local_ai.interfaces.streaming import StreamingInterface
    logger.debug("Importing AivisAdapter and speak...")
    from my_local_ai.utils.tts import AivisAdapter, speak
    logger.info("Required modules imported successfully.")
except ImportError as e:
    logger.critical(f"必要なモジュールのインポートに失敗しました: {e}", exc_info=True)
    sys.exit(1)


# --- メイン対話ループ ---
def run_interactive_stream_test():
    logger.info("Initializing Streaming Interface and AivisAdapter...")
    try:
        # TODO: Make model name configurable
        streaming_interface = StreamingInterface(model_name="elyza:jp8b")
        ai_name = streaming_interface.Personality.GetProfile().get("name", "AI")
        # TODO: Make Aivis URL/Speaker ID configurable
        aivis_adapter = AivisAdapter(url="http://127.0.0.1:10101", speaker_id=888753760)
        logger.info(f"{ai_name} is ready. AivisSpeech output enabled.")
        print(f"\n{ai_name} is ready. Type 'exit' to quit.") # User message
    except Exception as e:
        logger.critical("初期化に失敗しました。", exc_info=True)
        return

    print("\n--- Simple Input/Output Loop with AivisSpeech ---") # User message
    print("コメントを入力してください。AIが応答し、AivisSpeechが読み上げます。") # User message

    while True:
        try:
            user_input = input("Comment: ").strip()
            if user_input.lower() == "exit":
                logger.info("User requested exit.")
                break
            if not user_input:
                continue

            logger.info(f"Getting response for input: '{user_input[:50]}...'")
            start_time = time.time()
            ai_response_text = streaming_interface.RespondToComment("ConsoleUser", user_input)
            end_time = time.time()
            logger.info(f"Response generation took {end_time - start_time:.2f} seconds.")

            # Print response to console for user
            print(f"{ai_name}: {ai_response_text}")

            # Speak the response
            speak(aivis_adapter, ai_response_text)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Exiting.")
            break
        except Exception as loop_e:
            logger.exception("メインループで予期せぬエラーが発生しました。")
            time.sleep(1) # Avoid rapid looping on persistent error

    logger.info("Interactive stream test finished.")
    # Consider persisting memory on exit?
    # logger.info("Persisting stream memory before exit...")
    # streaming_interface.PersistStreamMemory()


if __name__ == "__main__":
    run_interactive_stream_test()