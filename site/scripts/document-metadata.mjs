import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const repositoryRoot = path.resolve(siteRoot, '..');

export const descriptions = {
  'README.md':
    'PyHookKit provides typed, provider-neutral notification examples, an optional SQLite router, and semantic parity across Slack and Microsoft Teams.',
  'README.ko.md':
    'PyHookKit은 공급자 중립 알림 예제, 선택적 SQLite 라우터, Slack과 Microsoft Teams의 의미 동등성을 제공하는 도구 모음입니다.',
  'docs/README.md':
    'Choose the shortest verified path for sending Adaptive Cards to Microsoft Teams, then add membership automation or routing only when required.',
  'docs/README.ko.md':
    'Microsoft Teams에 Adaptive Card를 보내는 가장 짧은 검증 경로를 선택하고, 필요한 경우에만 멤버십 자동화와 라우팅을 추가합니다.',
  'docs/central-notification-router.md':
    'Run the optional SQLite notification router with authenticated intake, outbox delivery, Slack and Teams fan-out, status tracking, and an admin dashboard.',
  'docs/central-notification-router.ko.md':
    '인증된 접수, outbox 전송, Slack·Teams 팬아웃, 상태 추적 및 관리 대시보드를 제공하는 선택적 SQLite 알림 라우터를 실행합니다.',
  'docs/central-router-sqlite-data-model.md':
    'Understand the central router SQLite tables, relationships, idempotency keys, delivery leases, state transitions, retention, and stored sensitive data.',
  'docs/central-router-sqlite-data-model.ko.md':
    '중앙 라우터 SQLite 테이블, 관계, 멱등성 키, 전송 임대, 상태 전이, 보존 범위 및 저장되는 민감 데이터를 설명합니다.',
  'docs/configuration.md':
    'Configure Slack, Teams Workflow, TeamsNotifyApp, provider Webhooks, and router credentials without committing signed URLs, tokens, or client secrets.',
  'docs/configuration.ko.md':
    '서명된 URL, 토큰 또는 클라이언트 비밀을 커밋하지 않고 Slack, Teams Workflow, TeamsNotifyApp 및 라우터 자격 증명을 구성합니다.',
  'docs/getting-started.md':
    'Run the paired Slack and Microsoft Teams notification examples with Python 3.12, first without installing PyHookKit and then with the typed package.',
  'docs/getting-started.ko.md':
    'Python 3.12에서 먼저 PyHookKit 설치 없이, 다음으로 형식화된 패키지를 사용해 Slack과 Microsoft Teams 쌍 예제를 실행합니다.',
  'docs/infrastructure.md':
    'Review the repository infrastructure layout for Power Automate, Azure Logic Apps, AKS Bookinfo, GitOps, provider integrations, runtime, and policy.',
  'docs/infrastructure.ko.md':
    'Power Automate, Azure Logic Apps, AKS Bookinfo, GitOps, 공급자 통합, 런타임 및 정책을 위한 저장소 인프라 구성을 설명합니다.',
  'docs/integrated-bookinfo-scenario.md':
    'Run the verified Bookinfo notification scenario across GitHub, GitLab, Argo CD, AKS, Power Automate, and Teams for approval, deployment, incident, and maintenance events.',
  'docs/integrated-bookinfo-scenario.ko.md':
    'GitHub, GitLab, Argo CD, AKS, Power Automate 및 Teams에서 승인, 배포, 인시던트와 유지 관리 Bookinfo 알림 시나리오를 실행합니다.',
  'docs/logic-app-teams-delivery.md':
    'Deploy an Azure Logic App that accepts routed Adaptive Card requests and posts them through an authorized Microsoft Teams managed connection.',
  'docs/logic-app-teams-delivery.ko.md':
    '라우팅된 Adaptive Card 요청을 받아 승인된 Microsoft Teams 관리형 연결로 게시하는 Azure Logic App을 배포합니다.',
  'docs/migration.md':
    'Migrate Slack notification producers to Microsoft Teams incrementally while preserving canonical meaning, rollback, ownership, and delivery verification.',
  'docs/migration.ko.md':
    '정규 의미, 롤백, 소유권과 전송 검증을 유지하면서 Slack 알림 생산자를 Microsoft Teams로 단계적으로 마이그레이션합니다.',
  'docs/notification-parity.md':
    'Define semantic notification parity across Slack and Microsoft Teams, including canonical fields, provider differences, degraded behavior, and parity tests.',
  'docs/notification-parity.ko.md':
    '정규 필드, 공급자 차이, 성능 저하 동작과 동등성 테스트를 포함해 Slack과 Microsoft Teams 간 알림 의미 동등성을 정의합니다.',
  'docs/power-automate-teams-workflow.md':
    'Create and operate one Power Automate flow that receives signed Webhook requests and posts dynamically routed Adaptive Cards to Teams channels.',
  'docs/power-automate-teams-workflow.ko.md':
    '서명된 Webhook 요청을 받아 동적으로 라우팅된 Adaptive Card를 Teams 채널에 게시하는 공통 Power Automate 흐름을 만듭니다.',
  'docs/producer-integrations.md':
    'Connect GitHub, GitLab, Argo CD, and Azure DevOps to the central router through canonical CI/CD submissions or authenticated provider-native Webhooks.',
  'docs/producer-integrations.ko.md':
    '정규 CI/CD 제출 또는 인증된 공급자 원본 Webhook으로 GitHub, GitLab, Argo CD 및 Azure DevOps를 중앙 라우터에 연결합니다.',
  'docs/security.md':
    'Protect notification Webhooks, callback URLs, API keys, Graph credentials, logs, and ownership boundaries across Slack, Teams, CI/CD, and Kubernetes.',
  'docs/security.ko.md':
    'Slack, Teams, CI/CD 및 Kubernetes 전반에서 알림 Webhook, 콜백 URL, API 키, Graph 자격 증명, 로그와 소유권 경계를 보호합니다.',
  'docs/slack-examples.md':
    'Run Slack Incoming Webhook and Web API examples for cards, mentions, actions, images, routing, threads, mutations, pagination, and retry handling.',
  'docs/slack-examples.ko.md':
    '카드, 멘션, 작업, 이미지, 라우팅, 스레드, 변경, 페이지 매김 및 재시도를 다루는 Slack Webhook과 Web API 예제를 실행합니다.',
  'docs/teams-adaptive-cards.md':
    'Design accessible Microsoft Teams Adaptive Cards with semantic hierarchy, supported actions, fallback text, mentions, images, and tested size limits.',
  'docs/teams-adaptive-cards.ko.md':
    '의미 계층, 지원 작업, 대체 텍스트, 멘션, 이미지 및 검증된 크기 제한을 적용해 접근 가능한 Microsoft Teams Adaptive Card를 설계합니다.',
  'docs/teams-delivery-options.md':
    'Compare Power Automate Workflow, Azure Logic Apps, Teams bots, and Microsoft Graph delivery by routing, authentication, mentions, lifecycle, and operations.',
  'docs/teams-delivery-options.ko.md':
    '라우팅, 인증, 멘션, 메시지 수명 주기와 운영 기준으로 Power Automate Workflow, Azure Logic Apps, Teams 봇 및 Graph 전송을 비교합니다.',
  'docs/teams-notify-app-bootstrap.md':
    'Bootstrap TeamsNotifyApp with least-privilege Microsoft Graph permissions to automate posting-identity membership for Teams and private channels.',
  'docs/teams-notify-app-bootstrap.ko.md':
    '최소 권한 Microsoft Graph 권한으로 TeamsNotifyApp을 부트스트랩해 Team과 비공개 채널의 게시 계정 멤버십을 자동화합니다.',
  'docs/teams-webhook-quickstart.md':
    'Send the first Adaptive Card to a standard Microsoft Teams channel in about 10 minutes with one shared Power Automate flow and no router or Graph app.',
  'docs/teams-webhook-quickstart.ko.md':
    '라우터나 Graph 앱 없이 공통 Power Automate 흐름 하나로 약 10분 안에 표준 Microsoft Teams 채널에 첫 Adaptive Card를 보냅니다.',
};

