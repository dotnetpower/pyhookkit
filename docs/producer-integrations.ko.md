# 생산자 통합

[English](producer-integrations.md)

GitHub, GitLab, Argo CD 및 Azure DevOps를 중앙 알림 라우터에 연결합니다.
CI/CD에서 정규 JSON을 제출하거나 공급자 원본 Webhook을 전용 수신 어댑터로
인증·변환할 수 있습니다. 이 가이드는 합성 경로, ID, URL 및 자격 증명만
사용합니다.

## 통합 경로 선택

| 생산자 | 권장 경로 | 공급자 원본 경로 |
|---|---|---|
| GitHub | GitHub Actions에서 정규 JSON 제출 | HMAC-SHA256 Repository Webhook |
| GitLab | GitLab CI에서 정규 JSON 제출 | Standard Webhooks signing token을 사용하는 Project Webhook |
| Argo CD | Notifications Webhook 템플릿에서 정규 JSON 제출 | 템플릿이 원본 통합이므로 별도 수신 어댑터가 필요하지 않음 |
| Azure DevOps | Azure Pipeline에서 정규 JSON 제출 | HTTPS Basic 인증을 사용하는 Service Hooks Web Hook |

사설 라우터에는 self-hosted Runner 또는 Agent가 내부 주소를 호출하는 CI/CD
방식을 사용하세요. 공급자 원본 Webhook에는 공개 HTTPS API Gateway가
필요합니다. `/admin`은 외부에 게시하지 마세요.

## 범위가 제한된 생산자 API 키 발급

생산자와 경로 또는 대상마다 서로 다른 키를 발급합니다. 원문 키는 한 번만
표시되며 SQLite에는 SHA-256 다이제스트만 저장됩니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  issue-api-key \
  --producer github \
  --target-id teams-release
```

`Authorization: Bearer <your-api-key>`로 키를 보내고 일치하는
`X-PyHookKit-Producer` 헤더를 추가합니다. 비밀이 아닌 키 ID로 키를
폐기합니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  revoke-api-key \
  --key-id abcdef123456
```

## GitHub Actions

Bookinfo 릴리스 워크플로는 `notification_path=router`를 지원합니다. 다음
값을 설정합니다.

- Repository Variable `NOTIFICATION_ROUTER_URL`
- 생산자 `github`에 제한된 Repository Secret `NOTIFICATION_ROUTER_TOKEN`
- 한 채널에만 보낼 때 선택적 입력 `router_target_id`

![GitHub Actions New secret 폼에서 NOTIFICATION_ROUTER_TOKEN 이름과 저장 전 합성 phk_ 라우터 API 키를 확인하는 화면입니다.](assets/producer-integrations/github-actions-secret.png)

화면의 값은 합성이며 폼을 제출하지 않았습니다. 실제 일회성 API 키는
Variable이 아니라 Repository Secret 또는 Environment Secret으로 저장하세요.

GitHub-hosted Runner는 HTTPS Gateway를 사용해야 합니다. self-hosted Runner는
내부 라우터 주소를 호출할 수 있습니다.

## GitHub Repository Webhook

1. 엔트로피가 높은 Webhook secret을 만들고 라우터 환경의
   `GITHUB_WEBHOOK_SECRET`에 저장합니다.
2. 통합을 등록합니다.

   ```shell
   uv run python -m pyhookkit.entrypoints.notification_router \
     --database .local/router.sqlite3 \
     add-integration \
     --integration-id github-release \
     --provider github \
     --producer github \
     --secret-env GITHUB_WEBHOOK_SECRET \
     --route release-notifications \
     --target-id teams-release
   ```

3. GitHub에서 **Settings** > **Webhooks** > **Add webhook**을 선택합니다.
4. **Payload URL**에
   `https://notify.example.test/v1/inbound/github/github-release`를 입력합니다.
5. `application/json`을 선택하고 같은 **Secret**을 입력합니다. SSL 검증을
   사용하고 필요한 이벤트만 선택합니다.

![GitHub Add webhook 폼에서 합성 PyHookKit 수신 URL, JSON 콘텐츠 형식, 합성 secret, 활성화된 SSL 검증 및 개별 이벤트 선택을 확인하는 화면입니다.](assets/producer-integrations/github-webhook-settings.png)

이 캡처는 저장하지 않은 문서 예제입니다. 계정 및 저장소 탐색 영역을
제외했으며 실제 엔드포인트나 자격 증명을 포함하지 않습니다.

수신기는 변경되지 않은 원문 본문의 `X-Hub-Signature-256` HMAC-SHA256을
검증하고 `X-GitHub-Delivery`를 멱등성 키로 사용합니다. 현재
`workflow_run`, `deployment_status` 및 Pull Request의 `opened`, `reopened`,
`review_requested` 동작을 지원합니다. GitHub가 처음 보내는 `ping`은 설정된
경로나 대상에 연결 검증 알림 하나로 전송합니다.

## GitLab CI

보호되고 마스킹된 `NOTIFICATION_ROUTER_TOKEN`과
`NOTIFICATION_ROUTER_URL`을 설정하고 `notification-path=router`를
선택합니다. 한 대상만 지정하려면 `NOTIFICATION_ROUTER_TARGET_ID`를
설정합니다.

## GitLab Project Webhook

새 GitLab Webhook에는 기존 평문 `X-Gitlab-Token` 대신 Standard Webhooks
signing token을 사용하세요.

