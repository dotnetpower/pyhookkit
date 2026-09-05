import path from 'path';
import { fileURLToPath } from 'url';

import { defineConfig, fontProviders } from 'astro/config';

import { unified } from '@astrojs/markdown-remark';

import sitemap from '@astrojs/sitemap';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';
import mdx from '@astrojs/mdx';
import partytown from '@astrojs/partytown';
import icon from 'astro-icon';
import type { AstroIntegration } from 'astro';

import astrowind from './vendor/integration';
import loadConfig from './vendor/integration/utils/loadConfig';

import { responsiveTablesRehypePlugin } from './src/utils/frontmatter';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Blog taxonomy sections marked `robots.index: false` in `src/config.yaml` are
// kept out of the sitemap. Listing a URL that we then ask crawlers not to index
// spends crawl budget on nothing and sends two contradictory signals at once.
// The prefixes are derived from the config instead of hardcoded because these
// pathnames are meant to be renamed (see the comments in `src/config.yaml`).
interface BlogSectionConfig {
  isEnabled?: boolean;
  pathname?: string;
  robots?: { index?: boolean };
}

const themeConfig = (await loadConfig('src/config.yaml')) as {
  apps?: { blog?: Record<string, BlogSectionConfig> };
};

const noindexTaxonomyPaths = ['category', 'tag']
  .map((section) => themeConfig?.apps?.blog?.[section])
  .filter((section): section is BlogSectionConfig => Boolean(section?.isEnabled) && section?.robots?.index === false)
  .map((section) => `/${(section.pathname ?? '').replace(/^\/+|\/+$/g, '')}/`);

const hasExternalScripts = false;
const whenExternalScripts = (items: (() => AstroIntegration) | (() => AstroIntegration)[] = []) =>
  hasExternalScripts ? (Array.isArray(items) ? items.map((item) => item()) : [items()]) : [];

export default defineConfig({
  site: 'https://dotnetpower.github.io',
  base: '/pyhookkit',
  trailingSlash: 'always',
  output: 'static',

  // Prefetch links as they enter the viewport for snappier navigations
  // (works together with <ClientRouter />, which enables prefetch by default).
  prefetch: {
    prefetchAll: true,
    defaultStrategy: 'viewport',
  },

  // Native Fonts API: self-hosts + subsets + preloads Inter and generates
  // metric-adjusted fallbacks. Injected via <Font /> in Layout.astro and
  // consumed through the `--font-inter` CSS variable in CustomStyles.astro.
  fonts: [
    {
      provider: fontProviders.fontsource(),
      name: 'Inter',
      cssVariable: '--font-inter',
      weights: ['100 900'],
      styles: ['normal'],
      subsets: ['latin'],
      fallbacks: ['sans-serif'],
    },
  ],

  integrations: [
    sitemap({
      filter: (page) => !noindexTaxonomyPaths.some((prefix) => new URL(page).pathname.startsWith(prefix)),
    }),
    starlight({
      title: {
        en: 'Teams Webhook Guide',
        ko: 'Teams Webhook 알림 가이드',
      },
      description: 'Send Microsoft Teams Adaptive Card notifications through one shared Power Automate Webhook flow.',
      defaultLocale: 'root',
      locales: {
        root: { label: 'English', lang: 'en' },
        ko: { label: '한국어', lang: 'ko' },
      },
      customCss: ['./src/assets/styles/starlight.css'],
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/dotnetpower/pyhookkit',
        },
      ],
      sidebar: [
        {
          label: 'Start here',
          translations: { ko: '시작하기' },
          items: ['docs', 'docs/teams-webhook-quickstart', 'docs/power-automate-teams-workflow'],
        },
        {
          label: 'Teams notifications',
          translations: { ko: 'Teams 알림' },
          items: ['docs/teams-adaptive-cards', 'docs/teams-delivery-options', 'docs/security'],
        },
        {
          label: 'Optional automation',
          translations: { ko: '선택적 자동화' },
          items: ['docs/teams-notify-app-bootstrap', 'docs/central-notification-router'],
        },
        {
          label: 'PyHookKit and advanced',
          translations: { ko: 'PyHookKit 및 고급 구성' },
          items: [
            'docs/project-overview',
            'docs/notification-parity',
            'docs/slack-examples',
            'docs/getting-started',
            'docs/configuration',
            'docs/logic-app-teams-delivery',
            'docs/migration',
            'docs/infrastructure',
            'docs/integrated-bookinfo-scenario',
          ],
        },
      ],
      lastUpdated: true,
      disable404Route: true,
    }),
    mdx(),
    icon({
      include: {
        tabler: ['*'],
        'flat-color-icons': [
          'template',
          'gallery',
          'approval',
          'document',
          'advertising',
          'currency-exchange',
          'voice-presentation',
          'business-contact',
          'database',
        ],
      },
    }),

    ...whenExternalScripts(() =>
      partytown({
        config: { forward: ['dataLayer.push'] },
      })
    ),

    astrowind({
      config: './src/config.yaml',
    }),
  ],

  image: {
    // Astro's default Sharp service handles local images.
    //
    // Most remote CDN images (Unsplash, Cloudinary, Imgix…) are routed by
    // src/components/common/Image.astro through `unpic`, which rewrites the
    // URL with CDN-side query parameters and serves it straight from the
    // provider — Astro never downloads it, so they don't need to be listed.
    //
    // `domains` only matters for remote URLs that fall through to Astro's
    // native <Image /> (i.e. providers Unpic can't detect, like Pixabay).
    // Listed entries are authorized to be processed by Sharp.
    domains: ['cdn.pixabay.com'],

    // Emit responsive styles for the native <Image layout=…> used by
    // src/components/common/Image.astro (local images). Utility classes on
    // each usage still win, since these styles use low-specificity selectors.
    responsiveStyles: true,
  },

  markdown: {
    processor: unified({
      rehypePlugins: [responsiveTablesRehypePlugin],
    }),
  },

  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        '~': path.resolve(__dirname, './src'),
      },
    },
  },
});
