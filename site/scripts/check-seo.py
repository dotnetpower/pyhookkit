#!/usr/bin/env python3
"""Validate SEO and machine-readable signals in the built documentation site."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / "dist"
EXCLUDED_PAGES = {"404.html", "decapcms/index.html"}
SITEMAP_NS = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._in_jsonld = False
        self._jsonld_buffer = ""
        self.metas: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.images: list[dict[str, str | None]] = []
        self.jsonld: list[str] = []
        self.h1_count = 0
        self.mermaid_source_count = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(attributes)
        elif tag == "link":
            self.links.append(attributes)
        elif tag == "img":
            self.images.append(attributes)
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "pre" and attributes.get("data-language") == "mermaid":
            self.mermaid_source_count += 1
        elif tag == "script" and attributes.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buffer = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_jsonld:
            self.jsonld.append(self._jsonld_buffer.strip())
            self._in_jsonld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_jsonld:
            self._jsonld_buffer += data


def meta_content(
    metas: list[dict[str, str | None]],
    attribute: str,
    name: str,
) -> str:
    return next(
        (
            str(meta.get("content") or "")
            for meta in metas
            if meta.get(attribute) == name
        ),
        "",
    )


def validate_pages(errors: list[str]) -> int:
    descriptions: list[str] = []
    page_count = 0
    for file_path in sorted(DIST.rglob("*.html")):
        relative = file_path.relative_to(DIST).as_posix()
        if relative in EXCLUDED_PAGES:
            continue
        page_count += 1
        parser = PageParser()
        parser.feed(file_path.read_text(encoding="utf-8"))

        description = meta_content(parser.metas, "name", "description")
        descriptions.append(description)
        canonical = next(
            (
                str(link.get("href") or "")
                for link in parser.links
                if link.get("rel") == "canonical"
            ),
            "",
        )
        alternates = {
            str(link.get("hreflang") or "")
            for link in parser.links
            if link.get("rel") == "alternate"
        }

        required = {
            "title": " ".join(parser.title.split()),
            "description": description,
            "canonical": canonical,
            "og:image": meta_content(parser.metas, "property", "og:image"),
            "og:image:alt": meta_content(
                parser.metas,
                "property",
                "og:image:alt",
            ),
        }
        for label, value in required.items():
            if not value:
                errors.append(f"{relative}: missing {label}")
        if len(required["title"]) > 70:
            errors.append(f"{relative}: title exceeds 70 characters")
        if parser.h1_count != 1:
            errors.append(f"{relative}: expected one h1, found {parser.h1_count}")
        if alternates != {"en", "ko", "x-default"}:
            errors.append(f"{relative}: incomplete hreflang set {sorted(alternates)}")
        if not parser.jsonld:
            errors.append(f"{relative}: missing JSON-LD")
        schema_types: set[str] = set()
        for value in parser.jsonld:
            try:
                structured = json.loads(value)
                graph = structured.get("@graph", [])
                schema_types.update(
                    str(item.get("@type"))
                    for item in graph
                    if isinstance(item, dict) and item.get("@type")
                )
            except json.JSONDecodeError as error:
                errors.append(f"{relative}: invalid JSON-LD: {error}")
        if relative.startswith("docs/") or relative.startswith("ko/docs/"):
            if not meta_content(parser.metas, "property", "article:modified_time"):
                errors.append(f"{relative}: missing article:modified_time")
        if relative.endswith("docs/teams-webhook-quickstart/index.html") and "HowTo" not in schema_types:
            errors.append(f"{relative}: missing HowTo JSON-LD")
        expected_locale = "ko_KR" if relative.startswith("ko/") else "en_US"
        if meta_content(parser.metas, "property", "og:locale") != expected_locale:
            errors.append(f"{relative}: incorrect og:locale")
        if relative.startswith("ko/") and not required["og:image"].endswith("/brand/og.ko.png"):
            errors.append(f"{relative}: Korean page does not use the Korean OG image")
        if parser.mermaid_source_count:
            errors.append(f"{relative}: Mermaid source was not pre-rendered")
        for image in parser.images:
            if not image.get("alt"):
                errors.append(f"{relative}: image is missing alt text")
            for attribute in ("width", "height", "loading", "decoding"):
                if not image.get(attribute):
                    errors.append(
                        f"{relative}: image {image.get('src')} is missing {attribute}"
                    )

    duplicates = {
        description: count
        for description, count in Counter(descriptions).items()
        if description and count > 1
    }
    if duplicates:
        errors.append(f"duplicate descriptions: {duplicates}")
    return page_count


def validate_sitemap(errors: list[str]) -> int:
    sitemap = ET.parse(DIST / "sitemap-0.xml").getroot()
    urls = sitemap.findall("sitemap:url", SITEMAP_NS)
    for item in urls:
        location = item.findtext("sitemap:loc", default="", namespaces=SITEMAP_NS)
        if item.find("sitemap:lastmod", SITEMAP_NS) is None:
            errors.append(f"{location}: sitemap lastmod is missing")
        languages = {
            link.attrib.get("hreflang", "")
            for link in item.findall("xhtml:link", SITEMAP_NS)
        }
        if languages != {"en", "ko", "x-default"}:
            errors.append(f"{location}: sitemap hreflang set is {sorted(languages)}")
    return len(urls)


def validate_machine_assets(errors: list[str]) -> None:
    expected = (
        "llms.txt",
        "openapi.json",
        "contracts/notification.schema.json",
        "contracts/delivery-result.schema.json",
    )
    for relative in expected:
        if not (DIST / relative).is_file():
            errors.append(f"missing machine-readable asset: {relative}")
    for relative in expected[1:]:
        try:
            json.loads((DIST / relative).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"invalid machine-readable asset {relative}: {error}")

    diagrams = sorted((DIST / "docs-assets" / "generated").glob("*.svg"))
    if len(diagrams) != 4:
        errors.append(f"expected four pre-rendered diagrams, found {len(diagrams)}")

    expected_sitemap = (
        "Sitemap: https://dotnetpower.github.io/pyhookkit/sitemap-index.xml"
    )
    robots = (DIST / "robots.txt").read_text(encoding="utf-8")
    if expected_sitemap not in robots:
        errors.append("robots.txt contains an incorrect sitemap URL")


def main() -> None:
    if not DIST.is_dir():
        raise SystemExit("Build the site before running the SEO check.")
    errors: list[str] = []
    page_count = validate_pages(errors)
    sitemap_count = validate_sitemap(errors)
    validate_machine_assets(errors)
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"Validated SEO signals for {page_count} pages and "
        f"{sitemap_count} sitemap URLs."
    )


if __name__ == "__main__":
    main()
