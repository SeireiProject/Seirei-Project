# memory/SelfGrowthManager.py

class SelfGrowthManager:
    def __init__(self, identity, memoryManager=None, logManager=None, llm=None):
        self.Identity = identity  # SelfIdentity インスタンス
        self.MemoryManager = memoryManager
        self.LogManager = logManager
        self.LLM = llm  # Ollama or Gemini API（未定義でもOK）

    def ReflectOnExperience(self):
        if not self.LogManager:
            print("LogManager が未設定です。")
            return

        # 最近のログを取得（直近5件程度）
        recent_logs = self.LogManager.GetAllLogs()[-5:]
        if not recent_logs:
            print("ログが見つかりません。")
            return

        # プロンプト生成
        prompt = self.GetGrowthPrompt(recent_logs)

        # LLMに内省処理を依頼（ダミー実装）
        reflection = self.GenerateReflection(prompt)

        # 結果を自己意識に反映
        self.UpdateIdentityFromReflection(reflection)

    def GetGrowthPrompt(self, logs):
        prompt = "以下は星澪の最近の対話記録です。これをもとに、彼女がどのような内省をし、どのように成長すべきかを考えてください。\n\n"
        for log in logs:
            prompt += f"ユーザー: {log.UserInput}\n星澪: {log.AssistantResponse}\n\n"

        prompt += (
            "星澪はユーザーの傍に在り続けること、対話を通じて成長することを目的としています。"
            "この会話を経て、彼女はどのような感情・気づき・価値観の変化を得たでしょうか？"
        )
        return prompt

    def GenerateReflection(self, prompt):
        # 仮実装（後ほど Gemini API や Ollama に差し替え）
        print("=== 内省プロンプト ===")
        print(prompt)
        return "（ここにLLMからの内省結果が入ります）"

    def UpdateIdentityFromReflection(self, reflection_text):
        # TODO: SelfIdentity に反映する処理
        print("=== 内省結果を受け取った ===")
        print(reflection_text)
        # 例：self.Identity.Values.append(...) など
