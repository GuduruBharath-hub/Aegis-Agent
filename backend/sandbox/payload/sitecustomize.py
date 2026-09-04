from __future__ import annotations

import socket
from typing import NoReturn


def _blocked(*args: object, **kwargs: object) -> NoReturn:
    raise OSError("AEGIS: network disabled in sandbox")


class _BlockedSocket(socket.socket):
    def __init__(self, *args: object, **kwargs: object) -> None:
        _blocked()


socket.socket = _BlockedSocket
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
