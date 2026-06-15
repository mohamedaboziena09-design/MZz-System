"""
File Store
==========
Manages all file I/O for employee photos and documents.

Files are stored under the project-level ``uploads/`` directory:

    uploads/
    ├─ photos/        ← profile photos     (jpg, jpeg, png, webp)
    └─ documents/     ← employee documents (pdf, doc, docx, jpg, jpeg, png)

Every saved file is renamed to a UUID-based filename to prevent
collisions and avoid exposing original filenames on disk.
The original filename is stored separately in the database.

Usage
-----
    from src.file_store import FileStore
    import pathlib

    store = FileStore()
    rel_path = store.save_photo(
        src=pathlib.Path("/tmp/photo.jpg"),
        original_filename="photo.jpg"
    )
    # rel_path → "uploads/photos/3f7a...b2.jpg"  (stored in DB)
"""

from __future__ import annotations

import pathlib
import shutil
import uuid
from typing import Optional


# ── Defaults ─────────────────────────────────────────────────
UPLOADS_DIR = pathlib.Path(__file__).parent.parent / "uploads"

ALLOWED_PHOTO_EXT: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})
ALLOWED_DOC_EXT:   frozenset[str] = frozenset({".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"})

MAX_PHOTO_SIZE_MB: float = 5.0
MAX_DOC_SIZE_MB:   float = 20.0


# ── Exceptions ───────────────────────────────────────────────

class FileStoreError(Exception):
    """Raised when a file operation cannot be completed."""


# ── FileStore ────────────────────────────────────────────────

class FileStore:
    """Handles saving, retrieving, and deleting uploaded files.

    Parameters
    ----------
    base_dir : pathlib.Path, optional
        Root uploads directory. Defaults to ``<project_root>/uploads``.
    """

    def __init__(self, base_dir: pathlib.Path = UPLOADS_DIR) -> None:
        self.base_dir     = base_dir
        self.photos_dir   = base_dir / "photos"
        self.documents_dir = base_dir / "documents"
        self._ensure_dirs()

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        """Create subdirectories if they don't exist."""
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _check_extension(filename: str, allowed: frozenset[str]) -> str:
        """Return the lowercase extension if it is in *allowed*.

        Raises
        ------
        FileStoreError
            If the extension is not permitted.
        """
        ext = pathlib.Path(filename).suffix.lower()
        if ext not in allowed:
            raise FileStoreError(
                f"File type '{ext}' is not allowed. "
                f"Allowed types: {', '.join(sorted(allowed))}"
            )
        return ext

    @staticmethod
    def _check_size(src: pathlib.Path, max_mb: float) -> None:
        """Raise FileStoreError if *src* exceeds *max_mb* megabytes."""
        size_mb = src.stat().st_size / (1024 * 1024)
        if size_mb > max_mb:
            raise FileStoreError(
                f"File size ({size_mb:.1f} MB) exceeds the maximum "
                f"allowed size of {max_mb:.0f} MB."
            )

    @staticmethod
    def _unique_name(ext: str) -> str:
        """Return a UUID-based filename with the given extension."""
        return f"{uuid.uuid4().hex}{ext}"

    def _relative(self, abs_path: pathlib.Path) -> str:
        """Convert an absolute path under base_dir to a relative string
        suitable for storage in the database.

        Always uses forward slashes regardless of OS (Windows-safe).

        Example
        -------
        ``C:\\project\\uploads\\photos\\abc.jpg`` → ``"uploads/photos/abc.jpg"``
        """
        return abs_path.relative_to(self.base_dir.parent).as_posix()

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def save_photo(self, src: pathlib.Path, original_filename: str) -> str:
        """Copy *src* into ``uploads/photos/`` under a UUID filename.

        Parameters
        ----------
        src : pathlib.Path
            Path to the source file (e.g. a temp file from an upload).
        original_filename : str
            The user-supplied filename, used only to extract the extension.

        Returns
        -------
        str
            Relative path to store in the database
            (e.g. ``"uploads/photos/3f7ab2.jpg"``).

        Raises
        ------
        FileStoreError
            On type or size violations.
        """
        ext  = self._check_extension(original_filename, ALLOWED_PHOTO_EXT)
        self._check_size(src, MAX_PHOTO_SIZE_MB)
        dest = self.photos_dir / self._unique_name(ext)
        shutil.copy2(src, dest)
        return self._relative(dest)

    def save_document(self, src: pathlib.Path, original_filename: str) -> str:
        """Copy *src* into ``uploads/documents/`` under a UUID filename.

        Parameters
        ----------
        src : pathlib.Path
            Path to the source file.
        original_filename : str
            The user-supplied filename, used only to extract the extension.

        Returns
        -------
        str
            Relative path to store in the database
            (e.g. ``"uploads/documents/9c1d44.pdf"``).

        Raises
        ------
        FileStoreError
            On type or size violations.
        """
        ext  = self._check_extension(original_filename, ALLOWED_DOC_EXT)
        self._check_size(src, MAX_DOC_SIZE_MB)
        dest = self.documents_dir / self._unique_name(ext)
        shutil.copy2(src, dest)
        return self._relative(dest)

    def delete_file(self, relative_path: str | None) -> None:
        """Delete a file by its relative path as stored in the database.

        Silently does nothing if *relative_path* is None, empty, or the
        file no longer exists on disk.

        Parameters
        ----------
        relative_path : str or None
            Value previously returned by ``save_photo`` or ``save_document``.
        """
        if not relative_path:
            return
        abs_path = self.base_dir.parent / relative_path
        if abs_path.exists():
            abs_path.unlink()

    def get_absolute_path(self, relative_path: str) -> Optional[pathlib.Path]:
        """Resolve a DB-stored relative path to an absolute ``pathlib.Path``.

        Returns ``None`` if the file does not exist.

        Parameters
        ----------
        relative_path : str
            Value previously returned by ``save_photo`` or ``save_document``.
        """
        abs_path = self.base_dir.parent / relative_path
        return abs_path if abs_path.exists() else None

    def exists(self, relative_path: str) -> bool:
        """Return ``True`` if the file at *relative_path* exists on disk."""
        return (self.base_dir.parent / relative_path).exists()
