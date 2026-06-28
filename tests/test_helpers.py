from agents.react_loop import _parse_llm_json, _validate_action

def test_parse_valid():
    assert _parse_llm_json('{"a": 1}') == {"a": 1}

def test_parse_fenced():
    assert _parse_llm_json('```json\n{"b": 2}\n```') == {"b": 2}

def test_parse_invalid():
    assert _parse_llm_json("{bad json}") is None

def test_parse_empty():
    assert _parse_llm_json("") is None

def test_validate_tool():
    d = {"thought": "t", "action": "tool", "tool_name": "sec", "tool_args": {"ticker": "AAPL"}, "confidence": 0.9}
    assert _validate_action(d) is True

def test_validate_done():
    d = {"thought": "t", "action": "done", "tool_name": None, "tool_args": None, "confidence": 0.9}
    assert _validate_action(d) is True

def test_validate_missing_keys():
    assert _validate_action({"thought": "t"}) is False

def test_validate_bad_action():
    assert _validate_action({"thought": "t", "action": "fly", "confidence": 0.5}) is False
