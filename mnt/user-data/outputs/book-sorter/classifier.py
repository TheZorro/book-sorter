import os
import logging
import anthropic

logger = logging.getLogger(__name__)

CATEGORIES = ["fiction", "non-fiction", "papers", "magazines", "unsorted"]

SYSTEM_PROMPT = """Du bist ein Bibliotheksassistent, der Bücher und Dokumente klassifiziert.
Du antwortest IMMER nur mit genau einem Wort aus dieser Liste:
fiction, non-fiction, papers, magazines, unsorted

Definitionen:
- fiction: Romane, Erzählungen, Science-Fiction, Fantasy, Thriller, Krimis, literarische Werke
- non-fiction: Sachbücher, Ratgeber, Biographien, Geschäftsbücher, Selbsthilfe, Geschichte, Wissenschaftspopulärbücher
- papers: Wissenschaftliche Aufsätze, Journalartikel, akademische Arbeiten, Dissertationen, Preprints
- magazines: Zeitschriften, Periodika, Magazine, Comics, Manga
- unsorted: Wenn keine klare Zuordnung möglich ist

Antworte NUR mit dem Kategorienamen, ohne Erklärung, ohne Satzzeichen."""


def classify(metadata: dict, filename: str) -> str:
    """
    Klassifiziert eine Datei anhand ihrer Metadaten.
    Gibt einen Kategorienamen zurück.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY nicht gesetzt")
        return "unsorted"

    # Prompt zusammenbauen
    parts = []
    if metadata.get("title"):
        parts.append(f"Titel: {metadata['title']}")
    if metadata.get("author"):
        parts.append(f"Autor: {metadata['author']}")
    if metadata.get("tags"):
        parts.append(f"Tags/Genre: {', '.join(metadata['tags'])}")
    if metadata.get("description"):
        parts.append(f"Beschreibung: {metadata['description']}")
    if metadata.get("source"):
        parts.append(f"Metadatenquelle: {metadata['source']}")

    # Dateiendung als Hinweis
    ext = os.path.splitext(filename)[1].lower()
    parts.append(f"Dateiendung: {ext}")
    parts.append(f"Dateiname: {filename}")

    user_message = "\n".join(parts)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        result = response.content[0].text.strip().lower()

        if result in CATEGORIES:
            logger.info(f"Klassifiziert als '{result}': {filename}")
            return result
        else:
            logger.warning(f"Unerwartete Antwort von Claude: '{result}' – fallback zu 'unsorted'")
            return "unsorted"

    except Exception as e:
        logger.error(f"Claude API Fehler: {e}")
        return "unsorted"
