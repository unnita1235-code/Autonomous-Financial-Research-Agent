"""Quick unit test for JSON parsing + validation helpers."""
from agents.react_loop import _parse_llm_json, _validate_action

# Test 1: whitespace
assert _parse_llm_json('  {"a":1}  ') == {"a": 1}
print("PASS: whitespace stripping")

# Test 2: markdown fences
fenced = '```json\n{"b":2}\n```'
assert _parse_llm_json(fenced) == {"b": 2}
print("PASS: markdown fence stripping")

# Test 3: invalid JSON
assert _parse_llm_json("{invalid}") is None
print("PASS: invalid JSON returns None")

# Test 4: valid tool action
valid_tool = {"thought":"t", "action":"tool", "tool_name":"sec", "tool_args":{"ticker":"AAPL"}, "confidence":0.9}
assert _validate_action(valid_tool) is True
print("PASS: valid tool action")

# Test 5: valid done action
valid_done = {"thought":"t", "action":"done", "tool_name":None, "tool_args":None, "confidence":0.9}
assert _validate_action(valid_done) is True
print("PASS: valid done action")

# Test 6: missing keys
assert _validate_action({"thought":"t"}) is False
print("PASS: missing keys rejected")

# Test 7: bad action value
assert _validate_action({"thought":"t", "action":"foo", "confidence":0.5}) is False
print("PASS: bad action value rejected")

# Test 8: tool action without tool_name
assert _validate_action({"thought":"t", "action":"tool", "tool_name":None, "tool_args":{}, "confidence":0.5}) is False
print("PASS: tool action without tool_name rejected")

print("\nAll parse/validate tests passed!")
