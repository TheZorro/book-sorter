# book-sorter

An automated book sorting agent that uses Claude AI to classify and organize ebook downloads into a structured library.

## What it does

- Watches a `/downloads` folder for new ebook files or folders
- Extracts metadata from EPUB and PDF files (title, author, genre tags)
- Falls back to filename parsing if metadata is missing
- Classifies each book using the Claude Haiku API into one of five categories:
  - `fiction` – Novels, sci-fi, fantasy, thrillers, crime
  - `non-fiction` – Self-help, biographies, history, science
  - `papers` – Academic papers, journal articles, dissertations
  - `magazines` – Periodicals, comics, manga
  - `unsorted` – Fallback when no clear category can be determined
- Moves files into `Lastname, Firstname` subfolders per category (e.g. `Corey, James S. A.`)
- Deletes empty source folders after processing

## Supported file formats

`.epub`, `.pdf`, `.mobi`, `.azw3`, `.cbz`, `.cbr`

## Requirements

- Docker
- An [Anthropic API key](https://console.anthropic.com/) (Claude Haiku is used – very low cost, typically < $0.05/month for a home library)

## Folder structure

The agent expects the following volume structure:

```
/downloads/          ← Drop new books here (files or folders)
/books/
  fiction/
    Corey, James S. A./
      Leviathan Falls.epub
    Ashton, Edward/
      Antimatter Blues.mobi
  non-fiction/
  papers/
  magazines/
  unsorted/
```

Create these folders before first run:

```bash
mkdir -p /path/to/books/{fiction,non-fiction,papers,magazines,unsorted}
mkdir -p /path/to/book-sorter/config
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/book-sorter.git
cd book-sorter
```

### 2. Create your .env file

```bash
cp .env.example .env
nano .env
```

Add your Anthropic API key:

```
ANTHROPIC_API_KEY=your-key-here
```

### 3. Build the Docker image

```bash
docker build -t book-sorter:latest .
```

### 4. Deploy

Adjust the volume paths in `docker-compose.yml` to match your setup, then:

```bash
docker compose up -d
```

## Example docker-compose.yml

```yaml
services:
  book-sorter:
    image: book-sorter:latest
    container_name: book-sorter
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
      - WAIT_SECONDS=30
      - ANTHROPIC_API_KEY=your-key-here
    volumes:
      - /opt/book-sorter/config:/config
      - /path/to/books/downloads:/downloads
      - /path/to/books/fiction:/books/fiction
      - /path/to/books/non-fiction:/books/non-fiction
      - /path/to/books/papers:/books/papers
      - /path/to/books/magazines:/books/magazines
      - /path/to/books/unsorted:/books/unsorted
    restart: unless-stopped
```

> **Portainer users:** Deploy as a Stack by pasting the above YAML into the web editor. Build the image manually via SSH first (`docker build -t book-sorter:latest .`), then use `image: book-sorter:latest` in the Stack definition.

## Configuration

All configuration is done via environment variables:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Required. Your Anthropic API key. |
| `WAIT_SECONDS` | `30` | Seconds to wait after detecting a new file before processing. Prevents processing incomplete downloads. |
| `TZ` | `UTC` | Timezone for log timestamps. |
| `PUID` / `PGID` | – | Optional. Set to match your host user for correct file permissions. |

## Logs

Logs are written to /config/sorter.log inside the container (map this to a host path via volumes). They are also available via docker logs book-sorter or in Portainer.

Example log output:
```
2026-02-18 16:06:29 [INFO] Processing file: Edward Ashton - Antimatter Blues.mobi
2026-02-18 16:06:29 [INFO] Metadata: Title=Antimatter Blues, Author=Edward Ashton, Source=filename
2026-02-18 16:06:32 [INFO] Classified as fiction: Edward Ashton - Antimatter Blues.mobi
2026-02-18 16:06:32 [INFO] Moved: Edward Ashton - Antimatter Blues.mobi to fiction/Ashton, Edward/
```

## Known limitations

- Author name formatting works best with "Firstname Lastname" metadata. Some sources store names differently (e.g. already as "Lastname, Firstname" or a single name) – the agent handles these cases but results may vary.
- MOBI files do not always contain embedded metadata; the agent falls back to filename parsing in these cases.
- The agent processes folders and files at the top level of `/downloads`. Nested structures within a single download folder are supported.

## Architecture

```
sorter.py       ← Watchdog file monitor, orchestrates the pipeline
extractor.py    ← Metadata extraction (EPUB via ebooklib, PDF via PyMuPDF, fallback via filename)
classifier.py   ← Claude Haiku API call for category classification
```

## License

MIT
