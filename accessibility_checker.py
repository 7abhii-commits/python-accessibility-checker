import os
from datetime import datetime
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup, Tag


# ------------ Fetch HTML (URL or local file) ------------

def fetch_html(source: str) -> tuple[BeautifulSoup | None, Dict[str, Any]]:
    """
    Load HTML from a URL (http/https) or local file path.

    Returns (soup, meta) where meta includes:
      - type: "url" or "file"
      - source: original input
      - status_code: for URLs, if available
      - error: error message if any
    """
    meta: Dict[str, Any] = {
        "type": "url" if source.startswith(("http://", "https://")) else "file",
        "source": source,
        "status_code": None,
        "error": None,
    }

    # URL case
    if meta["type"] == "url":
        print(f"\nChecking accessibility for URL: {source}\n")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }
        try:
            response = requests.get(source, headers=headers, timeout=20)
            meta["status_code"] = response.status_code

            if response.status_code in (401, 403):
                meta["error"] = (
                    f"Access restricted (HTTP {response.status_code}). "
                    "The page may require login, special headers, or is blocked for automated access."
                )
                print(meta["error"])
                return None, meta
            if 400 <= response.status_code < 600:
                meta["error"] = f"Failed to fetch page (HTTP {response.status_code})."
                print(meta["error"])
                return None, meta

            html = response.text
        except requests.RequestException as exc:
            meta["error"] = f"Error fetching URL: {exc}"
            print(meta["error"])
            return None, meta

        return BeautifulSoup(html, "html.parser"), meta

    # Local file case
    print(f"\nChecking accessibility for local file: {source}\n")
    try:
        with open(source, "r", encoding="utf-8") as f:
            html = f.read()
    except OSError as exc:
        meta["error"] = f"Error opening local file: {exc}"
        print(meta["error"])
        return None, meta

    return BeautifulSoup(html, "html.parser"), meta


# ------------ Accessibility checks ------------

def check_page_title(soup: BeautifulSoup) -> List[str]:
    """Check presence and quality of the page title."""
    issues: List[str] = []
    title_tag = soup.find("title")
    if not title_tag:
        issues.append(
            "Missing <title> element. Recommendation: Add a concise, descriptive <title> for the page (e.g., "
            "\"Product name – Brand\"). [WCAG 2.4.2 Page Titled]"
        )
        return issues

    title_text = title_tag.get_text(strip=True)
    if not title_text:
        issues.append(
            "Empty <title> element. Recommendation: Provide meaningful text that describes the page’s purpose. "
            "[WCAG 2.4.2 Page Titled]"
        )
    elif len(title_text) < 10:
        issues.append(
            f"Very short page title: \"{title_text}\". Recommendation: Expand it to describe page content more clearly. "
            "[WCAG 2.4.2 Page Titled]"
        )
    return issues


def check_headings(soup: BeautifulSoup) -> List[str]:
    """Check heading structure for basic issues."""
    issues: List[str] = []
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headings:
        issues.append(
            "No heading elements (h1–h6) found. Recommendation: Use headings to convey structure, starting with a single "
            "h1 that describes the page. [WCAG 1.3.1 Info and Relationships]"
        )
        return issues

    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        issues.append(
            "No <h1> heading found. Recommendation: Add one main <h1> that describes the page’s primary topic. "
            "[WCAG 1.3.1 Info and Relationships]"
        )
    elif len(h1s) > 1:
        issues.append(
            f"{len(h1s)} <h1> headings found. Recommendation: Ideally use a single <h1> per page for the main title, "
            "and use h2–h6 for subsections. [WCAG 1.3.1 Info and Relationships]"
        )

    last_level = 0
    for h in headings:
        level = int(h.name[1])
        if last_level and level > last_level + 1:
            issues.append(
                f"Heading level skip detected (from h{last_level} to h{level}). "
                "Recommendation: Avoid skipping heading levels; use nested levels in order (h2 after h1, then h3, etc.). "
                "[WCAG 2.4.6 Headings and Labels]"
            )
            break
        last_level = level

    return issues


