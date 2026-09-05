from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

BASE = "/pyhookkit"
DIST = Path(__file__).resolve().parents[1] / "dist"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        identifier = values.get("id")
        if identifier:
            self.ids.add(identifier)

        for name in ("href", "src"):
            value = values.get(name)
            if value:
                self.references.append(value)

        srcset = values.get("srcset")
        if srcset:
            self.references.extend(
                candidate.strip().split()[0]
                for candidate in srcset.split(",")
                if candidate.strip()
            )


def route_for(page: Path) -> str:
    relative = page.relative_to(DIST).as_posix()
    if relative == "index.html":
        return f"{BASE}/"
    if relative.endswith("/index.html"):
        return f"{BASE}/{relative.removesuffix('index.html')}"
    return f"{BASE}/{relative}"


def local_candidates(pathname: str) -> tuple[Path, ...]:
    relative = pathname.removeprefix(BASE).lstrip("/")
    target = DIST / relative
    if pathname.endswith("/") or pathname == BASE:
        return (target / "index.html",) if pathname != BASE else (DIST / "index.html",)
    if target.suffix:
        return (target,)
    return (target, target / "index.html", target.with_suffix(".html"))


def main() -> None:
    if not DIST.is_dir():
        raise SystemExit("dist does not exist; run npm run build first")

    pages: dict[Path, PageParser] = {}
    for page in DIST.rglob("*.html"):
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        pages[page.resolve()] = parser

    failures: list[str] = []
    checked = 0

    for page, parser in pages.items():
        route = route_for(page)
        for reference in parser.references:
            if reference.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
                continue

            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc:
                continue

            resolved = urlsplit(urljoin(f"https://local.invalid{route}", reference))
            pathname = unquote(resolved.path)
            if pathname != BASE and not pathname.startswith(f"{BASE}/"):
                failures.append(
                    f"{page.relative_to(DIST)}: escapes base path: {reference}"
                )
                continue

            target = next(
                (candidate for candidate in local_candidates(pathname) if candidate.exists()),
                None,
            )
            if target is None:
                failures.append(
                    f"{page.relative_to(DIST)}: missing target: {reference}"
                )
                continue

            checked += 1
            target_parser = pages.get(target.resolve())
            if (
                resolved.fragment
                and target_parser is not None
                and unquote(resolved.fragment) not in target_parser.ids
            ):
                failures.append(
                    f"{page.relative_to(DIST)}: missing anchor in "
                    f"{target.relative_to(DIST)}: #{resolved.fragment}"
                )

    if failures:
        print("\n".join(failures))
        raise SystemExit(f"{len(failures)} internal link error(s)")

    print(f"Validated {checked} internal references across {len(pages)} pages.")


if __name__ == "__main__":
    main()
