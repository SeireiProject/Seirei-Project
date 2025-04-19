# scripts/run_youtube_live.py

# --- Standard Library Imports ---
import sys
import os
import time
import logging
from pathlib import Path
import json

# --- Third-party Library Imports ---
try:
    import pytchat
except ImportError:
    print("エラー: 'pytchat' ライブラリが見つかりません。")
    print("次のコマンドでインストールしてください: pip install pytchat")
    sys.exit(1)
from dotenv import load_dotenv # ★★★ dotenv をインポート ★★★


# --- Project Setup: Path Configuration ---
# このスクリプトが 'scripts' ディレクトリにあると仮定
try:
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / "src"
    if src_path.is_dir():
        sys.path.insert(0, str(src_path))
        print(f"プロジェクトの src ディレクトリをシステムパスに追加しました: {src_path}")
    else:
        # もし 'scripts' の一つ上が 'src' だった場合 (プロジェクト構造による)
        src_path_alt = Path(__file__).resolve().parent
        if (src_path_alt / 'my_local_ai').is_dir():
            sys.path.insert(0, str(src_path_alt))
            print(f"プロジェクトの src ディレクトリ (代替) をシステムパスに追加しました: {src_path_alt}")
        else:
            raise FileNotFoundError(f"'src' ディレクトリが見つかりません。パスを確認してください。 Project Root: {project_root}")

except Exception as path_e:
    print(f"致命的エラー: プロジェクトパスの設定中にエラーが発生しました: {path_e}")
    sys.exit(1)

# --- Project Setup: Logging ---
try:
    from my_local_ai.utils.logger_config import setup_logging, get_logger
    # ログレベルを設定 (INFO または DEBUG)
    setup_logging(level=logging.INFO)
    logger = get_logger(__name__) # このスクリプト用のロガーを取得
except ImportError as log_e:
    print(f"致命的エラー: ロガー設定のインポートに失敗しました: {log_e}")
    sys.exit(1)
except Exception as setup_e:
    print(f"致命的エラー: ロギング設定中にエラーが発生しました: {setup_e}")
    sys.exit(1)
# --- Project Setup: Path Configuration ---
try:
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / "src"
    if src_path.is_dir():
        sys.path.insert(0, str(src_path))
        print(f"プロジェクトの src ディレクトリをシステムパスに追加しました: {src_path}")
    # ... (代替パスの処理もそのまま) ...
    else:
        raise FileNotFoundError(f"'src' ディレクトリが見つかりません。パスを確認してください。 Project Root: {project_root}")

    # ★★★ identity.json へのパスを追加 ★★★
    identity_file_path = project_root / "config" / "identity.json"
    logger.info(f"Identity file path set to: {identity_file_path}")

    # ★★★ .env ファイルの読み込み処理を追加 ★★★
    dotenv_path = project_root / ".env"
    if dotenv_path.is_file():
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f".env ファイルを読み込みました: {dotenv_path}")
    else:
        logger.warning(f".env ファイルが見つかりません: {dotenv_path}。内省機能はAPIキーがないと動作しません。")

except Exception as path_e:
    print(f"致命的エラー: プロジェクトパスの設定中にエラーが発生しました: {path_e}")
    sys.exit(1)

# --- Project Setup: Core Component Imports ---
try:
    logger.debug("StreamingInterfaceをインポート中...")
    from my_local_ai.interfaces.streaming import StreamingInterface
    logger.debug("AivisAdapterとspeakをインポート中...")
    from my_local_ai.utils.tts import AivisAdapter, speak
        # ★★★ 内省生成関数をインポート ★★★
    from my_local_ai.agent.self_awareness import generate_reflection_from_logs
    logger.info("コアAIモジュールのインポートに成功しました。")
except ImportError as e:
    logger.critical(f"必要なAIモジュールのインポートに失敗しました: {e}", exc_info=True)
    sys.exit(1)
except Exception as e:
     logger.critical(f"コアモジュールのインポート中に予期せぬエラーが発生しました: {e}", exc_info=True)
     sys.exit(1)


