import re

from bs4 import BeautifulSoup

UNWANTED_TAGS = [
    "script",
    "svg",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "noscript",
    "button",
    "form",
]

# Page widgets that aren't documentation (e.g. "Was this page helpful? Yes No").
UNWANTED_CLASSES = re.compile(r"feedback|breadcrumb", re.IGNORECASE)

# Elements that start a new line; everything else (links, code, bold) stays inline.
BLOCK_TAGS = [
    "address", "article", "blockquote", "dd", "div", "dl", "dt", "figcaption",
    "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "ol", "p",
    "section", "table", "td", "th", "tr", "ul",
]

# Placeholder for a real line break; HTML source newlines inside a paragraph are just spaces.
LINE_BREAK = "\x00"


def _is_inside(element, container) -> bool:
    return any(parent is container for parent in element.parents)


def clean_html(html: str) -> tuple[str, str]:
    """
    Extract the main readable content from an HTML page.

    Returns:
        A tuple containing (title, cleaned_content).
    """
    soup = BeautifulSoup(html, "html.parser")

    for elem in soup.find_all(UNWANTED_TAGS):
        elem.decompose()

    for elem in soup.find_all(class_=UNWANTED_CLASSES):
        if not elem.decomposed:
            elem.decompose()

    # Footnote markers would otherwise glue onto the word before them ("artifacts29").
    for sup in soup.find_all("sup"):
        if sup.get_text(strip=True).isdigit():
            sup.decompose()

    # Prefer the main content area instead of the entire page.
    main_content = soup.find("main") or soup.find("article") or soup.body or soup

    heading = main_content.find("h1") or soup.find("h1")
    title = heading.get_text(" ", strip=True) if heading else ""

    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    # Drop anything before the page heading (sidebar toggles, breadcrumbs).
    # Tags compare by content with ==, so containment is checked by identity.
    if heading is not None and _is_inside(heading, main_content):
        ancestor_ids = {id(parent) for parent in heading.parents}
        for elem in heading.find_all_previous():
            if id(elem) in ancestor_ids or elem.decomposed:
                continue
            if _is_inside(elem, main_content):
                elem.decompose()
        for text in heading.find_all_previous(string=True):
            if _is_inside(text, main_content):
                text.extract()

    # Code blocks keep their line breaks.
    for pre in main_content.find_all("pre"):
        code = pre.get_text().strip("\n").replace("\n", LINE_BREAK)
        pre.replace_with(f"{LINE_BREAK}{code}{LINE_BREAK}")

    for br in main_content.find_all("br"):
        br.replace_with(LINE_BREAK)

    for block in main_content.find_all(BLOCK_TAGS):
        block.insert_before(LINE_BREAK)
        block.insert_after(LINE_BREAK)

    content = main_content.get_text()

    # Normalize whitespace within each line and remove empty lines.
    lines = (re.sub(r"\s+", " ", line).strip() for line in content.split(LINE_BREAK))
    cleaned_content = "\n".join(line for line in lines if line)

    return title, cleaned_content
