# This is sample test file used for integration testing of execution_tag marker
import pytest


@pytest.mark.execution_tag("language.version", "3.12")
@pytest.mark.execution_tag("team", "backend") 
def test_with_multiple_tags():
    assert True

@pytest.mark.execution_tag("team", "frontend")
def test_with_single_tag():
    assert True

def test_without_tags():
    assert True
