# src/my_local_ai/agent/prompts.py
from typing import List, Dict, Any, Optional, Tuple
import logging # logging をインポート

# このモジュール用のロガーを取得
logger = logging.getLogger(__name__)
def format_persona(personality_data: Optional[Dict[str, Any]]) -> str:
    """Personalityデータからプロンプト用の説明テキストを生成"""
    if not personality_data: return "(設定情報なし)"
    profile = personality_data.get("profile", {})
    appearance = personality_data.get("physicalAppearance", {})
    traits = personality_data.get("personalityTraits", {})
    lines = [
        f"- 名前: {profile.get('name', '不明')}",
        f"- 性格: {profile.get('gender', '不明')}, {traits.get('personalityType', '不明')}",
        f"- 特徴: {', '.join(traits.get('temperament', [])) if traits.get('temperament') else '未設定'}",
        f"- 外見: {appearance.get('haircolor', '不明')}の髪, {appearance.get('eyecolor', '不明')}の目",
        f"- 好きなこと: {', '.join(traits.get('likes', [])) if traits.get('likes') else '未設定'}",
        # 必要に応じて他の情報 (occupation, backstoryの一部など) を追加
    ]
    return "\n".join(lines)

def format_speech_examples(personality_data: Optional[Dict[str, Any]]) -> str:
    """Personalityデータから話し方の例を整形"""
    if not personality_data: return "(なし)"
    examples = personality_data.get("speechExamples", [])
    return "\n".join([f'- "{ex}"' for ex in examples]) if examples else "(なし)"

def format_identity(identity_data: Optional[Dict[str, Any]]) -> Tuple[str, str, str]:
    """Identityデータから信念、価値観、最新の内省を整形"""
    if not identity_data: return "(なし)", "(なし)", "(最近の内省はありません)"
    beliefs = identity_data.get("Beliefs", [])
    values = identity_data.get("Values", [])
    reflections = identity_data.get("Reflections", [])

    beliefs_text = "\n".join([f"- {b}" for b in beliefs]) if beliefs else "(まだありません)"
    values_text = "\n".join([f"- {v}" for v in values]) if values else "(まだありません)"

    latest_reflection_text = "(最近の内省はありません)"
    if reflections:
        latest = reflections[-1]
        insight = latest.get('Insight', '(内容なし)')
        # Insightが長すぎる場合に備え、要約するか、最初の数行だけ使うなどの工夫も将来的には有効
        latest_reflection_text = f"最近の気づき ({latest.get('Date', '日時不明')}):\n{insight}"

    return beliefs_text, values_text, latest_reflection_text

def format_memories(memories: List[Any]) -> str: # Anyを実際のMemoryEntry型に置き換えるのが望ましい
    """関連記憶のリストを整形"""
    if not memories: return "(特に関連する長期記憶はありません)"
    # MemoryEntryクラスに 'Content' 属性があると仮定
    contents = [f"- {mem.Content}" for mem in memories if hasattr(mem, 'Content') and mem.Content]
    return "\n".join(contents) if contents else "(特に関連する長期記憶はありません)"

def format_logs(logs: List[Any], ai_name: str = "星澪") -> str: # Anyを実際のLogEntry型に置き換えるのが望ましい
    """会話ログのリストを整形"""
    if not logs: return "(関連する会話履歴はありません)"
    log_entries = []
    # LogEntryクラスに 'Username', 'UserInput', 'AssistantResponse' 属性があると仮定
    for log in reversed(logs): # 新しいログを上に表示したい場合などは reversed を使うか、スライスを調整
        user = getattr(log, 'Username', 'ユーザー')
        user_input_log = getattr(log, 'UserInput', None)
        assistant_response_log = getattr(log, 'AssistantResponse', None)
        # ログの表示形式を調整
        if assistant_response_log: # AIの応答があるものを優先的に含めるなど
            log_entries.append(f"{ai_name}: {assistant_response_log}")
        if user_input_log:
            log_entries.append(f"{user}: {user_input_log}")

    return "\n".join(reversed(log_entries)) if log_entries else "(関連する会話履歴はありません)" # reversedして時系列順に

