from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cbbs_cad.specs import REPO_ROOT

DEFAULT_K1_HOST = "192.168.200.243"
DEFAULT_K1_PORTS = (80, 8080, 7125)
DEFAULT_K1_MONITOR_ROOT = REPO_ROOT / "3d-print-work" / "generated" / "monitoring" / "k1"
MAX_CAPTURE_BYTES = 512_000

MUTATING_PATH_FRAGMENTS = (
    "/printer/print",
    "/printer/pause",
    "/printer/cancel",
    "/printer/restart",
    "/printer/gcode",
    "/server/restart",
    "/machine/reboot",
    "/machine/shutdown",
    "/server/files/upload",
    "/api/job",
    "/api/printer/command",
    "/api/files",
)


@dataclass(frozen=True)
class ProbeTarget:
    name: str
    path: str
    expected: str


@dataclass(frozen=True)
class LimitedResponse:
    status_code: int
    headers: dict[str, str]
    payload: bytes
    json_data: dict[str, Any] | None = None


K1_PROBE_TARGETS = (
    ProbeTarget("http-root", "/", "http availability"),
    ProbeTarget("moonraker-webcams-list", "/server/webcams/list", "moonraker webcam list"),
    ProbeTarget("mjpeg-stream-root", "/?action=stream", "mjpeg stream"),
    ProbeTarget("mjpeg-snapshot-root", "/?action=snapshot", "mjpeg snapshot"),
    ProbeTarget("mjpeg-stream-webcam", "/webcam/?action=stream", "mjpeg stream"),
    ProbeTarget("mjpeg-snapshot-webcam", "/webcam/?action=snapshot", "mjpeg snapshot"),
    ProbeTarget("webcam-stream", "/webcam/stream", "webcam stream"),
    ProbeTarget("webcam-snapshot", "/webcam/snapshot", "webcam snapshot"),
    ProbeTarget("video", "/video", "video stream"),
    ProbeTarget("snapshot", "/snapshot", "snapshot"),
)


def new_monitor_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _assert_read_only(method: str, url: str) -> None:
    if method.upper() != "GET":
        raise ValueError(f"K1 monitoring v1 only permits GET requests, not {method}")
    parsed = urlparse(url)
    path = parsed.path.lower()
    for fragment in MUTATING_PATH_FRAGMENTS:
        if fragment in path:
            raise ValueError(f"refusing mutating K1 endpoint: {url}")


def _probe_urls(host: str, ports: tuple[int, ...]) -> list[dict[str, str | int]]:
    urls: list[dict[str, str | int]] = []
    for port in ports:
        base = f"http://{host}:{port}"
        for target in K1_PROBE_TARGETS:
            url = f"{base}{target.path}"
            _assert_read_only("GET", url)
            urls.append(
                {
                    "name": target.name,
                    "port": port,
                    "url": url,
                    "expected": target.expected,
                    "method": "GET",
                }
            )
    return urls


def _response_bytes(response: Any) -> bytes:
    content = getattr(response, "content", b"")
    if isinstance(content, str):
        content = content.encode("utf-8", errors="replace")
    if not isinstance(content, bytes):
        return b""
    return content[:MAX_CAPTURE_BYTES]


