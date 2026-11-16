"""
Photo library behind the photo tile (day mode).

The browser never loads original photos. A 12-48 MP original is 3-15 MB, and
decoding one takes the Pi's browser long enough to stutter a crossfade. So
every photo is rendered once, in the background, into a display-sized JPEG
and a tiny blurred backdrop. The tile only loads those: a few hundred KB from
the Pi's own disk, decoded in a few milliseconds.

Sources (either or both):
  - PHOTOS_DIR: a folder on the Pi. Subfolder names become album captions.
  - PHOTOS_DRIVE_FOLDER_ID: a Google Drive folder shared with the service
    account the calendar already uses. Originals are streamed into memory,
    rendered and dropped, so the Pi only stores the small copies.

Cache (PHOTOS_CACHE_DIR):
  <id>.jpg        display copy, long edge <= PHOTOS_MAX_EDGE, sRGB/ICC kept, EXIF stripped
  <id>.blur.jpg   ~40 px blurred copy, stretched behind photos that don't fill the tile
  manifest.json   id -> album, date taken, size (so a restart doesn't re-render)

A photo's id hashes its source key, its version (mtime + size, or the Drive
md5) and the render settings. An edited photo or a changed PHOTOS_MAX_EDGE
gets a new id and is rendered again. Cache files of photos that left their
source are deleted after each scan. A source that fails to scan (Drive
offline, folder not mounted) keeps its photos instead of losing them.

Photos are handed out as a shuffle: every photo once before any repeats.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import BinaryIO, Callable, Dict, List, Optional, Set, Tuple

from PIL import ExifTags, Image, ImageFilter, ImageOps

from src.logger import logger
from src.models.internal import Photo

try:  # iPhone photos are HEIC; pillow-heif teaches Pillow to open them
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:  # pragma: no cover - optional dependency
    HEIF_SUPPORTED = False

# Bump to re-render every photo after changing how they are rendered
RENDER_VERSION = 1

SOURCE_LOCAL = "local"
SOURCE_DRIVE = "drive"

JPEG_QUALITY = 85
BACKDROP_EDGE = 40        # px; the browser stretches it, which blurs it further for free
BACKDROP_BLUR = 1.5       # Gaussian radius at 40 px
BACKDROP_QUALITY = 70
MANIFEST_NAME = "manifest.json"
MANIFEST_SAVE_EVERY = 25  # photos, during a long first run

LOCAL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
DRIVE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff", "image/bmp"}
if HEIF_SUPPORTED:
    LOCAL_EXTENSIONS |= {".heic", ".heif"}
    DRIVE_MIME_TYPES |= {"image/heic", "image/heif"}

_ID_LEN = 20
_FILE_RE = re.compile(rf"([0-9a-f]{{{_ID_LEN}}})(\.blur)?\.jpg")
_EXIF_DATE_RE = re.compile(r"\s*(\d{4})[:\-](\d{2})[:\-](\d{2})")
# Dates in camera/phone file names: IMG_20230614_121314, PXL_20230614..., 2023-06-14 12.13.14, IMG-20230614-WA0001
_NAME_DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")


@dataclass
class SourcePhoto:
    """An original photo as found in a source, not rendered yet."""
    source: str                        # SOURCE_LOCAL | SOURCE_DRIVE
    key: str                           # identity within the source: relative path / Drive file id
    version: str                       # changes whenever the original changes
    name: str                          # file name (date fallback, logs)
    album: str                         # nearest folder name, '' at the top of the source
    open: Callable[[], BinaryIO]       # opens the original for reading
    taken_hint: Optional[str] = None   # ISO date from source metadata, used when EXIF has none


# ----------------------------------------------------------------------------
# Dates
# ----------------------------------------------------------------------------

def _valid_date(year: str, month: str, day: str) -> Optional[str]:
    try:
        d = date(int(year), int(month), int(day))
    except ValueError:
        return None
    # Cameras write "0000:00:00" or 1970 when the clock was never set
    if not 1971 <= d.year <= date.today().year + 1:
        return None
    return d.isoformat()


def parse_exif_datetime(raw) -> Optional[str]:
    """'2023:06:14 12:13:14' (EXIF / Drive imageMediaMetadata.time) -> '2023-06-14'."""
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("ascii", "ignore")
    m = _EXIF_DATE_RE.match(str(raw))
    return _valid_date(*m.groups()) if m else None


def date_from_name(name: str) -> Optional[str]:
    m = _NAME_DATE_RE.search(name)
    return _valid_date(*m.groups()) if m else None


def _exif_date(im: Image.Image) -> Optional[str]:
    try:
        exif = im.getexif()
        raw = (exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal)
               or exif.get(ExifTags.Base.DateTime))
    except Exception:
        return None
    return parse_exif_datetime(raw)


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------

def _save_jpeg(im: Image.Image, path: Path, quality: int, icc: Optional[bytes]) -> None:
    """Write atomically, so a crash never leaves a half-written file under a valid name."""
    im.info.pop("icc_profile", None)
    params = {"quality": quality, "optimize": True}
    if icc:
        params["icc_profile"] = icc
    tmp = path.with_name(path.name + ".tmp")
    im.save(tmp, "JPEG", **params)
    os.replace(tmp, path)


def render_photo(src: SourcePhoto, photo_id: str, cache_dir: Path, max_edge: int) -> Photo:
    """Render one original into <id>.jpg + <id>.blur.jpg. Runs in a worker thread."""
    with src.open() as fh, Image.open(fh) as original:
        taken = _exif_date(original) or src.taken_hint or date_from_name(src.name)
        # Keep the color profile (iPhones shoot Display P3) unless the pixels get converted
        icc = original.info.get("icc_profile") if original.mode in ("RGB", "RGBA") else None

        # JPEG: let libjpeg decode at 1/2, 1/4 or 1/8 scale straight away (much faster
        # and lighter than decoding all 12+ MP). The long edge stays >= max_edge.
        w, h = original.size
        scale = max_edge / max(w, h)
        if scale < 1:
            original.draft("RGB", (max(1, round(w * scale)), max(1, round(h * scale))))

        im = ImageOps.exif_transpose(original)  # upright, whatever way the camera was held
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

        backdrop = im.copy()
        backdrop.thumbnail((BACKDROP_EDGE, BACKDROP_EDGE), Image.Resampling.BILINEAR)
        backdrop = backdrop.filter(ImageFilter.GaussianBlur(BACKDROP_BLUR))

    _save_jpeg(im, cache_dir / f"{photo_id}.jpg", JPEG_QUALITY, icc)
    _save_jpeg(backdrop, cache_dir / f"{photo_id}.blur.jpg", BACKDROP_QUALITY, icc)
    return Photo(id=photo_id, source=src.source, album=src.album, taken=taken,
                 width=im.width, height=im.height)


# ----------------------------------------------------------------------------
# Sources
# ----------------------------------------------------------------------------

def scan_local(root: Path, skip: Optional[Path] = None) -> Optional[List[SourcePhoto]]:
    """All photos under root. None when the folder is missing (not mounted, not created yet)."""
    if not root.is_dir():
        return None
    skip_resolved = skip.resolve() if skip else None
    photos: List[SourcePhoto] = []
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        # Skip hidden folders, NAS thumbnail folders (@eaDir) and the cache itself
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith((".", "@")) and (here / d).resolve() != skip_resolved
        )
        rel_dir = here.relative_to(root)
        album = here.name.replace("_", " ") if rel_dir != Path(".") else ""
        for name in sorted(filenames):
            if name.startswith(".") or Path(name).suffix.lower() not in LOCAL_EXTENSIONS:
                continue
            path = here / name
            try:
                st = path.stat()
            except OSError:
                continue
            photos.append(SourcePhoto(
                source=SOURCE_LOCAL,
                key=(rel_dir / name).as_posix(),
                version=f"{st.st_mtime_ns}-{st.st_size}",
                name=name,
                album=album,
                open=lambda p=path: open(p, "rb"),
            ))
    return photos


class DrivePhotoSource:
    """
    Photos in a Google Drive folder (and its subfolders), read with the
    service account the calendar uses.

    Setup: enable the Google Drive API in the service account's Cloud project
    and share the folder with the service account's e-mail (Viewer).
    """

    SCOPE = "https://www.googleapis.com/auth/drive.readonly"
    FOLDER_MIME = "application/vnd.google-apps.folder"
    FIELDS = "nextPageToken, files(id, name, mimeType, md5Checksum, modifiedTime, imageMediaMetadata/time)"
    TIMEOUT_SECONDS = 60
    CHUNK_BYTES = 8 * 1024 * 1024

    def __init__(self, folder_id: str, service_account_file: Optional[Path] = None, service=None):
        self.folder_id = folder_id
        self.service = service
        if self.service is None and service_account_file is not None:
            self.service = self._build_service(service_account_file)

    def _build_service(self, service_account_file: Path):
        try:
            import httplib2
            from google.oauth2 import service_account
            from google_auth_httplib2 import AuthorizedHttp
            from googleapiclient.discovery import build

            if not service_account_file.exists():
                logger.error(f"❌ Photos: service account file not found: {service_account_file}")
                return None
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_file), scopes=[self.SCOPE])
            http = AuthorizedHttp(credentials, http=httplib2.Http(timeout=self.TIMEOUT_SECONDS))
            service = build("drive", "v3", http=http, cache_discovery=False)
            logger.info(f"✅ Google Drive photo source ready (folder {self.folder_id})")
            return service
        except Exception as e:
            logger.error(f"❌ Photos: failed to initialize Google Drive: {e}")
            return None

    def list_photos(self) -> Optional[List[SourcePhoto]]:
        """All photos in the folder tree. None when Drive can't be listed right now."""
        if self.service is None:
            return None
        photos: List[SourcePhoto] = []
        queue: List[Tuple[str, str]] = [(self.folder_id, "")]
        seen = {self.folder_id}
        try:
            while queue:
                folder_id, album = queue.pop(0)
                page_token = None
                while True:
                    resp = self.service.files().list(
                        q=(f"'{folder_id}' in parents and trashed = false and "
                           f"(mimeType = '{self.FOLDER_MIME}' or mimeType contains 'image/')"),
                        fields=self.FIELDS,
                        pageSize=1000,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    ).execute()
                    for f in resp.get("files", []):
                        mime = f.get("mimeType", "")
                        if mime == self.FOLDER_MIME:
                            if f["id"] not in seen:
                                seen.add(f["id"])
                                queue.append((f["id"], f.get("name", "").replace("_", " ")))
                        elif mime in DRIVE_MIME_TYPES:
                            photos.append(SourcePhoto(
                                source=SOURCE_DRIVE,
                                key=f["id"],
                                version=f.get("md5Checksum") or f.get("modifiedTime", ""),
                                name=f.get("name", ""),
                                album=album,
                                open=lambda fid=f["id"]: self.download(fid),
                                taken_hint=parse_exif_datetime((f.get("imageMediaMetadata") or {}).get("time")),
                            ))
                    page_token = resp.get("nextPageToken")
                    if not page_token:
                        break
        except Exception as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status in (403, 404):
                logger.error(
                    f"❌ Photos: Drive folder {self.folder_id} not accessible ({status}). Share it with the "
                    f"service account's e-mail and enable the Google Drive API for its Cloud project.")
            else:
                logger.error(f"⚠️ Photos: Drive listing failed: {e}")
            return None
        return photos

    def download(self, file_id: str) -> BinaryIO:
        from googleapiclient.http import MediaIoBaseDownload

        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request, chunksize=self.CHUNK_BYTES)
        done = False
        while not done:
            _, done = downloader.next_chunk(num_retries=2)
        buf.seek(0)
        return buf


