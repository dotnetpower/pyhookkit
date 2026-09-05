import { getPermalink } from './utils/permalinks';

const englishHeaderData = {
  links: [
    { text: '3-step setup', href: '#setup' },
    { text: 'Roles', href: '#roles' },
    { text: 'Send notifications', href: '#send' },
    { text: 'Docs', href: getPermalink('/docs/') },
    { text: '한국어', href: getPermalink('/ko/') },
  ],
  actions: [
    {
      text: 'GitHub',
      href: 'https://github.com/dotnetpower/pyhookkit',
      target: '_blank',
      icon: 'tabler:brand-github',
    },
  ],
};

const koreanHeaderData = {
  links: [
    { text: '3단계 설정', href: '#setup' },
    { text: '역할 구분', href: '#roles' },
    { text: '알림 보내기', href: '#send' },
    { text: '문서', href: getPermalink('/ko/docs/') },
    { text: 'English', href: getPermalink('/') },
  ],
  actions: englishHeaderData.actions,
};

const englishFooterData = {
  links: [
    {
      title: 'Documentation',
      links: [
        { text: '10-minute quickstart', href: getPermalink('/docs/teams-webhook-quickstart/') },
        { text: 'Power Automate flow', href: getPermalink('/docs/power-automate-teams-workflow/') },
        { text: 'Adaptive Cards', href: getPermalink('/docs/teams-adaptive-cards/') },
      ],
    },
    {
      title: 'Teams delivery',
      links: [
        { text: 'Delivery options', href: getPermalink('/docs/teams-delivery-options/') },
        { text: 'Optional TeamsNotifyApp', href: getPermalink('/docs/teams-notify-app-bootstrap/') },
        { text: 'Optional router', href: getPermalink('/docs/central-notification-router/') },
      ],
    },
    {
      title: 'Project',
      links: [
        { text: 'Source code', href: 'https://github.com/dotnetpower/pyhookkit' },
        { text: 'Examples', href: 'https://github.com/dotnetpower/pyhookkit/tree/main/examples' },
        { text: 'Contracts', href: 'https://github.com/dotnetpower/pyhookkit/tree/main/contracts' },
      ],
    },
  ],
  secondaryLinks: [
    { text: 'MIT License', href: 'https://github.com/dotnetpower/pyhookkit/blob/main/LICENSE' },
    { text: 'Third-party notices', href: 'https://github.com/dotnetpower/pyhookkit/blob/main/THIRD_PARTY_NOTICES.md' },
  ],
  socialLinks: [{ ariaLabel: 'GitHub', icon: 'tabler:brand-github', href: 'https://github.com/dotnetpower/pyhookkit' }],
  footNote: 'Send Microsoft Teams notifications through one shared Power Automate Webhook flow.',
};

const koreanFooterData = {
  ...englishFooterData,
  links: [
    {
      title: '문서',
      links: [
        { text: '10분 빠른 시작', href: getPermalink('/ko/docs/teams-webhook-quickstart/') },
        { text: 'Power Automate 흐름', href: getPermalink('/ko/docs/power-automate-teams-workflow/') },
        { text: 'Adaptive Card', href: getPermalink('/ko/docs/teams-adaptive-cards/') },
      ],
    },
    {
      title: 'Teams 전송',
      links: [
        { text: '전송 옵션', href: getPermalink('/ko/docs/teams-delivery-options/') },
        { text: '선택적 TeamsNotifyApp', href: getPermalink('/ko/docs/teams-notify-app-bootstrap/') },
        { text: '선택적 라우터', href: getPermalink('/ko/docs/central-notification-router/') },
      ],
    },
    {
      title: '프로젝트',
      links: englishFooterData.links[2].links,
    },
  ],
  secondaryLinks: [
    { text: 'MIT 라이선스', href: 'https://github.com/dotnetpower/pyhookkit/blob/main/LICENSE' },
    { text: '서드파티 고지', href: 'https://github.com/dotnetpower/pyhookkit/blob/main/THIRD_PARTY_NOTICES.md' },
  ],
  footNote: '하나의 공통 Power Automate Webhook 흐름으로 Microsoft Teams 알림을 보내세요.',
};

export const getHeaderData = (locale: 'en' | 'ko' = 'en') => (locale === 'ko' ? koreanHeaderData : englishHeaderData);

export const getFooterData = (locale: 'en' | 'ko' = 'en') => (locale === 'ko' ? koreanFooterData : englishFooterData);
