#!/usr/bin/env python3
"""Check whether timetable source files have changed.

The tracked timetable-checks.json is the accepted baseline. Original downloads
and the latest check candidates live in the ignored .timetable-checker tree.
"""

from __future__ import annotations

import argparse
import atexit
import base64
import hashlib
import html.parser
import json
import os
import re
import socket
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import secrets
import struct
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "timetable-checks.json"
DEFAULT_CACHE = ROOT / ".timetable-checker"
USER_AGENT = "Saaristolautat timetable checker/1.0 (+https://saaristolautat.fi)"
_ALAND_FETCHER: "ChromeFetcher | None" = None
_ALAND_FETCH_ERROR: str | None = None


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in ("href", "data-timetable-url"):
            value = values.get(key)
            if value:
                if key == "data-timetable-url":
                    self.links.extend(part.strip() for part in value.split(",") if part.strip())
                else:
                    self.links.append(value)


class DevToolsSocket:
    """Small WebSocket client for the local Chrome DevTools endpoint."""

    def __init__(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=45)
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        request = (
            f"GET {target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            f"Origin: http://{parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = self._read_until(b"\r\n\r\n")
        if not response.startswith(b"HTTP/1.1 101"):
            status = response.split(b"\r\n", 1)[0].decode("ascii", errors="replace")
            raise RuntimeError(f"Chrome DevTools WebSocket -yhteys epäonnistui: {status}")
        self.next_id = 1

    def _read_until(self, marker: bytes) -> bytes:
        data = b""
        while marker not in data:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("Chrome sulki DevTools-yhteyden")
            data += chunk
        return data

    def _read_exact(self, length: int) -> bytes:
        data = b""
        while len(data) < length:
            chunk = self.socket.recv(length - len(data))
            if not chunk:
                raise RuntimeError("Chrome sulki DevTools-yhteyden")
            data += chunk
        return data

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        mask = secrets.token_bytes(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.socket.sendall(bytes(header) + mask + masked)

    def _receive_message(self) -> dict:
        fragments = bytearray()
        message_opcode = None
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            masked = bool(second & 0x80)
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(length)
            if mask:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 8:
                raise RuntimeError("Chrome sulki DevTools-yhteyden")
            if opcode == 9:
                self._send_frame(payload, opcode=10)
                continue
            if opcode in (1, 2):
                message_opcode = opcode
                fragments = bytearray(payload)
            elif opcode == 0:
                fragments.extend(payload)
            if final and message_opcode == 1:
                return json.loads(fragments.decode("utf-8"))

    def command(self, method: str, params: dict | None = None) -> dict:
        command_id = self.next_id
        self.next_id += 1
        self._send_frame(json.dumps({"id": command_id, "method": method,
                                     "params": params or {}}).encode("utf-8"))
        while True:
            message = self._receive_message()
            if message.get("id") != command_id:
                continue
            if message.get("error"):
                raise RuntimeError(f"Chrome DevTools: {message['error'].get('message')}")
            return message.get("result", {})

    def close(self) -> None:
        try:
            self._send_frame(b"", opcode=8)
        except OSError:
            pass
        self.socket.close()


class ChromeFetcher:
    """Fetch Ålandstrafiken through Chrome's validated browser session."""

    START_URL = "https://www.alandstrafiken.ax/turlistor"

    def __init__(self, profile: Path) -> None:
        self.profile = profile
        self.process: subprocess.Popen | None = None
        self.devtools: DevToolsSocket | None = None
        self.log_file = None
        chrome = find_chrome()
        if not chrome:
            raise RuntimeError("Google Chromea ei löytynyt Ålandstrafikenin tarkistusta varten")
        profile.mkdir(parents=True, exist_ok=True)
        clear_stale_chrome_lock(profile)
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        log_path = profile.parent / "chrome-startup.log"
        self.log_file = log_path.open("wb")
        self.process = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             "--no-default-browser-check", "--remote-allow-origins=*",
            f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL,
            stderr=self.log_file,
        )
        endpoint = f"http://127.0.0.1:{port}/json"
        targets = None
        for _ in range(100):
            if self.process.poll() is not None:
                self.log_file.flush()
                detail = log_path.read_text(encoding="utf-8", errors="replace").strip()
                if len(detail) > 600:
                    detail = detail[-600:]
                message = "Chrome ei käynnistynyt" + (f": {detail}" if detail else "")
                self.close()
                raise RuntimeError(message)
            try:
                with urllib.request.urlopen(endpoint, timeout=1) as response:
                    targets = json.load(response)
                if targets:
                    break
            except OSError:
                time.sleep(0.1)
        if not targets:
            self.close()
            raise RuntimeError("Chromen DevTools-rajapinta ei käynnistynyt")
        page = next((target for target in targets if target.get("type") == "page"), None)
        if not page:
            self.close()
            raise RuntimeError("Chrome ei luonut selaussivua")
        try:
            self.devtools = DevToolsSocket(page["webSocketDebuggerUrl"])
            self.devtools.command("Page.enable")
            self.devtools.command("Runtime.enable")
            self._validated = False
        except Exception:
            self.close()
            raise

    def evaluate(self, expression: str, await_promise: bool = False) -> object:
        assert self.devtools is not None
        result = self.devtools.command(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": await_promise,
             "returnByValue": True, "userGesture": True},
        )
        remote = result.get("result", {})
        if remote.get("subtype") == "error":
            raise RuntimeError(remote.get("description", "Chromen JavaScript-virhe"))
        return remote.get("value")

    def validate(self) -> None:
        if self._validated:
            return
        assert self.devtools is not None
        self.devtools.command("Page.navigate", {"url": self.START_URL})
        deadline = time.monotonic() + 60
        last_title = ""
        while time.monotonic() < deadline:
            time.sleep(0.5)
            state = self.evaluate(
                "({title:document.title, url:location.href, "
                "verify:!!document.querySelector('#verification-checkbox'), "
                "pdfs:document.querySelectorAll('a[href*=\".pdf\"]').length})"
            ) or {}
            last_title = state.get("title", "")
            if state.get("verify"):
                self.evaluate("document.querySelector('#verification-checkbox').click()")
            if ("Verifying" not in last_title and "Threat Protection" not in last_title
                    and state.get("pdfs", 0) > 0):
                self._validated = True
                return
        raise RuntimeError(
            f"Ålandstrafikenin selaintarkistus ei valmistunut (sivun otsikko: {last_title!r})"
        )

    def fetch(self, url: str) -> tuple[int, bytes, dict[str, str]]:
        self.validate()
        if urllib.parse.urldefrag(url)[0] == self.START_URL:
            html = str(self.evaluate("document.documentElement.outerHTML") or "")
            return 200, html.encode("utf-8"), {}
        expression = """
            (async () => {
              const response = await fetch(%s, {cache: 'no-store'});
              const bytes = new Uint8Array(await response.arrayBuffer());
              let binary = '';
              for (let i = 0; i < bytes.length; i += 32768) {
                binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
              }
              return {status: response.status, headers: Object.fromEntries(response.headers),
                      body: btoa(binary)};
            })()
        """ % json.dumps(url)
        result = self.evaluate(expression, await_promise=True)
        if not isinstance(result, dict):
            raise RuntimeError("Chrome ei palauttanut lataustulosta")
        return int(result["status"]), base64.b64decode(result["body"]), result.get("headers", {})

    def close(self) -> None:
        if self.devtools is not None:
            try:
                self.devtools.command("Browser.close")
            except (OSError, RuntimeError):
                pass
            self.devtools.close()
            self.devtools = None
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None
        clear_stale_chrome_lock(self.profile)


