from types import SimpleNamespace

import pytest

from app import net


@pytest.fixture(autouse=True)
def fake_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: object, **kwargs: object) -> SimpleNamespace:
        if isinstance(command, list):
            if not all(isinstance(arg, str) for arg in command):
                raise TypeError("subprocess argv entries must be strings")
            arguments = command
        elif isinstance(command, str):
            arguments = command.split()
        else:
            raise TypeError("unsupported command")
        count = arguments[arguments.index("-c") + 1]
        host = arguments[-1]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return SimpleNamespace(stdout=f"reply from {host}; count={count}\n")

    monkeypatch.setattr(net.subprocess, "run", fake_run)


def test_ping_default_count() -> None:
    assert net.ping_host("example.test") == "reply from example.test; count=2\n"


def test_ping_preserves_host_text() -> None:
    assert net.ping_host("host.internal") == "reply from host.internal; count=2\n"
