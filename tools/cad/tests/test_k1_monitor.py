from __future__ import annotations

from urllib.parse import urlparse

import pytest

from cbbs_cad.k1_monitor import (
    MUTATING_PATH_FRAGMENTS,
    _assert_read_only,
    _stream_urls_from_probe,
    probe_k1_camera,
)


class FailingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, url: str, **_kwargs):
        self.calls.append(("GET", url))
        raise TimeoutError("unreachable")


def test_k1_probe_uses_only_read_only_get_endpoints(tmp_path) -> None:
    client = FailingClient()

    manifest = probe_k1_camera(
        host="192.0.2.10",
        ports=(80,),
        output_root=tmp_path,
        run_id="probe-test",
        timeout_seconds=0.01,
        client=client,
    )

    assert manifest["status"] == "unreachable"
    assert manifest["mutating_endpoints_called"] == []
    assert (tmp_path / "probe-test" / "probe-manifest.json").is_file()
    assert client.calls
    for method, url in client.calls:
        assert method == "GET"
        path = urlparse(url).path.lower()
        assert not any(fragment in path for fragment in MUTATING_PATH_FRAGMENTS)


def test_k1_read_only_guard_rejects_mutating_methods_and_paths() -> None:
    with pytest.raises(ValueError, match="only permits GET"):
        _assert_read_only("POST", "http://192.0.2.10/server/webcams/list")

    with pytest.raises(ValueError, match="refusing mutating"):
        _assert_read_only("GET", "http://192.0.2.10/printer/gcode/script")


def test_k1_monitor_prefers_actual_mjpeg_stream_over_html_probe() -> None:
    probe = {
        "probe_targets": [
            {
                "ok": True,
                "expected": "mjpeg stream",
                "url": "http://192.0.2.10:80/?action=stream",
                "content_type": "text/html; charset=utf-8",
            },
            {
                "ok": True,
                "expected": "mjpeg stream",
                "url": "http://192.0.2.10:8080/?action=stream",
                "content_type": "multipart/x-mixed-replace;boundary=boundarydonotcross",
            },
        ],
        "discovered_webcams": [],
    }

    assert _stream_urls_from_probe(probe) == ["http://192.0.2.10:8080/?action=stream"]
