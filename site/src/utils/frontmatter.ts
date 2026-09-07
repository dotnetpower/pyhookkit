import type { RehypePlugin } from '@astrojs/markdown-remark';
import type { RemarkPlugin } from '@astrojs/markdown-remark';
import type { Element, RootContent } from 'hast';
import type { Image, Parent, Root as MarkdownRoot } from 'mdast';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const docsAssetPrefix = '/pyhookkit/docs-assets/';

function isElement(node: RootContent): node is Element {
  return node.type === 'element';
}

async function addImageMetadata(image: Image, index: number): Promise<void> {
  if (!image.url.startsWith(docsAssetPrefix)) return;

  const relativePath = decodeURIComponent(image.url.slice(docsAssetPrefix.length));
  const assetPath = path.resolve(siteRoot, 'public', 'docs-assets', relativePath);
  const assetsRoot = path.resolve(siteRoot, 'public', 'docs-assets');
  if (!assetPath.startsWith(`${assetsRoot}${path.sep}`)) return;

  const metadata = await sharp(assetPath).metadata();
  const data = (image.data ??= {}) as { hProperties?: Record<string, string | number> };
  const properties = (data.hProperties ??= {});
  if (metadata.width && metadata.height) {
    properties.width = metadata.width;
    properties.height = metadata.height;
  }
  properties.decoding = 'async';
  properties.loading = index === 0 ? 'eager' : 'lazy';
  if (index === 0) properties.fetchPriority = 'high';
}

async function enhanceMarkdown(parent: Parent, context: { imageIndex: number }): Promise<void> {
  for (let i = 0; i < parent.children.length; i++) {
    const child = parent.children[i];
    if (child.type === 'image') {
      await addImageMetadata(child, context.imageIndex++);
    }
    if ('children' in child) await enhanceMarkdown(child, context);
  }
}

export const documentationRemarkPlugin: RemarkPlugin = () => {
  return async function (tree: MarkdownRoot) {
    await enhanceMarkdown(tree, { imageIndex: 0 });
  };
};

export const responsiveTablesRehypePlugin: RehypePlugin = () => {
  return function (tree) {
    if (!tree.children) return;

    for (let i = 0; i < tree.children.length; i++) {
      const child = tree.children[i];
      if (!isElement(child) || child.tagName !== 'table') continue;
      tree.children[i] = {
        type: 'element',
        tagName: 'div',
        properties: { style: 'overflow:auto' },
        children: [child],
      };
      i++;
    }
  };
};
