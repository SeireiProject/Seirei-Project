# tests/memory/test_log_manager.py
import pytest
import os
import json
from datetime import datetime
from pathlib import Path
import time # For debug prints

# Modules to test
from my_local_ai.memory.log_manager import LogManager, LogEntry
# Dependencies needed
from my_local_ai.memory.embedder import Embedder

# Use pytest's tmp_path fixture for cleaner temporary file handling
@pytest.fixture
def log_manager_fixture(tmp_path):
    """Fixture to create a LogManager instance with a temporary log file."""
    test_log_file = tmp_path / "test_logs.jsonl" # Use .jsonl extension
    print(f"\n[{time.time():.3f}] Fixture setup: Creating LogManager instance using {test_log_file}")
    embedder = Embedder() # Create embedder instance
    log_manager = LogManager(log_path=str(test_log_file), embedder=embedder)
    # Yield both manager and path for potential direct file inspection in tests
    yield log_manager, test_log_file
    print(f"\n[{time.time():.3f}] Fixture teardown: LogManager instance goes out of scope, tmp_path cleans up file.")
    # tmp_path automatically handles cleanup

# --- Test Cases ---

def test_log_manager_init_empty(tmp_path):
    """Test LogManager initializes empty if file doesn't exist."""
    non_existent_file = tmp_path / "non_existent.jsonl"
    embedder = Embedder()
    lm = LogManager(log_path=str(non_existent_file), embedder=embedder)
    assert lm.GetAllLogs() == []

