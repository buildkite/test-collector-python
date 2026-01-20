import json
import os
import pytest
from pathlib import Path

def test_add_tag_to_execution_data(tmp_path, fake_env):
    """Verify that tags added via the execution_tag marker are correctly captured in the test data."""
    import subprocess
    import sys
    
    test_file = Path(__file__).parent / "data" / "test_sample_execution_tag.py"
    json_output_file = tmp_path / "test_results.json"
    
    # Run pytest with our plugin on the test file
    cmd = [
        sys.executable, "-m", "pytest", 
        str(test_file),
        f"--json={json_output_file}",
    ]
    
    # Run pytest in a subprocess
    result = subprocess.run(cmd, capture_output=True)

    assert json_output_file.exists(), "JSON output file was not created"

    with open(json_output_file, 'r') as f:
        test_results = json.load(f)
    
    tests_by_name = {test["name"]: test for test in test_results}
    
    multi_tag_test = tests_by_name["test_with_multiple_tags"]
    assert "tags" in multi_tag_test
    assert multi_tag_test["tags"] == {
        "language.version": "3.12",
        "team": "backend"
    }
    
    single_tag_test = tests_by_name["test_with_single_tag"] 
    assert "tags" in single_tag_test
    assert single_tag_test["tags"] == {"team": "frontend"}
    
    no_tag_test = tests_by_name["test_without_tags"]
    assert "tags" not in no_tag_test or no_tag_test.get("tags") == {}