# --- Configuration ---
# TODO: これらの設定を外部ファイル（例: config.yamlや.env）に移動する
# --- ここに取得したいYouTube LiveのビデオIDを入れてください ---
# 例: YouTubeのサンプルライブ "jfKfPfyJRdk" など
DEFAULT_YOUTUBE_VIDEO_ID = "YOUR_YOUTUBE_LIVE_VIDEO_ID"
# ★★★ Google APIキーを環境変数から取得 ★★★
GOOGLE_API_KEY_FOR_REFLECTION = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY_FOR_REFLECTION:
     logger.warning("環境変数 'GOOGLE_API_KEY' が未設定です。内省機能は実行されません。")

# --- AI Configuration ---
# TODO: これらも設定ファイルに移動する
OLLAMA_MODEL_NAME = "elyza:jp8b" # StreamingInterfaceが使用するモデル
AIVIS_URL = "http://127.0.0.1:10101" # Aivis TTSのURL
AIVIS_SPEAKER_ID = 888753760 # Aivis TTSのSpeaker ID

def speak_todays_reflection(identity_path: Path, adapter: AivisAdapter, ai_name: str):
    """
    identity.jsonを読み込み、最新の内省(Insight)をTTSで読み上げる。
    """
    logger.info(f"今日の学びの読み上げを開始します... Identityファイル: {identity_path}")
    print("\n--- 今日の星澪メモ ---") # コンソールにも区切りを表示

    if not identity_path.is_file():
        logger.warning(f"Identityファイルが見つかりません: {identity_path}。読み上げをスキップします。")
        print("（内省データファイルが見つかりませんでした）")
        return

    try:
        with identity_path.open('r', encoding='utf-8') as f:
            identity_data = json.load(f)

        reflections = identity_data.get("Reflections", [])
        if not reflections:
            logger.info("Identityファイルに内省データ(Reflections)がありません。")
            print("（まだ今日の学びはありません）")
            return

        # 最新の内省を取得 (リストの最後の要素)
        latest_reflection = reflections[-1]
        insight_text = latest_reflection.get("Insight")

        if not insight_text:
            logger.warning("最新の内省データにInsightテキストがありません。")
            print("（今日の学びのテキストが見つかりませんでした）")
            return

        # 読み上げ用の前置きを追加 (任意)
        speak_text = f"今日の配信を通じて、私が考えたこと、気づいたことをお話しします。\n\n{insight_text}"

        logger.info("最新のInsightを取得し、読み上げます...")
        # speak関数を使って読み上げる
        if adapter and speak:
            speak(adapter, speak_text)
        else:
            logger.error("TTSアダプターまたはspeak関数が利用できません。読み上げ不可。")
            print("（音声読み上げ機能が利用できません）")

        print("---------------------\n")

    except json.JSONDecodeError:
        logger.error(f"IdentityファイルのJSON形式が不正です: {identity_path}")
        print("（内省データファイルの形式が正しくありません）")
    except Exception as e:
        logger.exception(f"今日の学びの読み上げ中に予期せぬエラーが発生しました。")
        print("（今日の学びの読み上げ中にエラーが発生しました）")

