# AI Project "Seirei" (星澪) - 共に成長する対話型AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ## 概要

**星澪（せいれい）**は、あなたとの対話を通じて学び、自ら内省することで**自己成長**していくAIです。さらに、このプロジェクトはオープンソースであり、**視聴者やコミュニティの皆さんからの貢献によって育てられる**ことを目指しています。

ローカルLLM (Ollama) や外部API (Google Gemini) を活用し、記憶に基づいた自然な会話を行います。将来的にはAITuberとしての活動を視野に入れ、現在YouTube Liveとの連携機能などを開発中です。

**あなたも星澪の成長に参加しませんか？**

## コンセプト

* **自己成長 (Self-Growth):** 星澪は、ユーザーとの対話ログを基に定期的に自己内省を行い、自身の信念や価値観、応答パターンを更新していきます (`config/identity.json` に記録)。
* **視聴者による育成 (Community-Driven Growth):** このプロジェクトのコードは公開されており、バグ報告、機能提案、コード改善などを通じて、視聴者や開発者コミュニティの皆さんが星澪の成長に直接貢献できます。
* **AITuberとしての活動:** これらの成長を通じて、将来的にはより表現豊かでインタラクティブなAITuberとして活動することを目指します。

## 主な機能

* **対話応答:** ローカルLLM (Ollama) または外部LLMを利用して、自然な対話応答を生成します。
* **人格「星澪」:** `config/personality.json` に基づいた個性的な応答を行います（銀髪、青い目、静かで思慮深い性格など）。
* **長期記憶 (RAG):** `sentence-transformers` を用いたベクトル検索により、関連する過去の記憶 (`data/memories.json` 等) を参照して応答に深みを持たせます。
* **会話ログ:** ユーザーとの対話を記録・参照します (`data/logs.json` 等)。
* **自己内省:** 対話ログを基にGoogle Gemini APIを利用して内省を行い、自身の認識を更新します (`config/identity.json`)。
    * **差分ログ利用:** 前回の内省以降のログを対象とします。
    * **メタ内省:** 前回の内省がどう活かされたかを評価する機能も含まれます。
* **コマンドラインインターフェース (CLI):** ターミナル上で星澪と対話や記憶管理が可能です (`src/my_local_ai/interfaces/cli.py`)。
* **YouTube Live連携:**
    * リアルタイムでのコメント取得と応答 (`scripts/run_youtube_live.py`)。
    * 音声合成 (TTS) による応答の読み上げ (現在はAivisに対応、`sounddevice` で仮想オーディオデバイス等に出力可能)。
    * 配信終了時の自動内省と「今日の学び」の読み上げ。
* **テストコード:** `pytest` を用いたユニットテスト (`tests/`)。

## 技術スタック

* Python 3.10+
* Ollama (ローカルLLM実行環境)
* Google Gemini API (内省機能)
* Sentence Transformers (テキストEmbedding)
* PyYAML (設定ファイル読み込み) * Pytchat (YouTubeコメント取得)
* Sounddevice (音声出力制御)
* Aivis (TTSエンジン連携例)
* Pytest (テストフレームワーク)
* (その他、`requirements.txt` 参照)

## 必要なもの (Requirements)

* **Python:** 3.10 以降
* **Git:** コードの取得や貢献に必要です。
* **Ollama環境 (推奨):**
    * Ollamaがインストールされ、実行中であること。
    * 対話に使用するモデル (例: `elyza:jp8b`) がダウンロード済みであること (`ollama pull elyza:jp8b`)。
* **Google API Key (内省機能に必要):**
    * Google Cloud Platform で API キーを取得してください。
    * 詳細はセットアップ手順を参照。
* **TTSエンジン環境 (任意):**
    * 音声読み上げを使用する場合、対応するTTSエンジン (例: Aivis) が必要です。
* **仮想オーディオデバイス (任意):**
    * 配信ソフト (OBS等) へ音声を入力する場合に必要です (例: VB-Audio Virtual Cable)。
* **OS:** 主にWindowsで開発・テスト。macOS/Linux での動作は未確認な部分があります。
* その他Pythonライブラリ: `requirements.txt` に記載。

## セットアップ (Setup)

1.  **リポジトリをクローン:**
    ```bash
    git clone [https://github.com/](https://github.com/)[あなたのユーザー名]/[リポジトリ名].git
    cd [リポジトリ名]
    ```
2.  **仮想環境の作成と有効化 (推奨):**
    ```bash
    python -m venv venv
    # Windows (PowerShell)
    .\venv\Scripts\Activate.ps1
    # Windows (Command Prompt)
    .\venv\Scripts\activate.bat
    # macOS/Linux
    # source venv/bin/activate
    ```
