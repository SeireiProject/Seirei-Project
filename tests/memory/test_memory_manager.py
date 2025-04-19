# tests/memory/test_memory_manager.py
import pytest
import os
import json
from pathlib import Path
# テスト対象のクラスをインポート (絶対パスで)
from my_local_ai.memory.memory_manager import MemoryManager
# Embedderも必要になるかもしれないのでインポート
from my_local_ai.memory.embedder import Embedder

# テストで使用する一時的なファイルパスを定義
# pytestのフィクスチャを使うとより綺麗に書けますが、まずはシンプルに
TEST_MEMORY_FILE = "test_memories.json"

@pytest.fixture # テスト実行前に呼ばれ、後処理も行う pytest の機能
def memory_manager_instance():
    """テスト用のMemoryManagerインスタンスを作成し、テスト後にファイルを削除する"""
    # Embedderのインスタンスも作成 (テストによってはモック化することもあります)
    embedder = Embedder()
    # テスト用のファイルパスを指定して MemoryManager を初期化
    mm = MemoryManager(memory_path=TEST_MEMORY_FILE, embedder=embedder)
    # テスト関数にインスタンスを渡す
    yield mm
    # テスト関数の実行後にここが呼ばれる (後処理)
    if os.path.exists(TEST_MEMORY_FILE):
        os.remove(TEST_MEMORY_FILE) # テスト用に作成したファイルを削除

def test_save_and_get_memory(memory_manager_instance):
    """記憶を保存し、取得できるかテスト"""
    # Arrange (準備) - memory_manager_instance は fixture から提供される
    test_content = "これはテスト用の記憶です"

    # Act (実行)
    memory_manager_instance.SaveMemory(test_content)
    all_memories = memory_manager_instance.GetAllMemories()

    # Assert (検証)
    assert len(all_memories) == 1 # 記憶が1件になっているはず
    assert all_memories[0].Content == test_content # 保存した内容と一致するはず
    assert all_memories[0].Id == 0 # 最初のIDは0のはず
    assert isinstance(all_memories[0].Embedding, list) # Embeddingがリスト形式であるはず
    assert len(all_memories[0].Embedding) > 0 # Embeddingが空でないはず

def test_save_multiple_memories(memory_manager_instance):
    """複数の記憶を保存し、IDが正しく付与されるかテスト"""
    # Arrange
    content1 = "記憶1"
    content2 = "記憶2"

    # Act
    memory_manager_instance.SaveMemory(content1)
    memory_manager_instance.SaveMemory(content2)
    all_memories = memory_manager_instance.GetAllMemories()

    # Assert
    assert len(all_memories) == 2
    assert all_memories[0].Content == content1
    assert all_memories[0].Id == 0
    assert all_memories[1].Content == content2
    assert all_memories[1].Id == 1 # IDがインクリメントされているか

def test_edit_memory_successful(memory_manager_instance):
    """既存の記憶を正常に編集できるかテスト"""
    # Arrange (準備)
    mm = memory_manager_instance # fixture から MemoryManager を取得
    original_content = "これは元の記憶です"
    new_content = "これは編集後の記憶です"
    mm.SaveMemory(original_content) # 編集対象の記憶をまず保存
    # 元のEmbeddingを（比較のため）取得しておく
    original_embedding = mm.GetAllMemories()[0].Embedding

    # Act (実行)
    mm.EditMemoryByIndex(0, new_content) # インデックス0の記憶を編集
    edited_memories = mm.GetAllMemories()

    # Assert (検証)
    assert len(edited_memories) == 1 # 記憶の総数は変わらないはず
    assert edited_memories[0].Id == 0 # IDも変わらないはず
    assert edited_memories[0].Content == new_content # 内容が新しいものに更新されているはず
    assert isinstance(edited_memories[0].Embedding, list) # Embeddingはリスト型のはず
    # Embeddingが再計算されていることを確認 (単純比較は難しいが、少なくとも違うオブジェクトにはなるはず)
    assert edited_memories[0].Embedding is not original_embedding
    # assert edited_memories[0].Embedding != original_embedding # 値自体が違うことも確認したい場合

def test_edit_memory_invalid_index(memory_manager_instance):
    """存在しないインデックスを指定して編集しようとしても、エラーにならず何も変化しないことを確認"""
    # Arrange
    mm = memory_manager_instance
    original_content = "唯一の記憶"

def test_delete_memory_successful(memory_manager_instance):
    """記憶を正常に削除できるかテスト"""
    # Arrange
    mm = memory_manager_instance
    content0 = "記憶0"
    content1 = "記憶1"
    content2 = "記憶2"
    mm.SaveMemory(content0)
    mm.SaveMemory(content1)
    mm.SaveMemory(content2)
    assert len(mm.GetAllMemories()) == 3

    # Act
    mm.DeleteMemoryByIndex(1) # 真ん中 (ID=1) を削除

    # Assert
    remaining_memories = mm.GetAllMemories()
    assert len(remaining_memories) == 2
    assert remaining_memories[0].Content == content0
    assert remaining_memories[0].Id == 0
    assert remaining_memories[1].Content == content2
    # Note: After deleting index 1, the memory previously at index 2 is now at index 1 in the list.
    # The IDs remain unchanged, but list indices shift.
    assert remaining_memories[1].Id == 2 # Check ID remains correct

