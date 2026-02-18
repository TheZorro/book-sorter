import os
import time
import shutil
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from extractor import extract_metadata
from classifier import classify

# Logging konfigurieren
LOG_FILE = "/config/sorter.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),  # auch auf stdout für Docker logs
    ],
)
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = "/downloads"
BOOKS_BASE = "/books"
WAIT_SECONDS = int(os.environ.get("WAIT_SECONDS", "30"))
SUPPORTED_EXTENSIONS = {".epub", ".pdf", ".cbz", ".cbr", ".mobi", ".azw3"}

# Dateien die gerade verarbeitet werden (verhindert Doppelverarbeitung)
processing = set()


def process_file(filepath: str):
    """Verarbeitet eine einzelne Datei: Metadaten → Klassifizierung → Verschieben"""
    if filepath in processing:
        return
    processing.add(filepath)

    try:
        filename = os.path.basename(filepath)
        logger.info(f"Verarbeite: {filename}")

        # Warten bis Datei stabil ist (Download abgeschlossen)
        time.sleep(WAIT_SECONDS)

        # Nochmal prüfen ob Datei noch existiert
        if not os.path.exists(filepath):
            logger.warning(f"Datei verschwunden: {filename}")
            return

        # Dateigrösse prüfen (keine leeren Dateien)
        if os.path.getsize(filepath) < 1024:
            logger.warning(f"Datei zu klein, übersprungen: {filename}")
            return

        # Metadaten extrahieren
        metadata = extract_metadata(filepath)
        logger.info(f"Metadaten: Titel='{metadata.get('title', '')}', Autor='{metadata.get('author', '')}', Quelle='{metadata.get('source', '')}'")

        # Klassifizieren
        category = classify(metadata, filename)

        # Zielordner
        dest_dir = os.path.join(BOOKS_BASE, category)
        os.makedirs(dest_dir, exist_ok=True)

        # Zieldatei – bei Namenskonflikt Nummer anhängen
        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_dir, f"{stem}_{counter}{suffix}")
                counter += 1

        shutil.move(filepath, dest_path)
        logger.info(f"Verschoben: {filename} → {category}/")

    except Exception as e:
        logger.error(f"Fehler bei Verarbeitung von {filepath}: {e}")
        # Datei in unsorted verschieben als Fallback
        try:
            unsorted_dir = os.path.join(BOOKS_BASE, "unsorted")
            os.makedirs(unsorted_dir, exist_ok=True)
            shutil.move(filepath, os.path.join(unsorted_dir, os.path.basename(filepath)))
            logger.info(f"Fallback: {os.path.basename(filepath)} → unsorted/")
        except Exception as e2:
            logger.error(f"Auch Fallback fehlgeschlagen: {e2}")
    finally:
        processing.discard(filepath)


class BookHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        filepath = event.src_path
        ext = os.path.splitext(filepath)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            logger.info(f"Neue Datei erkannt: {os.path.basename(filepath)}")
            process_file(filepath)

    def on_moved(self, event):
        """Reagiert auch auf Umbenennung/Verschieben in den Ordner"""
        if event.is_directory:
            return
        filepath = event.dest_path
        ext = os.path.splitext(filepath)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            logger.info(f"Datei verschoben nach downloads: {os.path.basename(filepath)}")
            process_file(filepath)


def main():
    logger.info("Book Sorter Agent gestartet")
    logger.info(f"Überwache: {DOWNLOADS_DIR}")
    logger.info(f"Zielverzeichnis: {BOOKS_BASE}")
    logger.info(f"Wartezeit nach Erkennung: {WAIT_SECONDS}s")

    # Sicherstellen dass Verzeichnisse existieren
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(BOOKS_BASE, exist_ok=True)

    # Bestehende Dateien beim Start verarbeiten
    existing = [
        os.path.join(DOWNLOADS_DIR, f)
        for f in os.listdir(DOWNLOADS_DIR)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
    ]
    if existing:
        logger.info(f"{len(existing)} bestehende Datei(en) im downloads-Ordner gefunden, werden verarbeitet...")
        for filepath in existing:
            process_file(filepath)

    # Watchdog starten
    event_handler = BookHandler()
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Book Sorter Agent beendet")

    observer.join()


if __name__ == "__main__":
    main()