def _limited_get(client: Any, url: str, timeout_seconds: float) -> LimitedResponse:
    if hasattr(client, "stream"):
        with client.stream(
            "GET",
            url,
            timeout=timeout_seconds,
            follow_redirects=False,
        ) as response:
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                remaining = MAX_CAPTURE_BYTES - total
                if remaining <= 0:
                    break
                chunks.append(chunk[:remaining])
                total += min(len(chunk), remaining)
                if total >= MAX_CAPTURE_BYTES:
                    break
            payload = b"".join(chunks)
            headers = dict(response.headers)
            json_data = None
            if "json" in headers.get("content-type", "").lower():
                try:
                    decoded = json.loads(payload.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    decoded = None
                json_data = decoded if isinstance(decoded, dict) else None
            return LimitedResponse(
                status_code=int(response.status_code),
                headers=headers,
                payload=payload,
                json_data=json_data,
            )

    response = client.get(url, timeout=timeout_seconds, follow_redirects=False)
    payload = _response_bytes(response)
    headers = dict(getattr(response, "headers", {}))
    return LimitedResponse(
        status_code=int(response.status_code),
        headers=headers,
        payload=payload,
        json_data=_json_or_none(response),
    )


def _is_image_bytes(payload: bytes, content_type: str) -> bool:
    lowered = content_type.lower()
    return (
        "image/" in lowered
        or payload.startswith(b"\xff\xd8\xff")
        or payload.startswith(b"\x89PNG\r\n\x1a\n")
    )


def _snapshot_suffix(payload: bytes, content_type: str) -> str:
    lowered = content_type.lower()
    if "png" in lowered or payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    return ".jpg"


def _json_or_none(response: Any) -> dict[str, Any] | None:
    try:
        data = response.json()
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _http_client() -> Any:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(
            "K1 monitoring dependencies are optional. Run "
            "`uv sync --project tools/cad --group monitor` to install httpx/Pillow/OpenCV."
        ) from exc
    return httpx.Client()


def probe_k1_camera(
    *,
    host: str = DEFAULT_K1_HOST,
    ports: tuple[int, ...] = DEFAULT_K1_PORTS,
    output_root: Path = DEFAULT_K1_MONITOR_ROOT,
    run_id: str | None = None,
    timeout_seconds: float = 2.0,
    client: Any | None = None,
) -> dict[str, Any]:
    actual_run_id = run_id or new_monitor_run_id()
    output_dir = output_root / actual_run_id
    snapshot_dir = output_dir / "snapshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    close_client = False
    if client is None:
        client = _http_client()
        close_client = True

    results: list[dict[str, Any]] = []
    discovered_webcams: list[dict[str, Any]] = []
    try:
        for target in _probe_urls(host, ports):
            started = time.monotonic()
            record = {
                "name": target["name"],
                "url": target["url"],
                "port": target["port"],
                "method": "GET",
                "expected": target["expected"],
            }
            try:
                response = _limited_get(client, str(target["url"]), timeout_seconds)
                payload = response.payload
                content_type = response.headers.get("content-type", "")
                record.update(
                    {
                        "ok": 200 <= int(response.status_code) < 400,
                        "status_code": int(response.status_code),
                        "content_type": content_type,
                        "bytes_read": len(payload),
                        "elapsed_seconds": round(time.monotonic() - started, 4),
                    }
                )
                if target["name"] == "moonraker-webcams-list":
                    data = response.json_data
                    if data is not None:
                        webcam_path = output_dir / "moonraker-webcams-list.json"
                        _write_json(webcam_path, data)
                        webcams = data.get("result", {}).get("webcams", [])
                        if isinstance(webcams, list):
                            discovered_webcams.extend(
                                webcam for webcam in webcams if isinstance(webcam, dict)
                            )
                        record["json_path"] = str(webcam_path)
                if _is_image_bytes(payload, content_type):
                    suffix = _snapshot_suffix(payload, content_type)
                    snapshot_path = snapshot_dir / f"{target['port']}-{target['name']}{suffix}"
                    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                    snapshot_path.write_bytes(payload)
                    record["snapshot_path"] = str(snapshot_path)
            except Exception as exc:
                record.update(
                    {
                        "ok": False,
                        "error": type(exc).__name__,
                        "message": str(exc),
                        "elapsed_seconds": round(time.monotonic() - started, 4),
                    }
                )
            results.append(record)
    finally:
        if close_client:
            client.close()

    status = "reachable" if any(result.get("ok") for result in results) else "unreachable"
    manifest = {
        "schema": "cbbs-cad/k1-probe/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "truth_state": "internal review",
        "run_id": actual_run_id,
        "host": host,
        "ports": list(ports),
        "output_dir": str(output_dir),
        "status": status,
        "read_only": True,
        "mutating_endpoints_called": [],
        "probe_targets": results,
        "discovered_webcams": discovered_webcams,
    }
    _write_json(output_dir / "probe-manifest.json", manifest)
    return manifest


def _image_metrics(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return {"path": str(path), "status": "pillow-not-installed"}

    try:
        with Image.open(path) as image:
            gray = image.convert("L")
            stat = ImageStat.Stat(gray)
            return {
                "path": str(path),
                "status": "ok",
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "mean_luma": round(float(stat.mean[0]), 4),
                "luma_stddev": round(float(stat.stddev[0]), 4),
            }
    except Exception as exc:
        return {"path": str(path), "status": "error", "error": str(exc)}


def _opencv_stream_metrics(url: str, output_dir: Path, max_frames: int) -> dict[str, Any]:
    try:
        import cv2
    except ImportError:
        return {"url": url, "status": "opencv-not-installed"}

    _assert_read_only("GET", url)
    capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        return {"url": url, "status": "not-opened"}

    means: list[float] = []
    frame_path: Path | None = None
    try:
        for index in range(max_frames):
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            means.append(float(gray.mean()))
            if frame_path is None:
                frame_path = output_dir / "opencv-first-frame.png"
                cv2.imwrite(str(frame_path), frame)
    finally:
        capture.release()

    if not means:
        return {"url": url, "status": "no-frames"}
    return {
        "url": url,
        "status": "ok",
        "frame_count": len(means),
        "mean_luma": round(statistics.mean(means), 4),
        "first_frame_path": str(frame_path) if frame_path else None,
    }


def _is_stream_probe_result(result: dict[str, Any]) -> bool:
    if not result.get("ok") or "stream" not in str(result.get("expected", "")).lower():
        return False
    content_type = str(result.get("content_type", "")).lower()
    return (
        "multipart/x-mixed-replace" in content_type
        or "mjpeg" in content_type
        or "video/" in content_type
    )


def _stream_urls_from_probe(probe: dict[str, Any]) -> list[str]:
    stream_urls = [
        str(result["url"])
        for result in probe.get("probe_targets", [])
        if isinstance(result, dict) and _is_stream_probe_result(result)
    ]
    for webcam in probe.get("discovered_webcams", []):
        raw = webcam.get("stream_url") if isinstance(webcam, dict) else None
        if isinstance(raw, str) and raw:
            stream_urls.append(raw)
    return stream_urls


def monitor_k1_camera(
    *,
    host: str = DEFAULT_K1_HOST,
    ports: tuple[int, ...] = DEFAULT_K1_PORTS,
    output_root: Path = DEFAULT_K1_MONITOR_ROOT,
    run_id: str | None = None,
    timeout_seconds: float = 2.0,
    stream_frames: int = 3,
    client: Any | None = None,
) -> dict[str, Any]:
    probe = probe_k1_camera(
        host=host,
        ports=ports,
        output_root=output_root,
        run_id=run_id,
        timeout_seconds=timeout_seconds,
        client=client,
    )
    output_dir = Path(probe["output_dir"])
    snapshots = sorted((output_dir / "snapshots").glob("*"))
    snapshot_metrics = [_image_metrics(path) for path in snapshots if path.is_file()]

    stream_urls = _stream_urls_from_probe(probe)

    stream_metrics = []
    if stream_urls:
        stream_metrics.append(_opencv_stream_metrics(stream_urls[0], output_dir, stream_frames))

    session = {
        "schema": "cbbs-cad/k1-monitor-session/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "truth_state": "internal review",
        "run_id": probe["run_id"],
        "host": host,
        "output_dir": str(output_dir),
        "probe_manifest": str(output_dir / "probe-manifest.json"),
        "read_only": True,
        "automatic_failure_decision": "deferred until local camera access is verified",
        "snapshot_metrics": snapshot_metrics,
        "stream_metrics": stream_metrics,
    }
    _write_json(output_dir / "monitor-session.json", session)
    return session