# ----------------------------------------------------------------------------
# Library
# ----------------------------------------------------------------------------

class PhotoLibrary:
    """
    Prepared photos + the shuffle the tile draws from.

    State only changes on the event loop; scanning, rendering and file I/O run
    in worker threads one at a time, so the Pi keeps three cores for the rest.
    """

    def __init__(self, cache_dir: Path, max_edge: int,
                 local_dir: Optional[Path] = None, drive: Optional[DrivePhotoSource] = None):
        self.cache_dir = cache_dir
        self.max_edge = max_edge
        self.local_dir = local_dir
        self.drive = drive
        self.loaded = False
        self._photos: Dict[str, Photo] = {}
        self._failed: Set[str] = set()   # originals that couldn't be rendered (retried after a restart)
        self._pending = 0
        self._bag: List[str] = []
        self._last_shown: Optional[str] = None
        self._missing_dir_logged = False

    # --- what the tile sees ---------------------------------------------------

    @property
    def ready_count(self) -> int:
        return len(self._photos)

    @property
    def pending_count(self) -> int:
        return self._pending

    def next_photo(self) -> Optional[Photo]:
        """Next photo of the shuffle; every photo comes once before any repeats."""
        while True:
            if not self._bag:
                if not self._photos:
                    return None
                self._bag = list(self._photos)
                random.shuffle(self._bag)
                # No back-to-back repeat across two rounds
                if len(self._bag) > 1 and self._bag[-1] == self._last_shown:
                    self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
            photo = self._photos.get(self._bag.pop())
            if photo is not None:  # skips photos removed since the shuffle
                self._last_shown = photo.id
                return photo

    def file_path(self, name: str) -> Optional[Path]:
        """Cache file for '<id>.jpg' / '<id>.blur.jpg'; None for anything else (no path tricks)."""
        m = _FILE_RE.fullmatch(name)
        if not m or m.group(1) not in self._photos:
            return None
        path = self.cache_dir / name
        return path if path.is_file() else None

    # --- keeping it in sync ---------------------------------------------------

    def photo_id(self, src: SourcePhoto) -> str:
        raw = f"{RENDER_VERSION}|{self.max_edge}|{src.source}|{src.key}|{src.version}"
        return hashlib.sha1(raw.encode()).hexdigest()[:_ID_LEN]

    async def refresh(self) -> None:
        """Scan the sources, render new photos (one at a time) and drop removed ones."""
        if not self.loaded:
            self._photos = await asyncio.to_thread(self._load_manifest)
            self.loaded = True
            logger.info(f"🖼️ Photo library: {len(self._photos)} photos ready from cache")

        found, failed_sources = await asyncio.to_thread(self._scan)

        todo = [(pid, src) for pid, src in found.items() if pid not in self._photos and pid not in self._failed]
        self._pending = len(todo)
        if todo:
            logger.info(f"🖼️ Preparing {len(todo)} new photo(s)…")

        added = 0
        for pid, src in todo:
            try:
                photo = await asyncio.to_thread(render_photo, src, pid, self.cache_dir, self.max_edge)
            except Exception as e:
                self._failed.add(pid)
                logger.warning(f"⚠️ Photo skipped ({src.source}: {src.key}): {e}")
            else:
                self._add(photo)
                added += 1
                if added % MANIFEST_SAVE_EVERY == 0:
                    await asyncio.to_thread(self._save_manifest, dict(self._photos))
                    logger.info(f"🖼️ Prepared {added}/{len(todo)} photos")
            finally:
                self._pending -= 1

        # Drop photos that left their source. A source that failed to scan keeps its photos.
        gone = [pid for pid, p in self._photos.items() if p.source not in failed_sources and pid not in found]
        for pid in gone:
            del self._photos[pid]
        self._failed &= set(found)

        await asyncio.to_thread(self._save_manifest, dict(self._photos))
        await asyncio.to_thread(self._prune_files, set(self._photos))
        if todo or gone:
            logger.info(f"🖼️ Photo library: {len(self._photos)} ready (+{added}, -{len(gone)}, "
                        f"{len(todo) - added} skipped)")

    def _add(self, photo: Photo) -> None:
        self._photos[photo.id] = photo
        # Join the current round at a random spot instead of waiting for the next one
        if self._bag:
            self._bag.insert(random.randint(0, len(self._bag)), photo.id)

    def _scan(self) -> Tuple[Dict[str, SourcePhoto], Set[str]]:
        found: Dict[str, SourcePhoto] = {}
        failed: Set[str] = set()

        if self.local_dir is not None:
            local = scan_local(self.local_dir, skip=self.cache_dir)
            if local is None:
                failed.add(SOURCE_LOCAL)
                if not self._missing_dir_logged:
                    logger.info(f"📁 Photos folder not found: {self.local_dir} (create it to add local photos)")
                    self._missing_dir_logged = True
            else:
                self._missing_dir_logged = False
                found.update((self.photo_id(s), s) for s in local)

        if self.drive is not None:
            drive = self.drive.list_photos()
            if drive is None:
                failed.add(SOURCE_DRIVE)
            else:
                found.update((self.photo_id(s), s) for s in drive)

        return found, failed

    def _load_manifest(self) -> Dict[str, Photo]:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / MANIFEST_NAME
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.warning(f"⚠️ Photo manifest unreadable, rebuilding: {e}")
            return {}
        photos: Dict[str, Photo] = {}
        for pid, entry in (data.get("photos") or {}).items():
            try:
                photo = Photo(**entry)
            except TypeError:
                continue
            if (self.cache_dir / f"{pid}.jpg").is_file() and (self.cache_dir / f"{pid}.blur.jpg").is_file():
                photos[pid] = photo
        return photos

    def _save_manifest(self, photos: Dict[str, Photo]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / MANIFEST_NAME
        tmp = path.with_name(path.name + ".tmp")
        payload = {"version": RENDER_VERSION, "photos": {pid: p.to_dict() for pid, p in photos.items()}}
        tmp.write_text(json.dumps(payload, separators=(",", ":")))
        os.replace(tmp, path)

    def _prune_files(self, keep: Set[str]) -> None:
        """Delete cache files of photos that are gone, and leftovers of interrupted writes."""
        try:
            entries = list(os.scandir(self.cache_dir))
        except OSError:
            return
        for entry in entries:
            m = _FILE_RE.fullmatch(entry.name)
            stale = (m is not None and m.group(1) not in keep) or (
                entry.name.endswith(".jpg.tmp"))
            if stale:
                try:
                    os.unlink(entry.path)
                except OSError:
                    pass