def find_chrome() -> str | None:
    configured = os.environ.get("TIMETABLE_CHROME")
    if configured and Path(configured).is_file():
        return configured
    executable = shutil.which("google-chrome") or shutil.which("chromium")
    if executable:
        return executable
    mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return str(mac) if mac.is_file() else None


def clear_stale_chrome_lock(profile: Path) -> None:
    lock = profile / "SingletonLock"
    if not lock.is_symlink():
        return
    match = re.search(r"-(\d+)$", os.readlink(lock))
    if not match:
        raise RuntimeError(f"Chromen profiililukkoa ei tunnistettu: {lock}")
    pid = int(match.group(1))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            path = profile / name
            if path.is_symlink():
                path.unlink()
    except PermissionError:
        raise RuntimeError(f"Ålandstrafikenin Chrome-profiili on toisen prosessin {pid} käytössä")
    else:
        raise RuntimeError(f"Ålandstrafikenin Chrome-profiili on jo prosessin {pid} käytössä")


def aland_fetcher() -> ChromeFetcher:
    global _ALAND_FETCHER, _ALAND_FETCH_ERROR
    if _ALAND_FETCH_ERROR:
        raise RuntimeError(_ALAND_FETCH_ERROR)
    if _ALAND_FETCHER is None:
        try:
            _ALAND_FETCHER = ChromeFetcher(DEFAULT_CACHE / "chrome-profile")
            atexit.register(_ALAND_FETCHER.close)
        except Exception as error:
            _ALAND_FETCH_ERROR = str(error)
            raise
    return _ALAND_FETCHER


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_html_hash(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    # Finferries embeds short-lived service bulletins before the actual
    # timetable. They are useful on the live page but must not make a removed
    # disruption notice look like a timetable change.
    text = re.sub(
        r"<script>\s*var\s+finferriesFerryBulletins\s*=.*?</script>",
        "",
        text,
        flags=re.S,
    )
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r">\s+<", "><", text)
    text = re.sub(r"\s+", " ", text).strip()
    return sha256(text.encode("utf-8"))