def test_delete_memory_invalid_index(memory_manager_instance):
    """存在しないインデックスを削除しようとしてもエラーにならず、何も変化しないことを確認"""
    # Arrange
    mm = memory_manager_instance
    original_content = "唯一の記憶"
    mm.SaveMemory(original_content)
    memories_before_delete = mm.GetAllMemories().copy()

    # Act
    mm.DeleteMemoryByIndex(1) # 存在しないインデックス
    mm.DeleteMemoryByIndex(-1) # 負のインデックス
    memories_after_delete = mm.GetAllMemories()

    # Assert
    assert len(memories_after_delete) == 1
    assert memories_after_delete == memories_before_delete # 変化がないはず

def test_delete_only_memory(memory_manager_instance):
    """最後の記憶を削除すると空になることを確認"""
    # Arrange
    mm = memory_manager_instance
    mm.SaveMemory("最後の記憶")
    assert len(mm.GetAllMemories()) == 1

    # Act
    mm.DeleteMemoryByIndex(0)

    # Assert
    assert len(mm.GetAllMemories()) == 0

# --- Tests for SaveToFile and LoadFromFile ---

def test_save_and_load_cycle(memory_manager_instance):
    """ファイルに保存し、別のインスタンスで正しく読み込めるかテスト"""
    # Arrange
    mm_saver = memory_manager_instance # 保存用インスタンス (fixtureが提供)
    content1 = "記憶内容１"
    content2 = "記憶内容２"
    embedder = Embedder() # ローダー用にもEmbedderが必要

    mm_saver.SaveMemory(content1)
    mm_saver.SaveMemory(content2)
    saved_memories = mm_saver.GetAllMemories().copy() # 保存した内容をコピー

    # Act: 保存を実行
    mm_saver.SaveToFile()

    # 新しいインスタンスを作成し、同じファイルから読み込む
    mm_loader = MemoryManager(memory_path=TEST_MEMORY_FILE, embedder=embedder)
    # LoadFromFileは__init__で呼ばれるので、インスタンス作成だけで良いはず
    # mm_loader.LoadFromFile() # 明示的に呼ぶ必要はない (もし__init__で呼ばれないなら必要)
    loaded_memories = mm_loader.GetAllMemories()

    # Assert
    assert len(loaded_memories) == len(saved_memories)
    # 内容とIDが一致するか確認 (EmbeddingはJSON経由で誤差が出る可能性があるので比較しない)
    for i in range(len(saved_memories)):
        assert loaded_memories[i].Id == saved_memories[i].Id
        assert loaded_memories[i].Content == saved_memories[i].Content
        assert isinstance(loaded_memories[i].Embedding, list) # ロード後もEmbeddingがあるか
        assert len(loaded_memories[i].Embedding) > 0

def test_load_from_non_existent_file():
    """存在しないファイルからロードしようとしてもエラーにならず空のリストを返すテスト"""
    # Arrange
    non_existent_file = "non_existent_memory_file.json"
    # テスト前にファイルが存在しないことを確認 (念のため)
    if os.path.exists(non_existent_file):
        os.remove(non_existent_file)

    embedder = Embedder()
    mm = MemoryManager(memory_path=non_existent_file, embedder=embedder)

    # Act: LoadFromFileは__init__で呼ばれる

    # Assert
    assert len(mm.GetAllMemories()) == 0
    assert mm.NextId == 0 # NextIdもリセットされるか

    # Clean up (もしファイルが意図せず作られた場合に備えて)
    if os.path.exists(non_existent_file):
        os.remove(non_existent_file)


# Optional: Test for recalculating missing embeddings during load
# This requires manually creating a test file
def test_load_recalculates_embedding(tmp_path):
    """ロード時にEmbeddingがない場合、再計算されるかテスト"""
    # Arrange
    embedder = Embedder()
    test_file = tmp_path / "test_missing_embedding.json"
    # Embeddingがない、またはnullのデータを作成
    data_without_embedding = [
        {"Id": 0, "Content": "Embedding is missing", "Embedding": None},
        {"Id": 1, "Content": "No Embedding key"}
    ]
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(data_without_embedding, f)

    mm = MemoryManager(memory_path=str(test_file), embedder=embedder)

    # Act: LoadFromFileは__init__で呼ばれる
    loaded_memories = mm.GetAllMemories()

    # Assert
    assert len(loaded_memories) == 2
    assert loaded_memories[0].Content == "Embedding is missing"
    assert isinstance(loaded_memories[0].Embedding, list)
    assert len(loaded_memories[0].Embedding) > 0 # Embeddingが再計算されたはず
    assert loaded_memories[1].Content == "No Embedding key"
    assert isinstance(loaded_memories[1].Embedding, list)
    assert len(loaded_memories[1].Embedding) > 0 # Embeddingが再計算されたはず
    assert mm.NextId == 2 # NextIdも正しく設定されるか