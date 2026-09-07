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

## Search indexing

GitHub Pages publishes this repository as a project site under `/pyhookkit/`.
Submit the following sitemap directly in Google Search Console and Bing
Webmaster Tools because this repository cannot control the host-root
`https://dotnetpower.github.io/robots.txt`:

```text
https://dotnetpower.github.io/pyhookkit/sitemap-index.xml
```

Set repository variables `GOOGLE_SITE_VERIFICATION_ID` and
`BING_SITE_VERIFICATION_ID` to inject their public verification tokens during
the Pages build. These values are identifiers, not credentials.

The project also publishes `llms.txt`, JSON Schema contracts, and the central
router OpenAPI document under the `/pyhookkit/` base path.

## Attribution

The site is derived from the MIT-licensed
[AstroWind](https://github.com/arthelokyo/astrowind) template. See `LICENSE.md`
and the repository-root `THIRD_PARTY_NOTICES.md`.
