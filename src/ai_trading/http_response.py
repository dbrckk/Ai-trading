from __future__ import annotations

from typing import Protocol


class ResponseWriter(Protocol):
    def write(self, data: bytes) -> object: ...


def write_response_body(writer: ResponseWriter, body: bytes) -> bool:
    """Write an HTTP response body, treating client disconnects as benign."""
    try:
        writer.write(body)
    except (BrokenPipeError, ConnectionResetError):
        return False
    return True