def check_images_alt(soup: BeautifulSoup) -> List[str]:
    """Check <img> elements for missing or poor alt text."""
    issues: List[str] = []
    images: List[Tag] = soup.find_all("img")
    if not images:
        return issues

    missing_alt = [img for img in images if img.get("alt") is None]
    empty_alt = [img for img in images if img.get("alt") == ""]
    short_alt = [
        img for img in images
        if img.get("alt") not in (None, "")
        and len(img.get("alt", "").strip()) < 3
    ]

    if missing_alt:
        issues.append(
            f"{len(missing_alt)} image(s) missing alt attribute. "
            "Recommendation: Add meaningful alt text for informative images, or alt=\"\" for decorative ones. "
            "[WCAG 1.1.1 Non-text Content]"
        )
    if empty_alt and len(empty_alt) == len(images):
        issues.append(
            "All images have empty alt=\"\". Recommendation: Ensure informative images have descriptive alt text; "
            "use empty alt only for purely decorative images. [WCAG 1.1.1 Non-text Content]"
        )
    elif empty_alt:
        issues.append(
            f"{len(empty_alt)} image(s) with empty alt=\"\". Recommendation: Confirm these are decorative; "
            "otherwise, provide descriptive alt text. [WCAG 1.1.1 Non-text Content]"
        )
    if short_alt:
        issues.append(
            f"{len(short_alt)} image(s) with very short alt text. "
            "Recommendation: Make alt text descriptive enough to convey the image’s purpose. "
            "[WCAG 1.1.1 Non-text Content]"
        )

    return issues


def check_links_text(soup: BeautifulSoup) -> List[str]:
    """Check link text for 'click here' and empty links."""
    issues: List[str] = []
    links: List[Tag] = soup.find_all("a")
    if not links:
        return issues

    bad_phrases = {"click here", "here", "read more", "more"}
    ambiguous = 0
    empty_links = 0

    for a in links:
        text = a.get_text(strip=True).lower()
        if not text:
            empty_links += 1
        elif text in bad_phrases:
            ambiguous += 1

    if empty_links:
        issues.append(
            f"{empty_links} link(s) with no visible text. "
            "Recommendation: Ensure each link has meaningful text or an accessible name (e.g., aria-label). "
            "[WCAG 2.4.4 Link Purpose (In Context)]"
        )
    if ambiguous:
        issues.append(
            f"{ambiguous} link(s) with ambiguous text (e.g., 'click here', 'more'). "
            "Recommendation: Use link text that describes the destination or action (e.g., 'Download annual report'). "
            "[WCAG 2.4.4 Link Purpose (In Context)]"
        )

    return issues


def check_form_labels(soup: BeautifulSoup) -> List[str]:
    """Check that form controls have labels."""
    issues: List[str] = []
    inputs: List[Tag] = soup.find_all("input")
    selects: List[Tag] = soup.find_all("select")
    textareas: List[Tag] = soup.find_all("textarea")

    fields: List[Tag] = inputs + selects + textareas
    if not fields:
        return issues

    labels_by_for = {}
    for label in soup.find_all("label"):
        for_attr = label.get("for")
        if for_attr:
            labels_by_for.setdefault(for_attr, []).append(label)

    missing_labels = 0
    for field in fields:
        if field.name == "input" and field.get("type") == "hidden":
            continue

        has_label = False

        field_id = field.get("id")
        if field_id and field_id in labels_by_for:
            has_label = True

        if not has_label:
            parent = field.parent
            while isinstance(parent, Tag):
                if parent.name == "label":
                    has_label = True
                    break
                parent = parent.parent

        if not has_label:
            missing_labels += 1

    if missing_labels:
        issues.append(
            f"{missing_labels} form control(s) without an associated label. "
            "Recommendation: Use <label for=\"id\"> or wrap controls in <label> so screen readers announce purpose. "
            "[WCAG 3.3.2 Labels or Instructions]"
        )

    return issues


# ------------ Report builder (tabular) ------------

