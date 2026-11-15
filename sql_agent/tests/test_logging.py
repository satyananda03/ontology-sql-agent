import logging

from sql_agent.core.logging import _not_status_poll


def _keeps(message: str) -> bool:
    return _not_status_poll(
        logging.LogRecord("x", logging.INFO, "", 0, message, None, None)
    )


def test_only_successful_status_polls_are_dropped():
    assert not _keeps('127.0.0.1:44794 - "GET /ingest/status HTTP/1.1" 200')
    assert not _keeps(
        '127.0.0.1:1 - "GET /api/semantic-compilation/status HTTP/1.1" 200'
    )
    assert not _keeps(
        'HTTP Request: GET http://localhost:3002/ingest/status "HTTP/1.1 200 OK"'
    )
    assert _keeps('127.0.0.1:44794 - "GET /ingest/status HTTP/1.1" 500')
    assert _keeps('127.0.0.1:44794 - "GET /api/settings HTTP/1.1" 200')
    assert _keeps('HTTP Request: POST http://llm/v1/chat/completions "HTTP/1.1 200 OK"')
