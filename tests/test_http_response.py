from ai_trading.http_response import write_response_body


class _Writer:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.payloads: list[bytes] = []

    def write(self, data: bytes) -> object:
        if self.failure is not None:
            raise self.failure
        self.payloads.append(data)
        return len(data)


def test_write_response_body_writes_successfully() -> None:
    writer = _Writer()

    assert write_response_body(writer, b"ok")
    assert writer.payloads == [b"ok"]


def test_write_response_body_ignores_broken_pipe() -> None:
    assert not write_response_body(_Writer(BrokenPipeError()), b"payload")


def test_write_response_body_ignores_connection_reset() -> None:
    assert not write_response_body(_Writer(ConnectionResetError()), b"payload")
