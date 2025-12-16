# python-accessibility-checker

A Python command-line tool that analyzes web pages or local HTML files for common accessibility issues and generates a timestamped, tabular report with WCAG-inspired recommendations.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Report Format](#report-format)
- [Limitations](#limitations)
- [Roadmap / Ideas](#roadmap--ideas)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This project is a lightweight accessibility helper written in Python.  
It parses a URL or local HTML file, inspects the markup for common issues, and produces a human-readable text report that can be used as a starting point for improving accessibility.

The goal is to make it easy for developers, testers, and product folks to quickly spot frequent accessibility pitfalls before running more advanced tools or manual audits.

---

## Features

- **Input sources**
  - HTTP/HTTPS URLs.
  - Local `.html` / `.htm` files.

- **Checks (heuristic, not exhaustive)**
  - Page title:
    - Missing or empty `<title>`.
    - Very short titles.
  - Headings:
    - Missing `<h1>` or multiple `<h1>`s.
    - Basic detection of heading level “skips” (e.g. `h1` → `h3`).
  - Images:
    - Missing `alt` attributes.
    - Empty `alt=""` on non-obvious decorative images.
    - Very short `alt` text that may be unclear.
  - Links:
    - Links with no visible text.
    - Ambiguous link text like “click here”, “here”, “more”.
  - Forms:
    - Inputs/selects/textareas without associated `<label>`.

- **Error handling**
  - Graceful handling of restricted or failing URLs (401, 403, 4xx, 5xx).
  - Clear messages when local files cannot be opened.

- **Reporting**
  - Plain-text report saved to disk.
  - ASCII **table** with columns:
    - Category
    - Issue
    - Recommendation
    - WCAG reference (where applicable)
  - Filenames include source identifier + timestamp.

---

## Architecture

- **Language:** Python 3.10+  
- **Core modules:**
  - `requests` – fetches remote HTML.
  - `beautifulsoup4` (`bs4`) – parses HTML and queries elements.
  - `datetime`, `os`, `typing` – timestamps, paths, and type hints.

High-level flow:

1. **Input** – Read a URL or local file path from the user.
2. **Fetch** – Use `requests` for URLs or `open()` for local files.
3. **Parse** – Build a `BeautifulSoup` object from the HTML.
4. **Analyze** – Run a set of check functions (titles, headings, images, links, forms).
5. **Report** – Normalize findings into rows and render an ASCII table to a `.txt` file.

---

## Installation

1. **Clone the repository**

