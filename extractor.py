import os
import re
import logging

logger = logging.getLogger(__name__)


def extract_metadata(filepath: str) -> dict:
    ext = os.path.splitext(filepath)[1].lower()
    meta = {"title": "", "author": "", "tags": [], "description": "", "source": ""}

    if ext == ".epub":
        meta = _extract_epub(filepath)
    elif ext == ".pdf":
        meta = _extract_pdf(filepath)

    if not meta.get("title") or not meta.get("author"):
        filename_meta = _parse_filename(filepath)
        if not meta.get("title"):
            meta["title"] = filename_meta.get("title", "")
        if not meta.get("author"):
            meta["author"] = filename_meta.get("author", "")
        if not meta.get("source"):
            meta["source"] = "filename"

    return meta


def _extract_epub(filepath: str) -> dict:
    try:
        import ebooklib
        from ebooklib import epub

        book = epub.read_epub(filepath, options={"ignore_ncx": True})
        meta = {"title": "", "author": "", "tags": [], "description": "", "source": "epub-metadata"}

        title = book.get_metadata("DC", "title")
        if title:
            meta["title"] = title[0][0]

        creator = book.get_metadata("DC", "creator")
        if creator:
            meta["author"] = creator[0][0]

        subject = book.get_metadata("DC", "subject")
        if subject:
            meta["tags"] = [s[0] for s in subject]

        description = book.get_metadata("DC", "description")
        if description:
            meta["description"] = description[0][0][:500]

        return meta
    except Exception as e:
        logger.warning("EPUB extraction failed for " + filepath + ": " + str(e))
        return {"title": "", "author": "", "tags": [], "description": "", "source": ""}


def _extract_pdf(filepath: str) -> dict:
    try:
        import fitz

        doc = fitz.open(filepath)
        info = doc.metadata
        doc.close()

        return {
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "tags": [],
            "description": info.get("subject", ""),
            "source": "pdf-metadata",
        }
    except Exception as e:
        logger.warning("PDF extraction failed for " + filepath + ": " + str(e))
        return {"title": "", "author": "", "tags": [], "description": "", "source": ""}


def _parse_filename(filepath: str) -> dict:
    filename = os.path.splitext(os.path.basename(filepath))[0]
    parts = filename.split(" - ")
    if len(parts) >= 2:
        author = parts[0].strip()
        title = parts[-1].strip()
        title = re.sub(r"\[.*?\]", "", title).strip()
        return {"author": author, "title": title}
    return {"author": "", "title": filename}
