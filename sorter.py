import os
import time
import shutil
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from extractor import extract_metadata
from classifier import classify

LOG_FILE = "/config/sorter.log"
os.makedirs("/config", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = "/downloads"
BOOKS_BASE = "/books"
WAIT_SECONDS = int(os.environ.get("WAIT_SECONDS", "30"))
SUPPORTED_EXTENSIONS = {".epub", ".pdf", ".cbz", ".cbr", ".mobi", ".azw3"}

processing = set()


def format_author_folder(author: str) -> str:
    if not author:
        return "Unknown"
    author = author.strip()
    if "," in author:
        return author
    parts = author.split()
    if len(parts) == 1:
        return author
    lastname = parts[-1]
    firstname = " ".join(parts[:-1])
    return lastname + ", " + firstname


def find_book_files(folder: str):
    found = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                found.append(os.path.join(root, f))
    return found


def process_folder(folder_path: str):
    if folder_path in processing:
        return
    processing.add(folder_path)

    try:
        folder_name = os.path.basename(folder_path)
        logger.info("Processing folder: " + folder_name)

        time.sleep(WAIT_SECONDS)

        if not os.path.exists(folder_path):
            logger.warning("Folder disappeared: " + folder_name)
            return

        book_files = find_book_files(folder_path)
        if not book_files:
            logger.warning("No book files found in: " + folder_name)
            shutil.rmtree(folder_path)
            logger.info("Empty folder deleted: " + folder_name)
            return

        for filepath in book_files:
            filename = os.path.basename(filepath)
            logger.info("Processing file: " + filename)

            metadata = extract_metadata(filepath)
            title = metadata.get("title", "")
            author = metadata.get("author", "")
            source = metadata.get("source", "")
            logger.info("Metadata: Title=" + title + ", Author=" + author + ", Source=" + source)

            category = classify(metadata, filename)
            author_folder = format_author_folder(author)

            dest_dir = os.path.join(BOOKS_BASE, category, author_folder)
            os.makedirs(dest_dir, exist_ok=True)

            dest_path = os.path.join(dest_dir, filename)
            if os.path.exists(dest_path):
                stem = Path(filename).stem
                suffix = Path(filename).suffix
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_dir, stem + "_" + str(counter) + suffix)
                    counter += 1

            shutil.move(filepath, dest_path)
            logger.info("Moved: " + filename + " to " + category + "/" + author_folder + "/")

        shutil.rmtree(folder_path)
        logger.info("Source folder deleted: " + folder_name)

    except Exception as e:
        logger.error("Error processing " + folder_path + ": " + str(e))
    finally:
        processing.discard(folder_path)


def process_file(filepath: str):
    if filepath in processing:
        return
    processing.add(filepath)

    try:
        filename = os.path.basename(filepath)
        logger.info("Processing file: " + filename)

        time.sleep(WAIT_SECONDS)

        if not os.path.exists(filepath):
            logger.warning("File disappeared: " + filename)
            return

        if os.path.getsize(filepath) < 1024:
            logger.warning("File too small, skipping: " + filename)
            return

        metadata = extract_metadata(filepath)
        title = metadata.get("title", "")
        author = metadata.get("author", "")
        source = metadata.get("source", "")
        logger.info("Metadata: Title=" + title + ", Author=" + author + ", Source=" + source)

        category = classify(metadata, filename)
        author_folder = format_author_folder(author)

        dest_dir = os.path.join(BOOKS_BASE, category, author_folder)
        os.makedirs(dest_dir, exist_ok=True)

        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_dir, stem + "_" + str(counter) + suffix)
                counter += 1

        shutil.move(filepath, dest_path)
        logger.info("Moved: " + filename + " to " + category + "/" + author_folder + "/")

    except Exception as e:
        logger.error("Error processing " + filepath + ": " + str(e))
    finally:
        processing.discard(filepath)


class BookHandler(FileSystemEventHandler):
    def on_created(self, event):
        path = event.src_path
        if event.is_directory:
            logger.info("New folder detected: " + os.path.basename(path))
            process_folder(path)
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                logger.info("New file detected: " + os.path.basename(path))
                process_file(path)

    def on_moved(self, event):
        path = event.dest_path
        if event.is_directory:
            logger.info("Folder moved to downloads: " + os.path.basename(path))
            process_folder(path)
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                logger.info("File moved to downloads: " + os.path.basename(path))
                process_file(path)


def main():
    logger.info("Book Sorter Agent started")
    logger.info("Watching: " + DOWNLOADS_DIR)
    logger.info("Target directory: " + BOOKS_BASE)
    logger.info("Wait time after detection: " + str(WAIT_SECONDS) + "s")

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(BOOKS_BASE, exist_ok=True)

    for entry in os.listdir(DOWNLOADS_DIR):
        full_path = os.path.join(DOWNLOADS_DIR, entry)
        if os.path.isdir(full_path):
            logger.info("Existing folder found: " + entry)
            process_folder(full_path)
        else:
            ext = os.path.splitext(entry)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                logger.info("Existing file found: " + entry)
                process_file(full_path)

    event_handler = BookHandler()
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Book Sorter Agent stopped")

    observer.join()


if __name__ == "__main__":
    main()