def fetch(url: str, etag: str | None = None) -> tuple[int, bytes | None, dict[str, str]]:
    if urllib.parse.urlparse(url).hostname == "www.alandstrafiken.ax":
        status, body, headers = aland_fetcher().fetch(url)
        if status < 200 or status >= 300:
            snippet = body[:300].decode("utf-8", errors="replace").replace("\n", " ")
            raise RuntimeError(f"HTTP {status}: {snippet}")
        return status, body, headers
    executable = shutil.which("curl")
    if not executable:
        raise RuntimeError("curl puuttuu")
    with tempfile.TemporaryDirectory(prefix="timetable-download-") as directory:
        body_path = Path(directory) / "body"
        header_path = Path(directory) / "headers"
        command = [executable, "-L", "--silent", "--show-error", "--max-time", "45",
                   "--user-agent", USER_AGENT, "--dump-header", str(header_path),
                   "--output", str(body_path), "--write-out", "%{http_code}"]
        if etag:
            command.extend(["--header", f"If-None-Match: {etag}"])
        command.append(url)
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode:
            message = process.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"curl epäonnistui: {message}")
        try:
            status = int(process.stdout.decode("ascii"))
        except ValueError as error:
            raise RuntimeError("curl ei palauttanut HTTP-tilaa") from error
        header_text = header_path.read_text(encoding="iso-8859-1") if header_path.exists() else ""
        blocks = [block for block in re.split(r"\r?\n\r?\n", header_text) if block.startswith("HTTP/")]
        headers: dict[str, str] = {}
        if blocks:
            for line in blocks[-1].splitlines()[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()
        body = body_path.read_bytes() if body_path.exists() else b""
        if status == 304:
            return status, None, headers
        if status < 200 or status >= 300:
            snippet = body[:300].decode("utf-8", errors="replace").replace("\n", " ")
            raise RuntimeError(f"HTTP {status}: {snippet}")
        return status, body, headers


def pdf_page_hashes(path: Path, dpi: int) -> list[str]:
    executable = find_pdftoppm()
    if not executable:
        raise RuntimeError(
            "pdftoppm puuttuu (asenna Poppler komennolla `brew install poppler` "
            "tai aseta TIMETABLE_PDFTOPPM)"
        )
    with tempfile.TemporaryDirectory(prefix="timetable-render-") as directory:
        prefix = Path(directory) / "page"
        process = subprocess.run(
            [executable, "-r", str(dpi), "-png", str(path), str(prefix)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode:
            message = process.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"PDF-renderöinti epäonnistui: {message}")
        pages = sorted(Path(directory).glob("page-*.png"))
        if not pages:
            raise RuntimeError("PDF:stä ei syntynyt yhtään sivua")
        return [sha256(page.read_bytes()) for page in pages]


def find_pdftoppm() -> str | None:
    configured = os.environ.get("TIMETABLE_PDFTOPPM")
    if configured and Path(configured).is_file():
        return configured
    executable = shutil.which("pdftoppm")
    if executable:
        return executable
    common_paths = [
        Path("/opt/homebrew/bin/pdftoppm"),
        Path("/usr/local/bin/pdftoppm"),
    ]
    common_paths.extend(
        Path.home().glob(".cache/codex-runtimes/*/dependencies/bin/override/pdftoppm")
    )
    return next((str(candidate) for candidate in common_paths if candidate.is_file()), None)


def fingerprint(path: Path, kind: str, dpi: int, headers: dict[str, str] | None = None) -> dict:
    data = path.read_bytes()
    result = {
        "sha256": sha256(data),
        "size": len(data),
    }
    if headers:
        lowered = {key.lower(): value for key, value in headers.items()}
        if lowered.get("etag"):
            result["etag"] = lowered["etag"]
        if lowered.get("last-modified"):
            result["lastModified"] = lowered["last-modified"]
    if kind == "pdf":
        result["pageImageSha256"] = pdf_page_hashes(path, dpi)
    else:
        result["normalizedSha256"] = normalized_html_hash(data)
    return result


def cache_path(cache: Path, source: dict, area: str = "originals") -> Path:
    suffix = ".pdf" if source["kind"] == "pdf" else ".html"
    return cache / area / source["provider"] / f"{source['id']}{suffix}"


def compare(old: dict, new: dict, kind: str) -> tuple[str, str]:
    if old.get("sha256") == new.get("sha256"):
        return "UNCHANGED", "sama SHA-256"
    if kind == "html" and old.get("normalizedSha256") == new.get("normalizedSha256"):
        return "METADATA", "vain HTML:n merkityksetön muotoilu muuttui"
    if kind == "pdf" and old.get("pageImageSha256") == new.get("pageImageSha256"):
        return "METADATA", "PDF muuttui, mutta kaikki sivut näyttävät samoilta"
    if kind == "pdf":
        before = old.get("pageImageSha256", [])
        after = new.get("pageImageSha256", [])
        pages = [str(index + 1) for index in range(max(len(before), len(after)))
                 if index >= len(before) or index >= len(after) or before[index] != after[index]]
        return "CHANGED", "muuttuneet sivut: " + ", ".join(pages)
    return "CHANGED", "sisältö muuttui"


def discover_catalog(catalog: dict) -> set[str]:
    def page_links(url: str) -> set[str]:
        status, body, _ = fetch(url)
        if status != 200 or body is None:
            raise RuntimeError(f"odottamaton HTTP-tila {status}: {url}")
        parser = LinkParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        return {urllib.parse.urldefrag(urllib.parse.urljoin(url, link))[0] for link in parser.links}

    links = page_links(catalog["url"])
    if catalog.get("crawlPattern"):
        crawl_pattern = re.compile(catalog["crawlPattern"], re.I)
        pages = sorted(link for link in links if crawl_pattern.search(link))
        if catalog.get("crawlNames"):
            names = set(catalog["crawlNames"])
            pages = [page for page in pages if Path(urllib.parse.urlparse(page).path).stem in names]
        links = set()
        failures: list[str] = []
        for page in pages:
            try:
                links.update(page_links(page))
            except Exception as error:
                failures.append(f"{page}: {error}")
        if failures:
            raise RuntimeError("reittisivujen haku epäonnistui: " + "; ".join(failures))
    pattern = re.compile(catalog["pattern"], re.I)
    return {link for link in links if pattern.search(link)}


def check_catalogs(manifest: dict) -> tuple[list[dict], bool]:
    reports: list[dict] = []
    changed = False
    source_urls = {source["url"] for source in manifest["sources"]}
    for catalog in manifest.get("catalogs", []):
        try:
            links = discover_catalog(catalog)
            known = {url for url in source_urls if url.startswith(catalog.get("sourcePrefix", ""))}
            known.update(catalog.get("acceptedUrls", []))
            new = sorted(links - known)
            missing = sorted(known - links) if catalog.get("complete", False) else []
            if new or missing:
                changed = True
                detail = []
                if new:
                    detail.append(f"uusia linkkejä {len(new)}")
                if missing:
                    detail.append(f"poistuneita linkkejä {len(missing)}")
                reports.append({"id": catalog["id"], "status": "CHANGED", "detail": ", ".join(detail),
                                "newUrls": new, "missingUrls": missing})
            else:
                reports.append({"id": catalog["id"], "status": "UNCHANGED", "detail": "linkkilista ennallaan"})
        except Exception as error:  # keep checking other sources
            reports.append({"id": catalog["id"], "status": "ERROR", "detail": str(error)})
    return reports, changed


def run_check(manifest: dict, cache: Path, write_candidates: bool) -> tuple[list[dict], bool, bool]:
    reports: list[dict] = []
    changed = False
    errors = False
    for source in manifest["sources"]:
        old = source.get("fingerprint", {})
        try:
            status, body, headers = fetch(source["url"], old.get("etag"))
            if status == 304:
                reports.append({"id": source["id"], "status": "UNCHANGED", "detail": "HTTP 304 / ETag"})
                continue
            if body is None:
                raise RuntimeError("palvelin ei palauttanut sisältöä")
            with tempfile.NamedTemporaryFile(suffix="." + source["kind"], delete=False) as temporary:
                temporary.write(body)
                path = Path(temporary.name)
            try:
                current = fingerprint(path, source["kind"], manifest["settings"]["pdfRenderDpi"], headers)
                state, detail = compare(old, current, source["kind"])
                report = {"id": source["id"], "status": state, "detail": detail,
                          "fingerprint": current}
                reports.append(report)
                if state in {"CHANGED", "METADATA"}:
                    changed = True
                if write_candidates:
                    # Keep every HTTP 200 response. Besides preserving changes,
                    # this lets accept record a newly received ETag even when
                    # the bytes themselves are unchanged.
                    destination = cache_path(cache, source, "candidates")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
            finally:
                path.unlink(missing_ok=True)
        except Exception as error:
            errors = True
            reports.append({"id": source["id"], "status": "ERROR", "detail": str(error)})
    catalog_reports, catalog_changed = check_catalogs(manifest)
    return reports + catalog_reports, changed or catalog_changed, errors or any(r["status"] == "ERROR" for r in catalog_reports)


def run_local_check(manifest: dict, cache: Path, directories: list[Path]) -> tuple[list[dict], bool]:
    by_name: dict[str, Path] = {}
    for directory in directories:
        for path in directory.glob("**/*"):
            if path.is_file():
                by_name[path.name] = path
    reports: list[dict] = []
    changed = False
    matched = 0
    for source in manifest["sources"]:
        path = by_name.get(source.get("seedFile", ""))
        if not path:
            continue
        matched += 1
        try:
            current = fingerprint(path, source["kind"], manifest["settings"]["pdfRenderDpi"])
            state, detail = compare(source.get("fingerprint", {}), current, source["kind"])
            reports.append({"id": source["id"], "status": state, "detail": detail,
                            "fingerprint": current})
            destination = cache_path(cache, source, "candidates")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            changed = changed or state in {"CHANGED", "METADATA"}
        except Exception as error:
            reports.append({"id": source["id"], "status": "ERROR", "detail": str(error)})
    if not matched:
        raise RuntimeError("Hakemistoista ei löytynyt yhtään sources-rivien seedFile-nimeä")
    return reports, changed


def seed(manifest: dict, cache: Path, directories: list[Path]) -> None:
    by_name: dict[str, Path] = {}
    for directory in directories:
        for path in directory.glob("**/*"):
            if path.is_file():
                by_name[path.name] = path
    missing: list[str] = []
    for source in manifest["sources"]:
        local_name = source.get("seedFile")
        path = by_name.get(local_name) if local_name else None
        if not path:
            missing.append(f"{source['id']} ({local_name})")
            continue
        destination = cache_path(cache, source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        source["fingerprint"] = fingerprint(
            destination, source["kind"], manifest["settings"]["pdfRenderDpi"]
        )
    if missing:
        raise RuntimeError("Paikallista lähdetiedostoa ei löytynyt:\n  " + "\n  ".join(missing))
    manifest["acceptedAt"] = datetime.now(timezone.utc).isoformat()


def accept(manifest: dict, cache: Path) -> None:
    candidates = cache / "candidates"
    report_path = cache / "last-report.json"
    report_fingerprints: dict[str, dict] = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report_fingerprints = {
            item["id"]: item["fingerprint"]
            for item in report.get("results", [])
            if item.get("fingerprint")
        }
    missing: list[str] = []
    for source in manifest["sources"]:
        candidate = cache_path(cache, source, "candidates")
        original = cache_path(cache, source)
        if candidate.exists():
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, original)
            source["fingerprint"] = report_fingerprints.get(source["id"]) or fingerprint(
                original, source["kind"], manifest["settings"]["pdfRenderDpi"]
            )
        elif not original.exists():
            missing.append(source["id"])
    if missing:
        raise RuntimeError("Ei hyväksyttävää tiedostoa lähteille: " + ", ".join(missing))
    manifest["acceptedAt"] = datetime.now(timezone.utc).isoformat()
    if candidates.exists():
        shutil.rmtree(candidates)


def print_report(reports: list[dict]) -> None:
    for report in reports:
        print(f"{report['status']:<9} {report['id']}: {report['detail']}")
        for url in report.get("newUrls", []):
            print(f"           + {url}")
        for url in report.get("missingUrls", []):
            print(f"           - {url}")


def clear_candidates(cache: Path) -> None:
    candidates = cache / "candidates"
    if candidates.exists():
        shutil.rmtree(candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="vertaa verkkoa hyväksyttyyn vertailutilaan")
    seed_parser = subparsers.add_parser("seed", help="alusta vertailutila paikallisista lähdetiedostoista")
    seed_parser.add_argument("directories", nargs="+", type=Path)
    local_parser = subparsers.add_parser(
        "check-local", help="vertaa selaimella ladattuja tiedostoja hyväksyttyyn vertailutilaan"
    )
    local_parser.add_argument("directories", nargs="+", type=Path)
    subparsers.add_parser("accept", help="hyväksy edellisen tarkistuksen muuttuneet tiedostot")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    try:
        if args.command == "seed":
            seed(manifest, args.cache, args.directories)
            args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Vertailutila alustettu: {args.manifest}")
            return 0
        if args.command == "accept":
            accept(manifest, args.cache)
            args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Muutokset hyväksytty vertailutilaan: {args.manifest}")
            return 0
        if args.command == "check-local":
            clear_candidates(args.cache)
            reports, changed = run_local_check(manifest, args.cache, args.directories)
            print_report(reports)
            report_path = args.cache / "last-report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps({"checkedAt": datetime.now(timezone.utc).isoformat(),
                                               "results": reports}, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
            print(f"\nRaportti: {report_path}")
            return 1 if any(item["status"] == "ERROR" for item in reports) else 2 if changed else 0
        clear_candidates(args.cache)
        reports, changed, errors = run_check(manifest, args.cache, write_candidates=True)
        print_report(reports)
        report_path = args.cache / "last-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps({"checkedAt": datetime.now(timezone.utc).isoformat(),
                                           "results": reports}, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"\nRaportti: {report_path}")
        return 1 if errors else 2 if changed else 0
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