1. **Settings** > **Webhooks**에서 **Add new webhook**을 선택합니다.
2. URL에 `https://notify.example.test/v1/inbound/gitlab/gitlab-release`를
   입력합니다.
3. **Generate signing token**을 선택하고 한 번 표시되는 `whsec_` 값을
   `GITLAB_WEBHOOK_SIGNING_TOKEN`으로 라우터의 보호된 환경에 저장합니다.
4. Pipeline, Deployment 또는 Merge request 이벤트를 선택하고 SSL 검증을
   유지합니다.
5. 라우터 통합을 등록합니다.

   ```shell
   uv run python -m pyhookkit.entrypoints.notification_router \
     --database .local/router.sqlite3 \
     add-integration \
     --integration-id gitlab-release \
     --provider gitlab \
     --producer gitlab \
     --secret-env GITLAB_WEBHOOK_SIGNING_TOKEN \
     --route release-notifications
   ```

수신기는 `{webhook-id}.{webhook-timestamp}.{원문 본문}`의 HMAC-SHA256
`webhook-signature`를 검증합니다. 공백으로 구분된 서명 중 하나가 유효하면
인증하며 5분을 벗어난 타임스탬프는 거부합니다. `webhook-id`를 멱등성 키로
사용합니다.

## Argo CD Notifications

커밋된 Notifications 설정에는 Bearer 인증 `notification-router` 서비스와
Sync 성공·실패 정규 템플릿이 있습니다. `incident-alerts` 경로의 Health
Degraded 템플릿도 제공합니다.

1. 생산자 `argocd`에 경로가 제한된 키를 발급합니다.
2. 키를 `argocd-notifications-secret`의 `notification-router-token`으로
   저장합니다.
3. 합성 라우터 URL과 Argo CD URL을 실제 값으로 교체합니다.
4. Application에서 GitLab 템플릿 또는 라우터 템플릿 중 하나만
   구독합니다.
5. 한 채널에만 보내려면 URL이
   `/v1/destinations/{targetId}/notifications`인 별도 Webhook 서비스를
   설정합니다.

Argo CD는 `retryMax`, `retryWaitMin`, `retryWaitMax`에 따라 네트워크 오류와
HTTP 5xx를 재시도합니다. 계약 또는 인증 4xx 오류는 재시도할 수 없습니다.

## Azure Pipelines

커밋된 Azure Pipeline 예제를 사용합니다. `NOTIFICATION_ROUTER_URL`과 생산자
`azure-devops`에 제한된 비밀 `NOTIFICATION_ROUTER_TOKEN`을 설정합니다. 한
채널에만 보낼 때 `routerTargetId`를 지정합니다. API 키에는 Azure Key
Vault와 연결된 Variable Group을 사용하는 것이 좋습니다.

## Azure DevOps Service Hooks

Azure DevOps 공식 문서는 Web Hooks에 공개 HTTPS와 선택적 Basic 인증을
설명합니다. HMAC 전송 서명은 설명하지 않으므로 임의의 서명 헤더를 만들어
사용하지 마세요.

1. 고유한 password를 만들고 라우터 환경의
   `AZURE_DEVOPS_WEBHOOK_PASSWORD`에 저장합니다.
2. 비밀이 아닌 Basic 사용자 이름으로 `azure-devops` 통합을 등록합니다.
3. **Project settings** > **Service hooks**에서 **Web Hooks** 구독을
   만듭니다.
4. **Build completed** 또는 **Release deployment completed**를 선택합니다.
5. 공개 HTTPS 수신 URL, Basic 사용자 이름 및 password를 입력합니다.
   필요한 경우가 아니면 **Resource details to send**에서 **Minimal**을
   선택합니다.
6. **Test**를 선택하여 2xx 응답을 확인한 후 **Finish**를 선택합니다.

수신기는 `build.complete`와
`ms.vss-release.deployment-completed-event`를 지원합니다. 사설 라우터에는
Service Hook 대신 self-hosted Agent의 Azure Pipeline을 사용하세요.

## 실행 및 검증

라우터와 워커를 시작합니다. 마이그레이션 기간에는 환경 변수 기반 생산자
토큰도 지원합니다. SQLite에서 발급한 API 키만 사용하면 `--producer` 옵션이
필요하지 않습니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  serve
```

공급자의 테스트 전송 기능을 사용한 후 관리 대시보드에서 민감 정보가 제거된
결과를 확인합니다. `202`는 SQLite 접수를 의미합니다. 실제 공급자 전송
결과는 알림 상태에서 확인하세요.

## 보안 및 제한 사항

- 라우터 앞에서 TLS를 종료하고 서명 검증 전에는 원문 요청 바이트를 변경하지
  마세요.
- Gateway에 요청 크기 및 속도 제한을 적용하세요.
- 알림 및 수신 엔드포인트만 게시하고 `/admin`과 SQLite를 노출하지 마세요.
- 공급자 인증 비밀은 환경 주입 또는 관리형 비밀 저장소에 보관하세요.
- 공급자 Payload, 인증 헤더, signing token, 자격 증명이 포함된 URL 및
  공급자 응답을 기록하지 마세요.
- 하나의 SQLite 데이터베이스에는 라우터 복제본 하나만 사용하세요. 수평
  확장 전에는 관리형 트랜잭션 저장소 또는 내구성 큐로 이전하세요.
