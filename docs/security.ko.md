# 보안

[English](security.md)

커밋에는 합성 페이로드, 별칭, 식별자, 경로 및 URL만 사용하세요. Webhook
URL과 토큰은 자격 증명이므로 커밋하지 마세요.

민감한 데이터를 노출할 수 있는 원시 알림이나 공급자 응답을 기록하지 마세요.
승인된 비밀 관리자에서 참조를 통해 런타임 비밀을 주입하세요.

`.env`는 무시되며 로컬 개발 전용입니다. `.env.example`은 값이 비어 있는
변수 이름을 정의하며 자격 증명을 절대 포함하면 안 됩니다. Webhook URL,
`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`, Teams
Workflow URL 및 TeamsNotifyApp 클라이언트 비밀을 자격 증명으로
취급하세요. TeamsNotifyApp 부트스트랩은 모드 `0600`으로 `.env`를
원자적으로 업데이트합니다.

## 자격 증명 소유권

| 자격 증명 | 승인된 소유자 |
|---|---|
| Slack webhook 및 API 토큰 | 로컬 `.env` 또는 배포 비밀 저장소 |
| Power Automate 및 Logic App 콜백 URL | GitLab의 보호되고 마스킹된 변수 |
| Teams 채널 링크 | Git 외부의 보호된 배포 구성 |
| GitLab 생산자 트리거 토큰 | 호출하는 제어 플레인의 비밀 저장소 |
| Argo CD GitLab 프로젝트 토큰 | `argocd-notifications-secret` |
| 중앙 라우터 생산자 토큰 | 생산자별 비밀 저장소 |
| 중앙 라우터 공급자 자격 증명 | 라우터 런타임 비밀 저장소 |
| GitHub Webhook secret | 라우터 런타임 비밀 저장소와 일치하는 GitHub Webhook |
| GitLab `whsec_` signing token | 라우터 런타임 비밀 저장소. GitLab에서 한 번만 복사 |
| Azure DevOps Service Hook password | 라우터 런타임 비밀 저장소와 HTTPS Basic 인증 |
| TeamsNotifyApp 클라이언트 자격 증명 | 라우터 런타임 비밀 저장소 또는 소유자만 접근 가능한 로컬 `.env` |
| Kubernetes 관리자 자격 증명 | Git 외부의 운영자 kubeconfig |

생산자마다 별개의 폐기 가능한 토큰을 사용하세요. GitHub와 AKS 인시던트
프로브가 Argo CD 프로젝트 토큰을 공유하면 안 됩니다. Argo 토큰에는 실용적인
범위에서 가장 짧은 만료 기간을 부여하고 URL이나 알림 본문이 아닌
`PRIVATE-TOKEN` 헤더로 전송하세요.

서버에서 발급하는 `phk_` 생산자 API 키를 권장합니다. SQLite에는 SHA-256
다이제스트와 민감 정보가 제거된 사용 메타데이터만 저장합니다. 각 키를 하나의
경로나 대상으로 제한하고 한 번만 표시하며, 회전할 때 기존 생산자 비밀을
제거하기 전에 키를 폐기하세요.

공급자 원본 수신 인증 방식은 공급자마다 다릅니다.

- GitHub는 정확한 원문 본문의 `X-Hub-Signature-256` HMAC-SHA256을
  사용합니다.
- GitLab Standard Webhooks는
  `{webhook-id}.{webhook-timestamp}.{원문 본문}`의 HMAC-SHA256을 사용하며
  타임스탬프가 최신인지 확인해야 합니다.
- Azure DevOps Service Hooks는 공개 HTTPS와 Basic 인증을 사용합니다.
  공식 Web Hooks 문서에는 HMAC 전송 서명이 정의되어 있지 않습니다.

요청 크기와 속도 제한을 적용한 HTTPS Gateway를 통해 `/v1/inbound/*`만
게시하세요. `/admin`이나 SQLite 파일은 게시하지 마세요.

## 로깅 및 증거 자료

- 사용자가 제공한 사실, URL 또는 ID가 표준 알림에 포함될 수 있으면 원시
  표준 알림을 절대 기록하지 마세요.
- 배달 결과에는 공급자 중립적 상태, 시도 횟수 및 민감 정보가 제거된 오류
  분류만 포함합니다.
- 콜백 URL, 공급자 응답 본문, Socket Mode URL 또는 자격 증명이 포함된
  요청 헤더를 기록하지 마세요.
- 스크린샷은 유용한 최소 영역으로 자르고 계정, 테넌트, 구독, Teams 대상,
  연결 ID 및 서명된 URL을 제거하세요.
- 캡처를 커밋하기 전에 이미지 메타데이터를 제거하세요.
- 로그, 스크린샷, 셸 기록 또는 이슈에 노출된 모든 자격 증명을 교체하세요.

수신 Slack HTTP 요청은 정확한 원시 본문, `X-Slack-Request-Timestamp`,
`X-Slack-Signature`를 기준으로 검증해야 합니다. 재전송 공격을 제한하기
위해 5분보다 오래된 요청은 거부합니다. Slack이 반환한 Socket Mode URL은
수명이 짧은 자격 증명이므로 기록하면 안 됩니다.

로컬 설정 및 교체 지침은 [공급자 구성](configuration.ko.md)을, 콜백 저장은
[Power Automate Teams Workflow 가이드](power-automate-teams-workflow.ko.md)를
참조하세요.

## 공식 보안 참고 자료

- [GitHub Webhook 전송 검증](https://docs.github.com/webhooks/using-webhooks/validating-webhook-deliveries)
- [Slack 요청 검증](https://docs.slack.dev/authentication/verifying-requests-from-slack/)
- [GitLab Webhook 보안](https://docs.gitlab.com/user/project/integrations/webhooks/)
- [Azure DevOps Web Hooks](https://learn.microsoft.com/azure/devops/service-hooks/services/webhooks?view=azure-devops)