export const seoTitles = {
  'docs/teams-webhook-quickstart.md': 'Teams Webhook quickstart in 10 minutes | PyHookKit',
  'docs/teams-webhook-quickstart.ko.md': '10분 Teams Webhook 빠른 시작 | PyHookKit',
};

export function gitLastModified(relativePaths) {
  const paths = Array.isArray(relativePaths) ? relativePaths : [relativePaths];
  try {
    const value = execFileSync('git', ['log', '-1', '--format=%cI', '--', ...paths], {
      cwd: repositoryRoot,
      encoding: 'utf8',
    }).trim();
    return value || undefined;
  } catch {
    return undefined;
  }
}

export function sourcePathsForUrl(url) {
  const pathname = new URL(url).pathname.replace(/^\/pyhookkit\/?/, '');
  if (pathname === '' || pathname === 'ko/') {
    return [
      'site/src/components/product/ProductLanding.astro',
      'site/src/components/product/DeliveryArchitecture.astro',
      'site/src/components/product/TeamsSetupShowcase.astro',
      'site/src/navigation.ts',
    ];
  }

  const korean = pathname.startsWith('ko/');
  const localized = korean ? pathname.slice(3) : pathname;
  const slug = localized.replace(/^docs\/?/, '').replace(/\/$/, '');
  if (!localized.startsWith('docs')) return [];
  if (slug === '') return [korean ? 'docs/README.ko.md' : 'docs/README.md', 'site/scripts/document-metadata.mjs'];
  if (slug === 'project-overview') return [korean ? 'README.ko.md' : 'README.md', 'site/scripts/document-metadata.mjs'];
  return [`docs/${slug}${korean ? '.ko' : ''}.md`, 'site/scripts/document-metadata.mjs'];
}