# --- Main Execution Function ---
def run_live(video_id: str):
    """
    YouTube Liveチャットに接続し、コメントをAIで処理し、
    応答を出力（コンソール＋TTS）します。
    """
    logger.info(f"YouTube Live連携を開始します。ビデオID: {video_id}")
    print("-" * 30)
    print(f"星澪 - YouTube Live Integration")
    print(f"ビデオID: {video_id}")
    print("-" * 30)

    streaming_interface = None
    aivis_adapter = None
    chat = None
    ai_name = "AI" # デフォルト名

    try:
        # --- AIコンポーネントの初期化 ---
        logger.info("StreamingInterfaceを初期化中...")
        # 設定したモデル名を渡す
        streaming_interface = StreamingInterface(model_name=OLLAMA_MODEL_NAME)
        ai_name = streaming_interface.Personality.GetProfile().get("name", "星澪") # personality.jsonから名前取得
        logger.info(f"AI名: {ai_name}")

        logger.info("TTS用のAivisAdapterを初期化中...")
        aivis_adapter = AivisAdapter(url=AIVIS_URL, speaker_id=AIVIS_SPEAKER_ID)
        logger.info(f"{ai_name} と TTSシステムの初期化が完了しました。")

        # --- YouTubeチャットへの接続 ---
        logger.info(f"YouTubeチャットに接続中... ビデオID: {video_id}")
        chat = pytchat.create(video_id=video_id)
        if not chat.is_alive():
            logger.error(f"接続失敗、またはライブストリームがアクティブではありません。ビデオID: {video_id}")
            print(f"エラー: YouTube Liveが見つからないか、アクティブではありません (Video ID: {video_id})")
            return # 接続失敗時は終了

        logger.info("YouTubeチャットへの接続に成功しました。")
        print(f"\n{ai_name} が YouTube Live のコメントを待機しています...")
        print("スクリプトを停止するには Ctrl+C を押してください。")

        # --- メインのコメント処理ループ ---
        while chat.is_alive():
            # 新しいコメントを同期的に取得
            for item in chat.get().sync_items():
                timestamp = item.datetime
                username = item.author.name
                comment_text = item.message

                logger.info(f"チャット受信: {timestamp} [{username}] {comment_text}")

                # --- コメントのフィルタリングや前処理 (任意) ---
                if not comment_text: # 空のコメントは無視
                    logger.debug(f"空のコメントのため無視: {username}")
                    continue
                # 例: 特定のユーザーを無視
                # if username == "Nightbot":
                #     continue
                # 例: コマンドを無視
                # if comment_text.startswith("!"):
                #     continue

                # --- AIによるコメント処理 ---
                try:
                    logger.info(f"{username} からのコメントを処理中...")
                    start_time = time.time()

                    # StreamingInterfaceを使ってAIの応答を生成
                    ai_response = streaming_interface.RespondToComment(
                        Username=username,
                        comment=comment_text
                    )

                    end_time = time.time()
                    processing_time = end_time - start_time
                    logger.info(f"応答生成完了 ({processing_time:.2f}秒): '{ai_response[:50]}...'")

                    # --- AI応答の出力 ---
                    # 1. コンソールへの表示
                    print(f"\n[{timestamp}] {username}: {comment_text}")
                    print(f"-> {ai_name}: {ai_response}")

                    # 2. TTSによる音声合成
                    if aivis_adapter and speak:
                        logger.info("応答を音声化中...")
                        # speak関数にアダプターとテキストを渡す
                        speak(aivis_adapter, ai_response)
                        logger.info("TTS再生完了（または非同期開始）。")
                    else:
                         logger.warning("TTSアダプターまたはspeak関数が見つからないため、音声出力をスキップします。")

                    # TODO: ここにアバター制御（リップシンク、表情など）の連携コードを追加

                except Exception as ai_processing_error:
                    logger.exception(f"{username}からのコメント処理中、またはAI応答の生成・出力中にエラーが発生しました。")
                    # 必要に応じてコンソールにもエラー表示
                    # print(f"エラー: {username}のコメント処理中に問題が発生しました。")

            # --- CPU負荷軽減のための短い待機 (通常 sync_items() では不要な場合が多い) ---
            # time.sleep(0.1) # 必要に応じて調整

    # --- 特定の例外処理 ---
    except pytchat.exceptions.InvalidVideoIdException:
        logger.error(f"無効なYouTubeビデオIDが指定されました: {video_id}")
        print(f"エラー: 無効なYouTubeビデオIDです: {video_id}")
    except pytchat.exceptions.NoContents as nc_e:
         logger.warning(f"チャット接続が終了したか、コンテンツが見つかりません。ビデオID: {video_id}。配信が終了した可能性があります。 詳細: {nc_e}")
         print(f"情報: ライブストリームが終了したか、チャットが見つかりません (Video ID: {video_id})")
    except KeyboardInterrupt:
        logger.info("キーボード割り込みを受け付けました。シャットダウンします...")
        print("\nシャットダウンしています...")
    except Exception as general_error:
        # その他の予期せぬエラーをログに記録
        logger.exception("メインのLiveループで予期せぬエラーが発生しました。")
        print(f"予期せぬエラーが発生しました: {general_error}")

    # --- クリーンアップ処理 ---
    finally:
        logger.info("リソースをクリーンアップ中...")
        if chat and chat.is_alive():
            logger.debug("pytchat接続を終了中...")
            try:
                chat.terminate()
                logger.info("Pytchat接続を終了しました。")
            except Exception as term_e:
                 logger.error(f"pytchat終了中にエラー: {term_e}")

        # ★★★ 終了前に内省プロセスを実行 ★★★
        # APIキーがあり、StreamingInterfaceが初期化されている場合のみ実行
        if GOOGLE_API_KEY_FOR_REFLECTION and streaming_interface:
             logger.info("終了前に内省プロセスを実行します...")
             print("\n--- 内省中 (完了まで少しお待ちください) ---")
             try:
                 # 内省に使うログファイルとidentityファイルのパスを取得
                 # StreamingInterfaceが持つパス情報を利用するのが確実
                 reflection_log_path = streaming_interface.stream_log_path
                 reflection_identity_path = identity_file_path # スクリプト上部で定義済み

                 if reflection_log_path.is_file():
                     # generate_reflection_from_logs を呼び出して内省を実行
                     generate_reflection_from_logs(
                         log_path=reflection_log_path,
                         identity_path=reflection_identity_path,
                         api_key=GOOGLE_API_KEY_FOR_REFLECTION
                     )
                     logger.info("内省プロセスが完了し、identity.json が更新されました。")
                     print("--- 内省完了 ---")
                 else:
                     logger.warning(f"内省用のログファイルが見つかりません: {reflection_log_path}。内省をスキップします。")
                     print("（内省用のログファイルが見つかりませんでした）")

             except Exception as reflection_e:
                 logger.exception("内省プロセスの実行中にエラーが発生しました。")
                 print("（内省中にエラーが発生しました）")
        else:
             logger.warning("Google APIキーが未設定か、StreamingInterfaceが初期化されていないため、自動内省をスキップします。")
        # ★★★ 内省処理ここまで ★★★

        # ★★★ 「今日の星澪メモ」読み上げ処理 (内省の後に行う) ★★★
        if aivis_adapter and ai_name:
             # identity_file_path はスクリプト上部で定義済み
             speak_todays_reflection(identity_file_path, aivis_adapter, ai_name)
        else:
             logger.warning("TTSアダプターまたはAI名が初期化されていないため、今日の学びの読み上げをスキップします。")

        # 任意: 終了前にストリームのメモリを永続化する
        # ... (メモリ永続化処理はそのまま) ...

        print("YouTube Live 連携を終了しました。")


