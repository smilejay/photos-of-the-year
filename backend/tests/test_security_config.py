import pytest

from app import _env_bool, _validated_secret_key


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "change-me",
        "change-me-to-a-random-secret",
        "your-secret-key-change-in-production",
        "too-short",
    ],
)
def test_secret_key拒绝缺失占位和短密钥(value):
    with pytest.raises(RuntimeError):
        _validated_secret_key(value)


def test_secret_key接受至少32字节的随机值():
    value = "a" * 32
    assert _validated_secret_key(value) == value


def test_布尔环境变量拒绝非法值(monkeypatch):
    monkeypatch.setenv("TEST_BOOL_SETTING", "invalid")
    with pytest.raises(RuntimeError):
        _env_bool("TEST_BOOL_SETTING", True)
