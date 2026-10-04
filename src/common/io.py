"""Download-with-cache, interim parquet writing, and source/status registries."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests
import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
MANUAL = DATA / "manual"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
SOURCES_YAML = DATA / "sources.yaml"
STATUS_JSON = DATA / "status.json"
STATUS_MD = DATA / "SOURCES_STATUS.md"

for _d in (RAW, INTERIM, MANUAL, PROCESSED, REPORTS / "maps"):
    _d.mkdir(parents=True, exist_ok=True)

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# BLS rejects browser-like and library UAs; it accepts "<purpose> <email>".
CONTACT_UA = f"datacenter-siting research {os.environ.get('CONTACT_EMAIL', 'datacenter.siting@example.com')}"


class DownloadError(RuntimeError):
    pass


def today() -> str:
    return dt.date.today().isoformat()


def download(
    url: str,
    dest: str | Path,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    user_agent: str = BROWSER_UA,
    min_bytes: int = 200,
    allow_html: bool = False,
    timeout: int = 300,
    retries: int = 3,
    force: bool = False,
) -> Path:
    """Download `url` to data/raw/<dest> unless it already exists.

    The response is checked before it is accepted: HTTP 200, at least
    `min_bytes`, and (unless `allow_html`) not an HTML error/landing page.
    """
    path = RAW / dest
    if path.exists() and path.stat().st_size > 0 and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    hdrs = {"User-Agent": user_agent, **(headers or {})}
    print(f"[download] {url}" + (f" params={params}" if params else ""))
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with requests.get(url, params=params, headers=hdrs, stream=True, timeout=timeout) as r:
                if r.status_code != 200:
                    raise DownloadError(f"HTTP {r.status_code} for {r.url}")
                tmp = path.with_suffix(path.suffix + ".part")
                total = int(r.headers.get("content-length") or 0)
                with open(tmp, "wb") as f, tqdm(
                    total=total or None, unit="B", unit_scale=True, desc=path.name, leave=False,
                    disable=total < 5_000_000,
                ) as bar:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        bar.update(len(chunk))
            size = tmp.stat().st_size
            if size < min_bytes:
                tmp.unlink()
                raise DownloadError(f"Response too small ({size} bytes) for {url}")
            if not allow_html:
                head = tmp.open("rb").read(512).lstrip().lower()
                if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
                    tmp.unlink()
                    raise DownloadError(f"Got an HTML page instead of data for {url}")
            tmp.rename(path)
            print(f"[download] ok -> {path.relative_to(ROOT)} ({size/1e6:.1f} MB)")
            return path
        except DownloadError:
            raise
        except Exception as e:  # network errors: retry
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise DownloadError(f"Failed after {retries} attempts: {url}: {last_err}")


def unzip(path: Path, subdir: str | None = None) -> Path:
    """Extract a zip next to itself (once) and return the extraction folder."""
    out = path.parent / (subdir or path.stem)
    marker = out / ".extracted"
    if marker.exists():
        return out
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        z.extractall(out)
    marker.touch()
    return out


def check_fips_frame(df: pd.DataFrame) -> None:
    if "fips" not in df.columns:
        raise ValueError("interim frame has no 'fips' column")
    f = df["fips"]
    if not (f.map(type) == str).all():
        raise TypeError("fips must be str")
    bad = f[f.str.len() != 5]
    if len(bad):
        raise ValueError(f"non 5-char fips: {bad.head().tolist()}")
    if f.duplicated().any():
        raise ValueError(f"duplicate fips: {f[f.duplicated()].head().tolist()}")


def write_interim(df: pd.DataFrame, name: str) -> Path:
    """Write one interim parquet keyed by fips (string, 5 chars, unique)."""
    df = df.copy()
    check_fips_frame(df)
    base_path = INTERIM / "_base_counties.parquet"
    if base_path.exists():
        base = set(pd.read_parquet(base_path, columns=["fips"])["fips"])
        extra = sorted(set(df["fips"]) - base)
        if extra:
            print(f"[interim] WARNING {name}: dropping {len(extra)} fips not in base layer: {extra[:15]}")
            df = df[df["fips"].isin(base)]
        missing = len(base - set(df["fips"]))
        if missing:
            print(f"[interim] {name}: {missing} base counties have no row (left as NaN in the merge)")
    df = df.sort_values("fips").reset_index(drop=True)
    path = INTERIM / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"[interim] {path.relative_to(ROOT)}: {len(df)} rows, cols={list(df.columns)}")
    return path


# --------------------------------------------------------------------------- registries

def register_source(key: str, raw_files: list[Path] | None = None, **meta) -> None:
    """Record source/version/download date/license in data/sources.yaml.

    download_date is the modification date of the oldest cached raw file, so
    re-running a script on cached data does not move the date.
    """
    data = {}
    if SOURCES_YAML.exists():
        data = yaml.safe_load(SOURCES_YAML.read_text()) or {}
    entry = data.get(key, {})
    entry.update({k: v for k, v in meta.items() if v is not None})
    files = [Path(p) for p in (raw_files or []) if Path(p).exists()]
    if files:
        oldest = min(p.stat().st_mtime for p in files)
        entry["download_date"] = dt.date.fromtimestamp(oldest).isoformat()
        entry["raw_files"] = [str(p.relative_to(ROOT)) for p in files][:20]
    entry.setdefault("download_date", today())
    data[key] = entry
    SOURCES_YAML.write_text(
        "# Auto-maintained by src/common/io.register_source. One entry per dataset.\n"
        + yaml.safe_dump(dict(sorted(data.items())), sort_keys=False, allow_unicode=True, width=110)
    )


def set_status(key: str, status: str, message: str, features: list[str] | None = None) -> None:
    """Status is one of OK, PARTIAL, BLOCKED, FAILED, SKIPPED."""
    data = json.loads(STATUS_JSON.read_text()) if STATUS_JSON.exists() else {}
    data[key] = {
        "status": status,
        "message": message,
        "features": features or [],
        "updated": dt.datetime.now().isoformat(timespec="seconds"),
    }
    STATUS_JSON.write_text(json.dumps(dict(sorted(data.items())), indent=2))
    render_status_md()
    print(f"[status] {key}: {status} - {message}")


def render_status_md() -> None:
    data = json.loads(STATUS_JSON.read_text()) if STATUS_JSON.exists() else {}
    order = {"FAILED": 0, "BLOCKED": 1, "PARTIAL": 2, "SKIPPED": 3, "OK": 4}
    lines = [
        "# Source status",
        "",
        "Auto-generated by `src/common/io.set_status`. Features of any source that is not OK are left as NaN",
        "(never estimated). Re-run the ingest script after fixing the cause.",
        "",
        "| Source | Status | Features | Notes | Updated |",
        "|---|---|---|---|---|",
    ]
    for k, v in sorted(data.items(), key=lambda kv: (order.get(kv[1]["status"], 9), kv[0])):
        msg = v["message"].replace("|", "\\|").replace("\n", " ")
        feats = ", ".join(f"`{f}`" for f in v.get("features", []))
        lines.append(f"| `{k}` | **{v['status']}** | {feats} | {msg} | {v['updated']} |")
    STATUS_MD.write_text("\n".join(lines) + "\n")


def env_key(name: str) -> str | None:
    """Read a key from the environment, else a KEY=value line in the repo .env or its parent .env."""
    v = os.environ.get(name, "").strip()
    for env_file in (ROOT / ".env", ROOT.parent / ".env"):
        if v or not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            k, _, val = line.partition("=")
            if k.strip() == name:
                v = val.strip().strip("'\"")
    return v or None


def copy_to_raw(src: Path, dest: str) -> Path:
    path = RAW / dest
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        shutil.copy(src, path)
    return path
