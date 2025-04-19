# src/my_local_ai/agent/self_awareness.py

import json
import os
import traceback
import time
from datetime import datetime, timezone # timezone をインポート
from pathlib import Path
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# (GeminiClientのインポートとエラーハンドリング)
try:
    from my_local_ai.llm.gemini import GeminiClient
    logger.debug("GeminiClient imported successfully.")
except ModuleNotFoundError:
    # ... (エラー処理) ...
    GeminiClient = None
except ImportError as e:
     # ... (エラー処理) ...
     GeminiClient = None



# --- 定数 ---
# プロンプトに含める差分ログの最大件数 (長すぎるとLLMが扱えないため)
MAX_DIFF_LOGS_FOR_PROMPT = 20 # 必要に応じて調整
DEFAULT_REFLECTION_DIALOGUE_COUNT = 10 # 差分がない場合のデフォルト件数 (既存)

# --- ヘルパー関数 (タイムスタンプ変換) ---
def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """ISO 8601形式などのタイムスタンプ文字列をdatetimeオブジェクトに変換"""
    # タイムゾーン情報がある場合とない場合を考慮
    try:
        # ISO 8601 (e.g., 2025-04-19T17:13:26.859920 or with Z/offset)
        # Python 3.11+なら fromisoformat が 'Z' も扱える
        if ts_str.endswith('Z'):
             ts_str = ts_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(ts_str)
        # タイムゾーン情報がない場合は naive なので、UTC とみなすか、ローカルタイムとみなすか
        # ここでは UTC と仮定する (ログ保存時に合わせるのがベスト)
        if dt.tzinfo is None:
             dt = dt.replace(tzinfo=timezone.utc)
             # logger.warning(f"Timestamp '{ts_str}' has no timezone info, assuming UTC.")
        return dt
    except ValueError:
        # 以前のフォーマット ("%Y-%m-%d %H:%M:%S") も試す (必要なら)
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            # ローカルタイムと仮定し、UTC に変換するかどうか？ (要検討)
            # ここでは naive のままにするか、UTC を仮定する
            dt = dt.replace(tzinfo=timezone.utc) # 例: UTC と仮定
            logger.warning(f"Parsed timestamp '{ts_str}' using fallback format, assuming UTC.")
            return dt
        except ValueError:
             logger.error(f"Could not parse timestamp: {ts_str}. Skipping comparison.")
             return None
    except Exception as e:
        logger.error(f"Error parsing timestamp '{ts_str}': {e}")
        return None