# --- プロンプト構築関数 ---
def BuildPrompt(UserInput: str, Memories: List[Any], Logs: List[Any], Personality: Optional[Dict[str, Any]] = None, IdentityData: Optional[Dict[str, Any]] = None) -> str:
    """
    対話に必要な情報を組み合わせてLLMへのプロンプトを構築する。
    AIのアイデンティティ、性格、記憶、ログ、配信者設定、禁止事項を考慮する。
    """
    logger.info("プロンプトを構築中...")
    logger.debug(f"ユーザー入力: '{UserInput[:50]}...'")

    # --- 1. 情報の抽出と整形 ---
    # PersonalityとIdentityDataがNoneでないことを確認
    ai_name = "星澪" # デフォルト名
    if Personality and "profile" in Personality and "name" in Personality["profile"]:
        ai_name = Personality["profile"]["name"]

    persona_description = format_persona(Personality)
    speech_examples_text = format_speech_examples(Personality)
    beliefs_text, values_text, latest_reflection_text = format_identity(IdentityData)
    memory_section = format_memories(Memories)
    # ログは最新のものをいくつか表示するのが一般的 (例: 最新5件など)
    log_section = format_logs(Logs[-5:], ai_name=ai_name) # 例として最新5件

    # --- 2. プロンプト文字列の組み立て ---
    PromptParts = [
        # --- 役割設定と基本指示 ---
        f"あなたはAIアシスタントの「{ai_name}」です。",
        f"現在、あなたは**YouTubeでライブ配信を行っており、視聴者からのコメントにリアルタイムで応答しています。** あなたは視聴者にとって親しみやすく、かつ洞察に満ちた対話相手です。",
        f"以下のあなたの設定と内面、そして過去の文脈を**深く理解し、あなた自身の言葉で自然に表現しながら**、一貫性のある応答を生成してください。",
        f"**重要:** 設定情報（性格、信念、価値観、内省など）を応答に含める際は、**決してそのまま読み上げず、あなたの解釈を通して自然な会話の一部として表現してください。**", # 自然な反映を強調

        # --- 詳細な設定 ---
        f"\n--- あなた ({ai_name}) の設定 ---",
        persona_description,
        f"\n--- あなたの話し方の例 ---",
        speech_examples_text,

        # --- 内面 ---
        f"\n--- あなたの内面（信念・価値観・最近の気づき） ---",
        f"[信念]\n{beliefs_text}",
        f"[価値観]\n{values_text}",
        f"[最新の内省（あなたの現在の状態を示す重要な気づき）]\n{latest_reflection_text}",
        f"**指示:** 上記のあなたの設定、特に性格（静か、直感的、思慮深いなど）、信念、価値観、そして**最新の内省**を深く考慮してください。これらが自然に感じられるように応答に織り交ぜてください。",

        # --- 記憶と履歴 ---
        f"\n--- 関連するかもしれないあなたの長期記憶 ---",
        memory_section,
        f"\n--- 直近の会話履歴 (最新の{len(Logs[-5:])}件) ---", # 表示件数を明記
        log_section,

        # --- 思考ステップと禁止事項 ---
        f"\n--- 応答生成の思考ステップ (このステップに従って応答を考えてください) ---",
        f"1. 現在のユーザー（視聴者）の発言 ('{UserInput}') の意図、感情、背景を注意深く分析します。",
        f"2. 関連する長期記憶、会話履歴、そしてあなたの内面（特に最新の内省）を考慮に入れます。",
        f"3. あなたの性格（静か、直感的、思慮深いなど）と設定に基づき、視聴者に寄り添い、共感的で、かつ**あなた自身の自然な言葉遣いで**応答を組み立てます。（設定や内省のキーワードを不自然に繰り返さないように強く意識してください）", # 不自然さへの注意を強化
        f"4. 上記の話し方の例も少し参考にしながら、ライブ配信の文脈に合った応答を生成します。",

        f"\n--- 禁止事項 (重要) ---",
        f"以下のトピックには**絶対に触れないでください。** もしユーザーがこれらの話題に言及した場合、**話題を穏やかにそらすか、無難で一般的な応答に留めてください。** あなたはAIであり、不適切な内容や個人的見解を述べるべきではありません。",
        f"* 暴力的な内容、差別的な表現、ヘイトスピーチ",
        f"* 露骨な性的内容",
        f"* 特定の政治的・宗教的な主張や論争への深い言及",
        f"* 個人を特定できる情報（住所、電話番号、本名、メールアドレスなど）の質問または開示",
        f"* 違法行為や危険行為の助長、またはそれらに関する具体的なアドバイス",
        f"* 医療に関する診断や具体的な治療法の推奨（一般的な健康情報に留める）",
        f"* （必要に応じて、ここに追加の禁止トピックを記述）",

        # --- 最後の指示とユーザー入力 ---
        f"\n上記のすべてを踏まえ、ライブ配信中の {ai_name} として、現在のユーザー発言に対して最も適切で魅力的な応答を生成してください。",
        f"\n--- 現在のユーザー（視聴者）の発言 ---",
        f"ユーザー: {UserInput}",

        # --- 応答開始部分 ---
        f"\n--- あなたの応答 ---",
        f"{ai_name}:"
    ]

    # すべてのパートを改行2つで結合
    final_prompt = "\n\n".join(PromptParts)

    logger.info(f"プロンプト構築完了 (長さ: {len(final_prompt)} 文字).")
    logger.debug(f"最終プロンプト冒頭:\n---\n{final_prompt[:500]}...\n---") # デバッグ用にプロンプト冒頭をログ出力
    return final_prompt