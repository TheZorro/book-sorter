import os
import logging
import anthropic

logger = logging.getLogger(__name__)

CATEGORIES = ["fiction", "non-fiction", "papers", "magazines", "unsorted"]

SYSTEM_PROMPT = """You are a library assistant that classifies books and documents.
Reply ONLY with exactly one word from this list:
fiction, non-fiction, papers, magazines, unsorted

Definitions:
- fiction: Novels, short stories, science fiction, fantasy, thrillers, crime fiction, literary works
- non-fiction: Reference books, self-help, biographies, business books, history, popular science
- papers: Academic papers, journal articles, dissertations, preprints
- magazines: Periodicals, magazines, comics, manga
- unsorted: When no clear category can be determined

Reply with the category name ONLY, no explanation, no punctuation."""


def classify(metadata: dict, filename: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return "unsorted"

    parts = []
    if metadata.get("title"):
        parts.append("Title: " + metadata["title"])
    if metadata.get("author"):
        parts.append("Author: " + metadata["author"])
    if metadata.get("tags"):
        parts.append("Tags/Genre: " + ", ".join(metadata["tags"]))
    if metadata.get("description"):
        parts.append("Description: " + metadata["description"])
    if metadata.get("source"):
        parts.append("Metadata source: " + metadata["source"])

    ext = os.path.splitext(filename)[1].lower()
    parts.append("File extension: " + ext)
    parts.append("Filename: " + filename)

    user_message = "\n".join(parts)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        result = response.content[0].text.strip().lower()

        if result in CATEGORIES:
            logger.info("Classified as " + result + ": " + filename)
            return result
        else:
            logger.warning("Unexpected response: " + result + " - falling back to unsorted")
            return "unsorted"

    except Exception as e:
        logger.error("Claude API error: " + str(e))
        return "unsorted"