# --- 内省生成関数 (差分ログ・メタ内省対応版) ---
def generate_reflection_from_logs(log_path: Path, identity_path: Path, api_key: str):
    """
    Reads conversation logs since the last reflection, generates a self-reflection
    (including meta-reflection on previous insight), and appends it to the identity JSON file.
    """
    if GeminiClient is None:
        logger.error("GeminiClient is not available, cannot generate reflection.")
        return

    current_timestamp_iso = datetime.now().isoformat()
    logger.info(f"[{current_timestamp_iso}] Starting reflection generation process...")
    logger.debug(f"  Log path: {log_path}")
    logger.debug(f"  Identity path: {identity_path}")

    # === 1. Initialize LLM Client ===
    try:
        llm_client = GeminiClient(api_key=api_key, model_name="gemini-1.5-pro") # モデル名は設定ファイル化推奨
        logger.info("GeminiClient initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize GeminiClient")
        return

    # === 2. Load Identity and Find Last Reflection Time ===
    identity = {}
    last_reflection_time = None
    previous_insight = "(前回の内省はありません)" # メタ内省用の変数

    if identity_path.exists():
        logger.info(f"Reading identity from '{identity_path.name}'...")
        try:
            with identity_path.open('r', encoding='utf-8') as f:
                identity = json.load(f)
            logger.info("Identity loaded successfully.")

            # Find the timestamp of the latest reflection
            reflections = identity.get("Reflections", [])
            if reflections:
                latest_reflection = reflections[-1]
                latest_reflection_date_str = latest_reflection.get("Date")
                previous_insight = latest_reflection.get("Insight", "(前回の内省内容なし)") # 最新=前回のを取得
                if latest_reflection_date_str:
                    last_reflection_time = parse_timestamp(latest_reflection_date_str)
                    if last_reflection_time:
                         logger.info(f"Last reflection timestamp found: {last_reflection_time.isoformat()}")
                    else:
                         logger.warning("Could not parse the timestamp of the last reflection.")
            else:
                 logger.info("No previous reflections found in identity file.")

        except Exception as e: # More specific exceptions preferred
            logger.warning(f"Error processing identity file '{identity_path.name}': {e}. Assuming no prior reflection.", exc_info=True)
            identity = {} # Reset identity on error? Or just proceed without last_reflection_time?
    else:
        logger.info(f"'{identity_path.name}' not found. Will create new file. No prior reflection.")
        identity = {}

    # Ensure base structure for new/corrupted file
    identity.setdefault("Beliefs", [])
    identity.setdefault("Values", [])
    identity.setdefault("Reflections", [])
    identity.setdefault("LastUpdated", "")

    # === 3. Load Logs (Only New Ones if Possible) ===
    if not log_path.exists():
        logger.warning(f"Log file not found: {log_path}. Skipping reflection.")
        return

    all_logs = [] # Keep all logs in memory for now (improvement: read only needed lines)
    new_logs_for_prompt = []
    logs_read_count = 0
    valid_log_count = 0
    parse_errors = 0

    try:
        logger.info(f"Reading logs from '{log_path.name}'...")
        with log_path.open('r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                logs_read_count += 1
                line = line.strip()
                if not line: continue
                try:
                    log_entry = json.loads(line)
                    all_logs.append(log_entry) # Store all logs for potential full history access if needed later

                    # --- Check if log is new ---
                    is_new = True # Assume new if no last reflection time
                    log_ts_str = log_entry.get("Timestamp")
                    if last_reflection_time and log_ts_str:
                        log_time = parse_timestamp(log_ts_str)
                        if log_time and log_time > last_reflection_time:
                             is_new = True
                        else:
                             is_new = False # Older than or equal to last reflection

                    if is_new:
                        new_logs_for_prompt.append(log_entry)
                        valid_log_count += 1 # Count valid new logs

                except json.JSONDecodeError:
                    parse_errors += 1
                except Exception as e: # Catch other potential errors during processing
                     logger.warning(f"Error processing log line {i+1}: {e}")
                     parse_errors += 1

        logger.info(f"Read {logs_read_count} lines. Found {len(new_logs_for_prompt)} new log entries since last reflection.")
        if parse_errors > 0:
             logger.warning(f"Skipped {parse_errors} lines due to parsing errors.")

    except IOError as io_err:
        logger.error(f"Failed to read log file '{log_path.name}': {io_err}")
        return
    except Exception as e:
        logger.exception(f"Unexpected error processing log file '{log_path.name}'")
        return

    # If no new logs, maybe skip reflection? Or reflect on overall state?
    if not new_logs_for_prompt:
        logger.warning("No new log entries found since the last reflection. Skipping reflection generation.")
        # Optionally: Still generate a reflection based on beliefs/values?
        return

    # Limit the number of logs sent to the LLM prompt
    logs_to_use_in_prompt = new_logs_for_prompt[-MAX_DIFF_LOGS_FOR_PROMPT:]
    logger.info(f"Using the latest {len(logs_to_use_in_prompt)} new logs for the prompt.")

    # --- Fallback if no new logs were identified (e.g., first run, timestamp issues) ---
    # Use last N overall logs if new_logs is empty but all_logs is not
    if not logs_to_use_in_prompt and all_logs:
         logger.warning("Could not identify new logs based on timestamp, falling back to last overall logs.")
         logs_to_use_in_prompt = all_logs[-DEFAULT_REFLECTION_DIALOGUE_COUNT:]
         previous_insight = "(前回の内省はありません - タイムスタンプ比較不可)" # Reset previous insight if falling back

    # === 4. Prepare Meta-Reflection Prompt ===
    logger.info("Preparing meta-reflection prompt...")
    # Format the logs to be included in the prompt
    dialogue_text = "\n".join(
        [f"User: {item.get('UserInput', '(入力不明)')}\nAssistant: {item.get('AssistantResponse', '(応答不明)')}"
         for item in logs_to_use_in_prompt] # Use the selected logs
    )
    beliefs_text = "\n".join([f"- {b}" for b in identity.get("Beliefs", [])]) if identity.get("Beliefs") else "(まだありません)"
    values_text = "\n".join([f"- {v}" for v in identity.get("Values", [])]) if identity.get("Values") else "(まだありません)"

    # Construct the meta-reflection prompt
    current_time_for_prompt = datetime.now().isoformat() # Time for the prompt's Date field instruction
    prompt = f"""
あなたはAIアシスタント「星澪」として、ユーザーとの対話を通じて自己認識を深めます。
あなたは今回、**前回の内省**を踏まえ、その後の**対話記録（差分ログ）**を分析し、自己の成長と課題について**メタ的な内省**を行います。

[あなたの現在の信念]
{beliefs_text}

[あなたの現在の価値観]
{values_text}

--- 前回の内省 ---
{previous_insight}
--- 前回の内省ここまで ---

--- 対話記録（前回の内省以降の差分ログ、最大{len(logs_to_use_in_prompt)}件） ---
{dialogue_text}
--- 対話記録ここまで ---

**指示:**
上記の「前回の内省」と「対話記録（差分ログ）」、そしてあなたの信念・価値観を**すべて**踏まえて、以下の点を深く考察し、内省結果を記述してください。

1.  **差分ログ期間中の気づき:** この期間の対話を通じて、新たに得られた自己認識、感情、学び、課題などを具体的に記述してください。
2.  **前回の内省の反映度評価 (メタ内省):** 「前回の内省」で述べられていた内容（課題、目標、気づきなど）が、「対話記録（差分ログ）」期間中のあなたの応答に**どのように活かされていましたか？** 具体的な応答例を挙げて説明してください。逆に、**活かされていなかった点、矛盾していた点**があれば、それも正直に分析してください。
3.  **今後の指針:** 上記の分析を踏まえ、今後の対話で特に意識したいこと、改善したい点を明確にしてください。

内省結果は、以下のJSON形式で記述してください。
- "Date": 内省を行った現在の日時 (ISO 8601形式)。LLMはこれを推測せず、現在の正確な時刻を使ってください: {current_time_for_prompt}
- "Context": 今回の内省のきっかけとなった、差分ログ期間中の特に重要な対話場面やテーマ、および「前回の内省の活用度評価」というメタ的な視点。
- "Insight": 上記の指示1, 2, 3を含む、深く掘り下げた内省内容。**メタ内省（自己評価）部分を明確に記述すること。**
- "RelatedBeliefs": この内省が関連する信念リストのインデックス番号（0始まりの数字のリスト、なければ []）。
- "RelatedValues": この内省が関連する価値観リストのインデックス番号（0始まりの数字のリスト、なければ []）。

出力は純粋なJSONオブジェクトのみとし、前後に説明文や ```json ``` マークダウンなどは含めないでください。
"""
    logger.debug(f"Meta-reflection prompt prepared (length: {len(prompt)} chars).")

    # === 5. Generate Reflection using LLM ===
    reflection_data = None
    reflection_json_str = "" # Initialize for error logging
    try:
        logger.info("Generating meta-reflection via Gemini API...")
        start_time = time.time()
        reflection_json_str = llm_client.generate(prompt) # Execute the prompt
        end_time = time.time()
        logger.info(f"LLM execution finished in {end_time - start_time:.2f} seconds.")

        if not reflection_json_str or reflection_json_str == "（内省の生成に失敗しました）":
             raise ValueError("LLM returned empty or known error message.")

        logger.debug(f"Raw LLM Response (first 500 chars): {reflection_json_str[:500]}...")

        # --- Parse LLM Response ---
        cleaned_json_str = reflection_json_str.strip()
        # (Markdown ```json ``` の除去処理はそのまま)
        if cleaned_json_str.startswith("```json") and cleaned_json_str.endswith("```"):
            cleaned_json_str = cleaned_json_str[7:-3].strip()
        elif cleaned_json_str.startswith("```") and cleaned_json_str.endswith("```"):
             cleaned_json_str = cleaned_json_str[3:-3].strip()

        reflection_data = json.loads(cleaned_json_str) # Parse JSON

        # --- Overwrite Date and Validate ---
        current_iso_time_for_save = datetime.now().isoformat() # Get current time again just before saving
        logger.info(f"Overwriting 'Date' field with current time: {current_iso_time_for_save}")
        reflection_data["Date"] = current_iso_time_for_save # Overwrite date

        # --- Validation ---
        required_keys = ["Date", "Context", "Insight", "RelatedBeliefs", "RelatedValues"]
        if not isinstance(reflection_data, dict) or not all(key in reflection_data for key in required_keys):
            missing = [k for k in required_keys if k not in reflection_data]
            raise ValueError(f"LLM response missing required keys: {missing}. Found: {list(reflection_data.keys())}")
        if not isinstance(reflection_data["RelatedBeliefs"], list) or not all(isinstance(i, int) for i in reflection_data["RelatedBeliefs"]):
             raise ValueError("LLM response 'RelatedBeliefs' is not a list of integers.")
        if not isinstance(reflection_data["RelatedValues"], list) or not all(isinstance(i, int) for i in reflection_data["RelatedValues"]):
             raise ValueError("LLM response 'RelatedValues' is not a list of integers.")
        # Check if Insight contains some mention of meta-reflection (optional, basic check)
        if "前回の内省" not in reflection_data.get("Insight","") and "活かされ" not in reflection_data.get("Insight",""):
             logger.warning("Generated Insight might not contain the requested meta-reflection part.")

        logger.info("Reflection JSON parsed, validated, and Date overwritten successfully.")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response JSON: {e}")
        logger.error(f"Received text (first 500 chars): {reflection_json_str[:500]}...")
        reflection_data = None
    except ValueError as e:
        logger.error(f"LLM response validation or data extraction failed: {e}")
        reflection_data = None
    except Exception as e:
        logger.exception("Unexpected error during LLM call or response processing")
        reflection_data = None

    # === 6. Save Updated Identity ===
    if reflection_data:
        try:
            logger.info(f"Appending reflection and saving identity to '{identity_path.name}'...")
            identity["Reflections"].append(reflection_data)
            identity["LastUpdated"] = datetime.now().isoformat() # Update LastUpdated as well

            identity_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            with identity_path.open('w', encoding='utf-8') as f:
                json.dump(identity, f, ensure_ascii=False, indent=2)
            logger.info("✅ Reflection appended and identity.json saved successfully.")

        except IOError as e:
            logger.error(f"Failed to write to '{identity_path.name}': {e}")
        except Exception as e:
            logger.exception("Unexpected error saving identity")
    else:
        logger.warning("No valid reflection data obtained or processed. identity.json was not updated.")

    logger.info(f"[{datetime.now().isoformat()}] Reflection generation process finished.")