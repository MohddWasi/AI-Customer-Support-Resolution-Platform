import re
from bs4 import BeautifulSoup
from sqlalchemy import true

def clean_html(html: str) -> tuple[str, str]:
     """
    Extract the main readable content from an HTML page.

    Returns:
        A tuple containing (title, cleaned_content).
    """
     soup = BeautifulSoup(html, "html.parser")

     #Extract the document title
     heading = soup.find("h1")

     title = heading.get_text(strip=True) if heading else ""

     if not title and soup.title :
          title = soup.title.get_text(strip=True)

     #remove unwanted elements
     unwanted_elements = [
          "script",
          "svg",
          "style",
          "nav",
          "header",
          "footer",
          "aside",
          "noscript"
     ]

     for elem in soup.find_all(unwanted_elements):
          elem.decompose()

     # Prefer the main content area instead of the entire page.
     main_content = soup.find("main")

     if main_content is None:
          main_content = soup.find("article")

     if main_content is None:
          main_content = soup.body or soup

     content = main_content.get_text(separator="\n")

     # normalize whitespace
     lines = [ re.sub(r"\s", " ", line).strip()
                for line in content.splitlines()]

     # remove empty lines
     cleaned_content = "\n".join(line for line in lines if line)

     return title, cleaned_content