3.  **依存ライブラリのインストール:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **APIキーの設定:**
    * プロジェクトのルートディレクトリ (`[リポジトリ名]/`) に `.env` という名前のファイルを作成します。（もし `.env.example` ファイルがあれば、それをコピーして `.env` にリネームします）
    * 以下の内容を記述し、`your_actual_key` を実際の Google API キーに置き換えます。
        ```dotenv
        GOOGLE_API_KEY=your_actual_key
        ```
    * **注意:** `.env` ファイルは `.gitignore` に含まれており、リポジトリには公開されません。**絶対にAPIキーを直接コードやリポジトリに含めないでください。**
5.  **Ollama の準備:**
    * Ollama をインストールし、実行しておきます。
    * 使用したいモデルをダウンロードします (例: `ollama pull elyza:jp8b`)。
6.  **TTS / 仮想オーディオデバイスの準備 (必要に応じて):**
    * 使用するTTSエンジン (Aivis等) をインストール・起動します。
    * 仮想オーディオデバイス (VB-Audio Virtual Cable等) をインストールします。

## 設定 (Configuration)

* **主要な設定:**
    * **[今後]** `config/config.yaml` ファイルでLLMモデル名、APIエンドポイント、TTS設定、音声デバイス名などを一元管理します。（詳細は `config.yaml` 内のコメントを参照）
    * **[現状]** 各スクリプト (`run_youtube_live.py`,`llm/ollama.py`, `llm/gemini.py`, `utils/tts.py` など) の上部で設定値が定義されています。
* **人格設定:** `config/personality.json` を編集することで、星澪の基本的な性格、外見、話し方などを変更できます。
* **アイデンティティ (記憶):** `config/identity.json` には、星澪の信念、価値観、そして自己内省の結果が自動的に記録・蓄積されていきます。**通常、このファイルを手動で編集する必要はありません。**

## 実行方法 (How to Run)

* **コマンドラインインターフェース (CLI):**
    * ターミナルでプロジェクトルートにいることを確認し、仮想環境を有効にします。
    * `python src/my_local_ai/interfaces/cli.py` を実行します。
* **YouTube Live連携:**
    * ターミナルでプロジェクトルートにいることを確認し、仮想環境を有効にします。
    * `.env` ファイルに `GOOGLE_API_KEY` が設定されていることを確認します。
    * OllamaとTTSエンジン (Aivis等) を起動しておきます。
    * `python scripts/run_youtube_live.py [YouTubeビデオID]` を実行します。
        * `[YouTubeビデオID]` を実際のライブ配信のIDに置き換えます。
        * 引数を省略した場合は、スクリプト内の `DEFAULT_YOUTUBE_VIDEO_ID` が使用されます（要設定）。
* **手動での内省実行:**
    * `.env` ファイルに `GOOGLE_API_KEY` が設定されていることを確認します。
    * `python scripts/run_reflection.py` を実行します。(`identity.json` が更新されます)。

## 使い方 (Usage)

* **CLI:**
    * プロンプト (`You:`) に続けてメッセージを入力すると、星澪が応答します。
    * 利用可能なコマンド:
        * `:save <内容>`: 内容を長期記憶に保存。
        * `:show memory`: 長期記憶を一覧表示。
        * `:edit <番号> <新しい内容>`: 指定番号の記憶を編集。
        * `:forget <番号>`: 指定番号の記憶を削除。
        * `:help`: ヘルプを表示。
        * `exit`: 終了。
* **YouTube Live連携:**
    * 実行すると、指定したライブ配信のコメントを読み取り、星澪が応答（コンソール表示＋音声読み上げ）します。
    * スクリプトを `Ctrl+C` で停止すると、自動的にその時点までのログで内省を行い、「今日の星澪メモ」として読み上げてから終了します。

## 貢献 (Contribution) - あなたも星澪を育てませんか？

このプロジェクトは、コミュニティの皆さんと一緒にAI「星澪」を育てていくことを目指しています！
**開発者はプログラミング初心者で、プロジェクトのコードの大部分はAI（Google Gemini）によって書かれています。そのため、改善の余地が多く残されています！** 
バグの発見、コードの改善提案（もっと良い書き方があるよ！など）、新しい機能のアイデア、星澪に覚えてほしい知識の提案など、どんな小さな貢献でも大歓迎です。


* **コード貢献 (Pull Request):**
    1.  このリポジトリを **Fork** します。
    2.  新しいブランチを作成します (`git checkout -b feature/your-feature-name`)。
    3.  変更を加えてコミットします (`git commit -m "Add some feature"`)。
    4.  あなたのForkしたリポジトリにプッシュします (`git push origin feature/your-feature-name`)。
    5.  GitHub上で **Pull Request** を作成し、変更内容を説明してください。

貢献に関する詳しいガイドラインは、を参照してください。

## ライセンス (License)

このプロジェクトは [**MIT License**](LICENSE) の下で公開されています。
## 謝辞 (Acknowledgements)

* このプロジェクトは、多くの優れたオープンソースライブラリや技術（Ollama, Sentence Transformers, Pytchat, etc.）の上に成り立っています。開発者の皆様に感謝いたします。