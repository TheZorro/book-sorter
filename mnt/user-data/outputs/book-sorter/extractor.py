import os
import re
import logging

logger = logging.getLogger(__name__)


def extract_metadata(filepath: str) -> dict:
    """
    Versucht Metadaten aus einer Datei zu extrahieren.
    Gibt immer ein Dict zurück, auch wenn nur der Dateiname verfügbar ist.
    """
    ext = os.path.splitext(filepath)[1].lower()
    meta = {"title": "", "author": "", "tags": [], "description": "", "source": ""}

    if ext == ".epub":
        meta = _extract_epub(filepath)
    elif ext == ".pdf":
        meta = _extract_pdf(filepath)

    # Fallback: Dateiname parsen wenn Titel/Autor fehlen
    if not meta.get("title") or not meta.get("author"):
        filename_meta = _parse_filename(filepath)
        if not meta.get("title"):
            meta["title"] = filename_meta.get("title", "")
        if not meta.get("author"):
            meta["author"] = filename_meta.get("author", "")
        if not meta.get("source"):
            meta["source"] = "dateiname"

    return meta


def _extract_epub(filepath: str) -> dict:
    try:
        import ebooklib
        from ebooklib import epub

        book = epub.read_epub(filepath, options={"ignore_ncx": True})
        meta = {"title": "", "author": "", "tags": [], "description": "", "source": "epub-metadaten"}

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
            # Kürzen auf 500 Zeichen für den Prompt
            meta["description"] = description[0][0][:500]

        return meta
    except Exception as e:
        logger.warning(f"EPUB-Extraktion fehlgeschlagen für {filepath}: {e}")
        return {"title": "", "author": "", "tags": [], "description": "", "source": ""}


def _extract_pdf(filepath: str) -> dict:
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(filepath)
        info = doc.metadata
        doc.close()

        return {
            "title": info.get("title", ""),
            "author": info.get("author", ""),
            "tags": [],
            "description": info.get("subject", ""),
            "source": "pdf-metadaten",
        }
    except Exception as e:
        logger.warning(f"PDF-Extraktion fehlgeschlagen für {filepath}: {e}")
        return {"title": "", "author": "", "tags": [], "description": "", "source": ""}


def _parse_filename(filepath: str) -> dict:
    """
    Parst Dateinamen im Format:
    - "Autor - Titel.epub"
    - "Autor - [Serie 01] - Titel.epub"
    - "Titel.epub"
    """
    filename = os.path.splitext(os.path.basename(filepath))[0]

    # Format: "Autor - Titel" oder "Autor - [Serie] - Titel"
    parts = filename.split(" - ")
    if len(parts) >= 2:
        author = parts[0].strip()
        # Letzter Teil ist der Titel, mittlere Teile sind Serie etc.
        title = parts[-1].strip()
        # Eckige Klammern aus Titel entfernen
        title = re.sub(r"\[.*?\]", "", title).strip()
        return {"author": author, "title": title}

    return {"author": "", "title": filename}