def test_save_log_single(log_manager_fixture):
    """Test saving a single log entry."""
    log_manager, test_log_file = log_manager_fixture
    user_input = "Hello AI"
    assistant_response = "Hello User"
    username = "TestUser"

    # Act
    log_manager.SaveLog(user_input, assistant_response, username)
    logs = log_manager.GetAllLogs()

    # Assert Log List
    assert len(logs) == 1
    saved_log = logs[0]
    assert isinstance(saved_log, LogEntry)
    assert saved_log.UserInput == user_input
    assert saved_log.AssistantResponse == assistant_response
    assert saved_log.Username == username
    # Check timestamp format (basic check)
    assert isinstance(saved_log.Timestamp, str)
    try:
        datetime.strptime(saved_log.Timestamp, "%Y-%m-%d %H:%M:%S")
        timestamp_valid = True
    except ValueError:
        timestamp_valid = False
    assert timestamp_valid
    # Check embedding
    assert isinstance(saved_log.Embedding, list)
    assert len(saved_log.Embedding) > 0

    # Assert File Content
    assert test_log_file.exists()
    with open(test_log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["UserInput"] == user_input
    assert log_data["AssistantResponse"] == assistant_response
    assert log_data["Username"] == username
    assert "Embedding" in log_data
    assert isinstance(log_data["Embedding"], list)

def test_save_log_multiple(log_manager_fixture):
    """Test saving multiple log entries."""
    log_manager, test_log_file = log_manager_fixture
    inputs = ["Input 1", "Input 2", "Input 3"]
    outputs = ["Response 1", "Response 2", "Response 3"]

    # Act
    log_manager.SaveLog(inputs[0], outputs[0], "UserA")
    log_manager.SaveLog(inputs[1], outputs[1], "UserB")
    log_manager.SaveLog(inputs[2], outputs[2], "UserA")
    logs = log_manager.GetAllLogs()

    # Assert Log List
    assert len(logs) == 3
    assert logs[0].UserInput == inputs[0]
    assert logs[1].UserInput == inputs[1]
    assert logs[2].UserInput == inputs[2]

    # Assert File Content
    assert test_log_file.exists()
    with open(test_log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 3
    # Basic check on last line content
    log_data = json.loads(lines[2])
    assert log_data["UserInput"] == inputs[2]


def test_load_logs_cycle(log_manager_fixture):
    """Test saving logs and reloading them in a new instance."""
    log_manager_saver, test_log_file = log_manager_fixture
    inputs = ["Apple", "Banana"]
    outputs = ["Fruit 1", "Fruit 2"]
    usernames = ["Alice", "Bob"]

    # Act (Save)
    log_manager_saver.SaveLog(inputs[0], outputs[0], usernames[0])
    log_manager_saver.SaveLog(inputs[1], outputs[1], usernames[1])

    # Act (Load in new instance)
    embedder = Embedder() # Need a new embedder for the loader
    log_manager_loader = LogManager(log_path=str(test_log_file), embedder=embedder)
    loaded_logs = log_manager_loader.GetAllLogs()

    # Assert
    assert len(loaded_logs) == 2
    assert loaded_logs[0].UserInput == inputs[0]
    assert loaded_logs[0].AssistantResponse == outputs[0]
    assert loaded_logs[0].Username == usernames[0]
    assert isinstance(loaded_logs[0].Embedding, list) # Check embedding loaded/created
    assert len(loaded_logs[0].Embedding) > 0
    assert loaded_logs[1].UserInput == inputs[1]
    assert loaded_logs[1].AssistantResponse == outputs[1]
    assert loaded_logs[1].Username == usernames[1]
    assert isinstance(loaded_logs[1].Embedding, list)
    assert len(loaded_logs[1].Embedding) > 0


def test_load_recalculates_missing_embedding(tmp_path):
    """Test that LoadLogs recalculates missing embeddings."""
    # Arrange
    embedder = Embedder()
    test_log_file = tmp_path / "test_missing_embedding.jsonl"
    log_data_no_embedding = [
        {"Timestamp": "2025-04-18 10:00:00", "UserInput": "Input without embedding", "AssistantResponse": "Resp1", "Username": "UserX", "Embedding": None},
        {"Timestamp": "2025-04-18 10:01:00", "UserInput": "Input missing embedding key", "AssistantResponse": "Resp2", "Username": "UserY"}
    ]
    with open(test_log_file, "w", encoding="utf-8") as f:
        for entry in log_data_no_embedding:
            f.write(json.dumps(entry) + "\n")

    # Act
    log_manager = LogManager(log_path=str(test_log_file), embedder=embedder)
    loaded_logs = log_manager.GetAllLogs()

    # Assert
    assert len(loaded_logs) == 2
    assert loaded_logs[0].UserInput == "Input without embedding"
    assert isinstance(loaded_logs[0].Embedding, list)
    assert len(loaded_logs[0].Embedding) > 0 # Should be recalculated

    assert loaded_logs[1].UserInput == "Input missing embedding key"
    assert isinstance(loaded_logs[1].Embedding, list)
    assert len(loaded_logs[1].Embedding) > 0 # Should be recalculated


def test_search_relevant_logs(log_manager_fixture):
    """Test searching for relevant logs."""
    log_manager, _ = log_manager_fixture
    # Arrange: Save distinct logs
    log_manager.SaveLog("I like apples.", "Red fruits are nice.", "FruitFan")
    log_manager.SaveLog("The weather today is sunny.", "A great day!", "WeatherWatcher")
    log_manager.SaveLog("How to learn Python?", "Try the official tutorial.", "DevHelper")
    log_manager.SaveLog("Red apples are my favorite.", "Sweet!", "FruitFan")
    # Wait a bit for file system to catch up if needed? Unlikely needed here.
    # time.sleep(0.1)

    # Act: Search for something related to apples
    # Ensure embedder model is loaded before search if lazy loading
    if log_manager.Embedder.model is None:
         log_manager.Embedder.Embed("preload query") # Trigger load

    query = "What kind of fruit?"
    relevant_logs = log_manager.SearchRelevantLogs(query, topK=2)

    # Assert
    assert len(relevant_logs) == 2 # Should get top 2
    # Check contents of the top results (order might vary slightly based on embedding)
    contents = {log.UserInput for log in relevant_logs}
    assert "I like apples." in contents
    assert "Red apples are my favorite." in contents
    assert "The weather today is sunny." not in contents # Should not contain weather log

def test_search_relevant_logs_no_match(log_manager_fixture):
    """Test searching when no relevant logs exist."""
    log_manager, _ = log_manager_fixture
    # Arrange: Save unrelated logs
    log_manager.SaveLog("The weather today is sunny.", "A great day!", "WeatherWatcher")
    log_manager.SaveLog("How to learn Python?", "Try the official tutorial.", "DevHelper")
    # Ensure embedder model is loaded
    if log_manager.Embedder.model is None:
         log_manager.Embedder.Embed("preload query")

    # Act: Search for something completely different
    query = "Tell me about quantum physics"
    relevant_logs = log_manager.SearchRelevantLogs(query, topK=3)

    # Assert
    # Depending on the embedder, might still return *something* based on weak similarity,
    # but ideally, for very different queries, it might return fewer than topK or empty.
    # For this test, let's just assert it doesn't return the saved logs.
    contents = {log.UserInput for log in relevant_logs}
    assert "The weather today is sunny." not in contents
    assert "How to learn Python?" not in contents
    # Or assert empty if that's expected
    # assert len(relevant_logs) == 0

def test_search_relevant_logs_empty_log(log_manager_fixture):
    """Test searching when log manager has no logs."""
    log_manager, _ = log_manager_fixture
    # Arrange: No logs saved
    # Ensure embedder model is loaded
    if log_manager.Embedder.model is None:
         log_manager.Embedder.Embed("preload query")

    # Act
    query = "Anything?"
    relevant_logs = log_manager.SearchRelevantLogs(query, topK=3)

    # Assert
    assert len(relevant_logs) == 0 # Should be empty