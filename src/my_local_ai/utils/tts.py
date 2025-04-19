# src/my_local_ai/utils/tts.py
import sounddevice # sounddevice をインポート
import logging
import requests
import soundfile
import io
import json
from pathlib import Path
import platform
import logging # logging をインポート

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)

# --- 再生ライブラリのインポートと準備 ---
playsound_func = None
winsound_module = None

try:
    from playsound3 import playsound as playsound3_play
    playsound_func = playsound3_play
    logger.info("Playback library: playsound3 loaded.")
except ImportError:
    logger.warning("'playsound3' library not found. Will try winsound.")

if platform.system() == "Windows":
    try:
        import winsound
        winsound_module = winsound
        if playsound_func is None:
             logger.info("Playback library: winsound available (Windows fallback).")
    except ImportError:
        logger.info("winsound module not found on this Windows system.")
else:
    if playsound_func is None:
         logger.info("winsound is not available on non-Windows OS.")

if playsound_func is None and winsound_module is None:
    logger.error("音声再生ライブラリ (playsound3 または winsound) が見つかりません。")

# --- プロジェクトルートと一時ファイルのパス定義 ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    TEMP_WAV_DIR = PROJECT_ROOT / "data" / "temp"
    TEMP_WAV_FILENAME = TEMP_WAV_DIR / "_temp_aivis_output.wav"
    logger.debug(f"Project root determined: {PROJECT_ROOT}")
    logger.debug(f"Temporary WAV path: {TEMP_WAV_FILENAME}")
except NameError:
    PROJECT_ROOT = Path.cwd()
    TEMP_WAV_DIR = PROJECT_ROOT / "data" / "temp"
    TEMP_WAV_FILENAME = TEMP_WAV_DIR / "_temp_aivis_output.wav"
    logger.warning(f"Could not determine project root from __file__. Using CWD: {PROJECT_ROOT}")


# --- AivisAdapter クラス ---
class AivisAdapter:
    def __init__(self, url="http://127.0.0.1:10101", speaker_id=888753760):
        self.URL = url
        self.speaker = speaker_id
        logger.info(f"AivisAdapter Initialized. URL: {self.URL}, Speaker ID: {self.speaker}")

    def generate_voice_wav(self, text: str) -> bytes | None:
        if not text:
            logger.warning("AivisAdapter: Received empty text.")
            return None
        logger.info(f"AivisAdapter: Generating audio for text (length {len(text)})...")
        logger.debug(f"AivisAdapter: Text snippet: '{text[:30]}...'")
        try:
            query_params = {"text": text, "speaker": self.speaker}
            logger.debug(f"Sending audio_query request to {self.URL}/audio_query with params: {query_params}")
            query_response = requests.post(f"{self.URL}/audio_query", params=query_params, timeout=10)
            query_response.raise_for_status()
            audio_query_data = query_response.json()
            logger.info("AivisAdapter: Audio query successful.")
            logger.debug(f"Audio query data (keys): {list(audio_query_data.keys()) if isinstance(audio_query_data, dict) else 'N/A'}")


            synthesis_params = {"speaker": self.speaker}
            synthesis_headers = {"accept": "audio/wav", "Content-Type": "application/json"}
            logger.debug(f"Sending synthesis request to {self.URL}/synthesis with speaker: {synthesis_params['speaker']}")
            audio_response = requests.post(
                f"{self.URL}/synthesis", params=synthesis_params, headers=synthesis_headers,
                data=json.dumps(audio_query_data), timeout=20
            )
            audio_response.raise_for_status()
            logger.info(f"AivisAdapter: Synthesis successful (Received {len(audio_response.content)} bytes).")
            return audio_response.content

        except requests.exceptions.ConnectionError:
            logger.error(f"AivisAdapter: API ({self.URL}) に接続できません。アプリが起動していますか？")
        except requests.exceptions.Timeout:
            logger.error(f"AivisAdapter: API がタイムアウトしました。")
        except requests.exceptions.RequestException as e:
            logger.error(f"AivisAdapter: API リクエストエラー: {e}")
            if e.response is not None:
                 logger.error(f"       Status: {e.response.status_code}, Body: {e.response.text[:200]}...")
        except Exception as e:
            logger.exception(f"AivisAdapter: 音声生成中に予期せぬエラー") # logger.exceptionでトレースバックも記録
        return None


# --- 音声再生関数 ---
# --- 定数 (出力デバイス指定用) ---
# TODO: このデバイス名を設定ファイルなどで指定できるようにする
TARGET_OUTPUT_DEVICE_NAME = "Yamaha SYNCROOM Driver"

# --- 新しい speak 関数 (sounddevice版) ---
def speak(adapter: AivisAdapter, text_to_speak: str, target_device_name=TARGET_OUTPUT_DEVICE_NAME):
    """
    AivisAdapterで音声を生成し、指定されたオーディオデバイスで再生する (sounddeviceを使用)。
    target_device_name: 再生するデバイスの名前 (部分一致で検索)。Noneの場合はデフォルト。
    """
    wav_data = adapter.generate_voice_wav(text_to_speak)
    if not wav_data:
        logger.warning("AivisAdapterによる音声生成に失敗したため、再生をスキップします。")
        return

    device_id = None # sounddeviceで使用するデバイスID (整数)
    try:
        if target_device_name:
            devices = sounddevice.query_devices()
            logger.debug(f"利用可能なオーディオデバイス:\n{devices}") # デバッグ用に一覧表示
            found = False
            for i, dev in enumerate(devices):
                # 名前に部分一致し、かつ出力チャンネルがあるデバイスを探す
                if target_device_name.lower() in dev['name'].lower() and dev['max_output_channels'] > 0:
                    device_id = i
                    found = True
                    logger.info(f"ターゲット出力デバイス発見: '{dev['name']}' (Index: {device_id})")
                    break
            if not found:
                logger.warning(f"ターゲット出力デバイス '{target_device_name}' が見つからないか、出力デバイスではありません。デフォルトデバイスを使用します。")
        else:
             logger.info("ターゲットデバイス名が指定されていないため、デフォルトデバイスを使用します。")

    except Exception as e:
         logger.error(f"オーディオデバイスのクエリ中にエラー: {e}。デフォルトデバイスを使用します。")
         device_id = None # エラー時もデフォルトにフォールバック

    logger.info(f"音声再生試行 デバイス: {device_id if device_id is not None else 'デフォルト'}")

    try:
        # BytesIOを使ってメモリ上でWAVデータを読み込み、numpy配列に変換
        with io.BytesIO(wav_data) as audio_stream:
            # sounddeviceはfloat32形式を推奨
            audio_data, samplerate = soundfile.read(audio_stream, dtype='float32')

        # 指定されたデバイス (device_id) またはデフォルト (None) で再生
        # play()は非同期なので、完了を待つために wait() を使う
        sounddevice.play(audio_data, samplerate, device=device_id)
        logger.debug(f"デバイス {device_id if device_id is not None else 'デフォルト'} で再生開始。完了待ち...")
        sounddevice.wait() # 再生完了を待機
        logger.info("音声再生完了。")

    except sounddevice.PortAudioError as pae:
         logger.error(f"PortAudioエラー: {pae}")
         logger.error("オーディオデバイスが正しく動作しているか、選択が正しいか確認してください。")
    except Exception as e:
        logger.exception("sounddeviceでの音声再生中に予期せぬエラーが発生しました。")