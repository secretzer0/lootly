"""Pytest configuration for eBay MCP API tests."""
import os
import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--test-mode",
        action="store",
        default="unit",
        choices=["unit", "integration"],
        help="Test mode: unit (mocked) or integration (real API calls)"
    )


@pytest.fixture(scope="session", autouse=True)
def set_test_mode(request):
    """Set TEST_MODE environment variable based on command line option."""
    test_mode = request.config.getoption("--test-mode")
    os.environ["TEST_MODE"] = test_mode
    return test_mode