def build_report(soup: BeautifulSoup, meta: Dict[str, Any]) -> str:
    """Build a text report as a table with findings and recommendations."""
    records: List[Dict[str, str]] = []

    def add_records(category: str, findings: List[str]) -> None:
        if not findings:
            records.append({
                "Category": category,
                "Issue": "No obvious issues found in this category based on basic automated checks.",
                "Recommendation": "-",
                "WCAG": "-"
            })
            return
        for text in findings:
            wcag = "-"
            issue = text
            recommendation = "-"

            if "[" in text and text.endswith("]"):
                before, bracket = text.rsplit("[", 1)
                wcag = bracket.rstrip("]")
                issue = before.strip()

            if "Recommendation:" in issue:
                parts = issue.split("Recommendation:", 1)
                issue = parts[0].strip().rstrip(".")
                recommendation = parts[1].strip()

            records.append({
                "Category": category,
                "Issue": issue,
                "Recommendation": recommendation,
                "WCAG": wcag,
            })

    add_records("Page Title", check_page_title(soup))
    add_records("Headings", check_headings(soup))
    add_records("Images (Alt Text)", check_images_alt(soup))
    add_records("Links", check_links_text(soup))
    add_records("Form Labels", check_form_labels(soup))

    now = datetime.now().isoformat(timespec="seconds")
    header_lines: List[str] = []
    header_lines.append("Basic Accessibility Report (Tabular)")
    header_lines.append("=" * 100)
    header_lines.append(f"Source: {meta.get('source', '')}")
    header_lines.append(f"Source type: {meta.get('type')}")
    if meta.get("status_code") is not None:
        header_lines.append(f"HTTP status: {meta['status_code']}")
    header_lines.append(f"Generated at: {now}")
    header_lines.append("")
    header_lines.append(
        "Note: This is a heuristic, partial check and does NOT guarantee WCAG/ADA compliance."
    )
    header_lines.append(
        "For a full audit, use professional tools and manual testing."
    )
    header_lines.append("")

    headers = ["Category", "Issue", "Recommendation", "WCAG"]
    col_widths = {h: len(h) for h in headers}
    for rec in records:
        for h in headers:
            col_widths[h] = max(col_widths[h], len(rec[h]))

    def fmt_row(row: Dict[str, str] | None = None, sep: str = "|") -> str:
        if row is None:
            return sep + sep.join(
                f" {h.ljust(col_widths[h])} " for h in headers
            ) + sep
        return sep + sep.join(
            f" {row[h].ljust(col_widths[h])} " for h in headers
        ) + sep

    def horizontal_line(char: str = "-") -> str:
        total = 1
        for h in headers:
            total += 2 + col_widths[h]
            total += 1
        return char * total

    table_lines: List[str] = []
    table_lines.append(horizontal_line("="))
    table_lines.append(fmt_row(None))
    table_lines.append(horizontal_line("="))
    for rec in records:
        table_lines.append(fmt_row(rec))
        table_lines.append(horizontal_line("-"))

    table_text = "\n".join(table_lines)
    return "\n".join(header_lines) + "\n" + table_text + f"\n\nTimestamp: {now}\n"


# ------------ Orchestration ------------

def generate_report(source: str) -> None:
    """Fetch HTML (URL or file), run checks, and write report to a .txt file."""
    soup, meta = fetch_html(source)
    if soup is None:
        return

    report_text = build_report(soup, meta)

    if meta["type"] == "url":
        safe_part = (
            source.replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .replace("?", "_")
            .replace("&", "_")
            .replace("=", "_")
        )
    else:
        safe_part = os.path.basename(source).replace(".", "_")

    timestamp_short = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"a11y_report_{safe_part}_{timestamp_short}.txt"
    filepath = os.path.join(os.getcwd(), filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nReport saved to: {filepath}")


def main() -> None:
    print("Basic Accessibility Checker (URL or local HTML)")
    print("------------------------------------------------")
    source = input("Enter a URL (https://...) or a local HTML file path: ").strip()
    if not source:
        print("No input provided. Exiting.")
        return

    generate_report(source)


if __name__ == "__main__":
    main()