# --- スクリプト実行のエントリーポイント ---
if __name__ == "__main__":
    # 使用するYouTubeビデオIDを決定
    # 優先度: コマンドライン引数 > デフォルト値
    if len(sys.argv) > 1:
        youtube_video_id = sys.argv[1]
        logger.info(f"コマンドライン引数からYouTubeビデオIDを使用します: {youtube_video_id}")
    else:
        youtube_video_id = DEFAULT_YOUTUBE_VIDEO_ID
        logger.info(f"デフォルトのYouTubeビデオIDを使用します: {youtube_video_id}")

    # ビデオIDがプレースホルダーのままか、空でないかを確認
    if youtube_video_id == "YOUR_YOUTUBE_LIVE_VIDEO_ID" or not youtube_video_id:
        print("\n" + "="*60)
        print(" エラー: YouTube Live のビデオIDが設定されていません！")
        print(" スクリプト内の 'DEFAULT_YOUTUBE_VIDEO_ID' 変数を編集するか、")
        print(" コマンドライン引数でビデオIDを指定してください。")
        print(" 例: python scripts/run_youtube_live.py <実際のビデオID>")
        print("="*60 + "\n")
        sys.exit(1) # 有効なIDがない場合は終了

    # メインの連携関数を実行
    run_live(youtube_video_id)