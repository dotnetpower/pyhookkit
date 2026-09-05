# PyHookKit website

This AstroWind-based static site explains how to prepare Teams notifications in
three steps and provides the PyHookKit Starlight documentation portal published
through GitHub Pages.

## Canonical documentation

Do not edit generated files under `src/content/docs/`. The `sync:docs` script
loads the repository-root `README.md`, `README.ko.md`, and top-level files under
`docs/`, adds Starlight frontmatter, rewrites repository-relative links, and
copies documentation assets. The original Markdown remains the canonical source
for GitHub and the website.

## Local development

Requires Node.js 22 or newer.

```shell
npm install
npm run dev
```

The configured GitHub Pages base path is `/pyhookkit/`.

## Verification

```shell
npm run check
npm run build
```

## Attribution

The site is derived from the MIT-licensed
[AstroWind](https://github.com/arthelokyo/astrowind) template. See `LICENSE.md`
and the repository-root `THIRD_PARTY_NOTICES.md`.
