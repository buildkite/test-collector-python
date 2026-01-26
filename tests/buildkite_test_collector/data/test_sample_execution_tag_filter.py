# This is sample test file used for integration testing of execution_tag marker
import pytest


@pytest.mark.execution_tag("color", "red")
@pytest.mark.execution_tag("size", "medium")
def test_apple():
    assert True

@pytest.mark.execution_tag("color", "orange")
@pytest.mark.execution_tag("size", "medium")
def test_orange():
    assert True

@pytest.mark.execution_tag("color", "yellow")
@pytest.mark.execution_tag("size", "large")
def test_banana():
    assert True

@pytest.mark.execution_tag("color", "purple")
@pytest.mark.execution_tag("size", "small")
def test_grape():
    assert True

@pytest.mark.execution_tag("color", "red")
@pytest.mark.execution_tag("size", "small")
def test_strawberry():
    assert True

