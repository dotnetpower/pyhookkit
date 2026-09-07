import { cp, mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import { existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderMermaidSVG } from 'beautiful-mermaid';

import { descriptions, gitLastModified, seoTitles } from './document-metadata.mjs';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repositoryRoot = path.resolve(siteRoot, '..');
const outputRoot = path.join(siteRoot, 'src', 'content', 'docs');
const publicAssetsRoot = path.join(siteRoot, 'public', 'docs-assets');
const publicContractsRoot = path.join(siteRoot, 'public', 'contracts');
const repositoryUrl = 'https://github.com/dotnetpower/pyhookkit';
const siteBase = '/pyhookkit';
const generatedDiagrams = [];

const docsDirectory = path.join(repositoryRoot, 'docs');
const tabbedDocuments = new Set(['docs/teams-webhook-quickstart.md', 'docs/teams-webhook-quickstart.ko.md']);
const documentationFiles = (await readdir(docsDirectory, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
  .map((entry) => path.join(docsDirectory, entry.name));

const sources = [
  path.join(repositoryRoot, 'README.md'),
  path.join(repositoryRoot, 'README.ko.md'),
  ...documentationFiles,
];

function sourceMetadata(source) {
  const relative = path.relative(repositoryRoot, source).replaceAll(path.sep, '/');
  const korean = relative.endsWith('.ko.md');
  const mdx = tabbedDocuments.has(relative);
  const localeRoot = korean ? path.join(outputRoot, 'ko') : outputRoot;

  if (relative === 'README.md' || relative === 'README.ko.md') {
    return {
      korean,
      mdx,
      relative,
      target: path.join(localeRoot, 'docs', 'project-overview.md'),
    };
  }

  const fileName = path
    .basename(source)
    .replace(/\.ko\.md$/, '.md')
    .replace(/\.md$/, mdx ? '.mdx' : '.md');
  return {
    korean,
    mdx,
    relative,
    target: path.join(localeRoot, 'docs', fileName === 'README.md' ? 'index.md' : fileName),
  };
}

const entries = sources.map((source) => ({ source, ...sourceMetadata(source) }));
const targetBySource = new Map(entries.map((entry) => [path.resolve(entry.source), path.resolve(entry.target)]));

function splitDestination(destination) {
  const match = destination.match(/^([^?#]*)([?#].*)?$/);
  return { pathname: match?.[1] ?? destination, suffix: match?.[2] ?? '' };
}

function publishedRoute(target) {
  const relative = path
    .relative(outputRoot, target)
    .replaceAll(path.sep, '/')
    .replace(/\.mdx?$/, '');
  const route = relative.endsWith('/index') ? relative.slice(0, -'/index'.length) : relative;
  return `${siteBase}/${route}/`.replace(/\/{2,}/g, '/');
}

function githubReference(resolvedPath, suffix) {
  const relative = path.relative(repositoryRoot, resolvedPath).replaceAll(path.sep, '/');
  if (relative.startsWith('..')) return null;

  const kind = existsSync(resolvedPath) && statSync(resolvedPath).isDirectory() ? 'tree' : 'blob';
  return `${repositoryUrl}/${kind}/main/${relative}${suffix}`;
}

function rewriteDestination(destination, entry, isImage) {
  if (
    destination === '' ||
    destination.startsWith('#') ||
    destination.startsWith('/') ||
    /^[a-z][a-z\d+.-]*:/i.test(destination) ||
    destination.startsWith('//')
  ) {
    return destination;
  }

  const { pathname: relativePath, suffix } = splitDestination(destination);
  let decodedPath = relativePath;
  try {
    decodedPath = decodeURIComponent(relativePath);
  } catch {
    // Preserve malformed paths exactly; the site link checker will report them.
  }

  const resolved = path.resolve(path.dirname(entry.source), decodedPath);
  const publishedTarget = targetBySource.get(resolved);
  if (publishedTarget) return `${publishedRoute(publishedTarget)}${suffix}`;

  const assetsRoot = path.join(repositoryRoot, 'docs', 'assets');
  const assetRelative = path.relative(assetsRoot, resolved);
  if (!assetRelative.startsWith('..') && !path.isAbsolute(assetRelative)) {
    if (isImage || !resolved.endsWith('.md')) {
      return `${siteBase}/docs-assets/${assetRelative.replaceAll(path.sep, '/')}${suffix}`;
    }
    return githubReference(resolved, suffix) ?? destination;
  }

  if (isImage) return destination;
  return githubReference(resolved, suffix) ?? destination;
}

function rewriteLinks(markdown, entry) {
  const markdownLinks = /(!?\[[^\]]*\]\()([^\s)]+)(\s+(?:"[^"]*"|'[^']*'))?(\))/g;
  const withMarkdownLinks = markdown.replace(markdownLinks, (_match, opening, destination, title = '', closing) => {
    const isImage = opening.startsWith('!');
    return `${opening}${rewriteDestination(destination, entry, isImage)}${title}${closing}`;
  });

  return withMarkdownLinks.replace(
    /(<(?:img|source)\b[^>]*?\s(?:src|srcset)=['"])([^'"]+)(['"])/gi,
    (_match, opening, destination, closing) => {
      return `${opening}${rewriteDestination(destination, entry, true)}${closing}`;
    }
  );
}

function rewriteAlerts(markdown) {
  const variants = {
    NOTE: 'note',
    TIP: 'tip',
    IMPORTANT: 'caution',
    WARNING: 'danger',
    CAUTION: 'danger',
  };

  return markdown.replace(
    /^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\n((?:^>.*(?:\n|$))+)/gm,
    (_match, kind, quotedBody) => {
      const body = quotedBody.replace(/^> ?/gm, '').trimEnd();
      return `:::${variants[kind]}\n${body}\n:::\n`;
    }
  );
}

function rewriteTabs(markdown) {
  return markdown.replace(/<!-- starlight-tabs:start -->\n([\s\S]*?)<!-- starlight-tabs:end -->/g, (_match, body) => {
    const tabs = body
      .trim()
      .split(/^### /m)
      .filter(Boolean)
      .map((section) => {
        const newline = section.indexOf('\n');
        if (newline < 0) throw new Error('A tab heading must have content');
        const label = section.slice(0, newline).trim();
        const content = section.slice(newline + 1).trim();
        return `<TabItem label=${JSON.stringify(label)}>\n\n${content}\n\n</TabItem>`;
      });
    return `<Tabs>\n\n${tabs.join('\n\n')}\n\n</Tabs>`;
  });
}

function rewriteMermaid(markdown, entry, documentTitle) {
  let diagramIndex = 0;
  return markdown.replace(/```mermaid\n([\s\S]*?)```/g, (_match, diagram, offset) => {
    diagramIndex += 1;
    const preceding = markdown.slice(0, offset);
    const headings = [...preceding.matchAll(/^#{1,6}\s+(.+)$/gm)];
    const heading = (headings.at(-1)?.[1] ?? documentTitle).replace(/[`*_]/g, '').trim();
    const label = `${heading}${entry.korean ? ' 다이어그램' : ' diagram'}`;
    const baseName = path.basename(entry.relative, '.md').replace(/\.ko$/, '');
    const fileName = `${baseName}${entry.korean ? '-ko' : ''}-${diagramIndex}.svg`;
    generatedDiagrams.push({
      fileName,
      content: renderMermaidSVG(diagram.trim(), {
        bg: '#ffffff',
        fg: '#171827',
        accent: '#4f46e5',
      }),
    });
    return `![${label}](${siteBase}/docs-assets/generated/${fileName})`;
  });
}

function prepareDocument(sourceText, entry) {
  const heading = sourceText.match(/^#\s+(.+)$/m);
  if (!heading) throw new Error(`Document has no level-one heading: ${entry.relative}`);

  const title = heading[1].replace(/[`*_]/g, '').trim();
  const withoutHeading = sourceText.replace(/^#\s+.+\n+/, '');
  const content = rewriteAlerts(rewriteLinks(rewriteTabs(rewriteMermaid(withoutHeading, entry, title)), entry));
  const componentImport = entry.mdx ? "import { TabItem, Tabs } from '@astrojs/starlight/components';\n\n" : '';
  const generatedComment = entry.mdx
    ? `{/* Generated from ${entry.relative}; edit the canonical source file instead. */}`
    : `<!-- Generated from ${entry.relative}; edit the canonical source file instead. -->`;
  const editUrl = `${repositoryUrl}/edit/main/${entry.relative}`;
  const description = descriptions[entry.relative];
  if (!description) throw new Error(`Document has no description: ${entry.relative}`);
  const lastUpdated = gitLastModified([entry.relative, 'site/scripts/document-metadata.mjs']);
  if (!lastUpdated) throw new Error(`Document has no Git modification date: ${entry.relative}`);
  const customTitle = seoTitles[entry.relative];
  const customHead = customTitle ? `head:\n  - tag: title\n    content: ${JSON.stringify(customTitle)}\n` : '';

  return `---\ntitle: ${JSON.stringify(title)}\ndescription: ${JSON.stringify(
    description
  )}\nlastUpdated: ${lastUpdated}\n${customHead}editUrl: ${JSON.stringify(
    editUrl
  )}\n---\n\n${componentImport}${generatedComment}\n\n${content}`;
}

await rm(outputRoot, { recursive: true, force: true });
await rm(publicAssetsRoot, { recursive: true, force: true });
await rm(publicContractsRoot, { recursive: true, force: true });
await mkdir(outputRoot, { recursive: true });

for (const entry of entries) {
  const sourceText = await readFile(entry.source, 'utf8');
  await mkdir(path.dirname(entry.target), { recursive: true });
  await writeFile(entry.target, prepareDocument(sourceText, entry), 'utf8');
}

const sourceAssets = path.join(repositoryRoot, 'docs', 'assets');
await cp(sourceAssets, publicAssetsRoot, {
  recursive: true,
  filter: (source) => !source.endsWith('.md'),
});

const generatedDiagramsRoot = path.join(publicAssetsRoot, 'generated');
await mkdir(generatedDiagramsRoot, { recursive: true });
for (const diagram of generatedDiagrams) {
  await writeFile(path.join(generatedDiagramsRoot, diagram.fileName), diagram.content, 'utf8');
}

await mkdir(publicContractsRoot, { recursive: true });
for (const fileName of ['notification.schema.json', 'delivery-result.schema.json']) {
  await cp(path.join(repositoryRoot, 'contracts', fileName), path.join(publicContractsRoot, fileName));
}

const generated = await stat(outputRoot);
if (!generated.isDirectory()) throw new Error('Documentation output was not created');
console.log(`Synchronized ${entries.length} canonical Markdown files without modifying their sources.`);
