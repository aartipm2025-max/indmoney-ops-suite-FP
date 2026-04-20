import os


def pytest_configure(config: object) -> None:
    """Inject a fake GROQ_API_KEY before any module is collected, so config.py
    doesn't raise ConfigError during the test run."""
    os.environ.setdefault("GROQ_API_KEY", "gsk_test_fake_key_for_testing")
