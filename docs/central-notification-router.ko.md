# 중앙 알림 라우터

[English](central-notification-router.md)

중앙 라우터는 GitLab, Argo CD 또는 다른 생성자가 보낸 동일한 정규 알림을
하나의 라우팅 경계를 통해 전송하는 선택적 SQLite 기반 예제입니다. 기존의
Slack 및 Teams 직접 명령은 로컬 테스트, 마이그레이션 및 의도적으로 선택한
대체 경로에 계속 사용할 수 있습니다.

```text
GitLab ──────┐
Argo CD ─────┼── canonical JSON ──> router ──> SQLite outbox
other source ┘                                  ├─ Slack webhook
                                                └─ Teams Workflow
```

팬아웃은 라우터가 담당합니다. Power Automate는 여전히 요청당 하나의 대상만
수신하며 라우팅 데이터베이스가 아니라 Teams 전송 어댑터로 유지됩니다.

## 범위

이 예제는 다음을 제공합니다.

- 엄격한 정규 알림 구문 분석
- 생성자별 전달자 자격 증명
- 하나의 경로를 여러 대상으로 연결하는 구성
- 트랜잭션 방식의 SQLite 알림 및 대상 전송 레코드
- 각 생성자와 `eventId`에 대한 멱등성
- 최소 1회 전송을 보장하는 임대 기반 워커
- 민감 정보가 제거된 집계 및 대상별 전송 상태
- 기존 Slack 및 Teams 렌더러와 재시도 정책 재사용

관리 API, 자동 ID 조회, 배달 못 한 편지 재생 UI 및 다중 노드 워커 조정은
의도적으로 제외합니다. SQLite는 이 단일 프로세스 예제와 적당한 알림
볼륨에 적합합니다. 여러 라우터 복제본을 실행하기 전에 큐 기반 저장소를
사용하세요.

## 경로 초기화

`examples/python`에서 명령을 실행하세요. 데이터베이스 및 자격 증명 파일은
Git에서 무시됩니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  init-db
```

Slack 대상을 추가합니다. 데이터베이스에는 Webhook 값이 아니라 환경 변수
이름만 저장됩니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id slack-release \
  --route release-notifications \
  --provider slack \
  --endpoint-env SLACK_WEBHOOK_URL
```

승인된 채널 링크를 제공하여 Teams 대상을 추가합니다. 서명된 Workflow URL은
SQLite 외부에 유지됩니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-release \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "$TEAMS_WORKFLOW_CHANNEL_LINK"
```

## TeamsNotifyApp 부트스트랩

Azure CLI 위임 토큰을 영구 저장하는 대신 표시되는 단일 테넌트
`TeamsNotifyApp` 등록을 사용하세요. 채널 테넌트에 한 번 로그인합니다.

전체 ID, 최소 역할, 순환 및 복구 런북은
[TeamsNotifyApp 부트스트랩](teams-notify-app-bootstrap.ko.md)에 있습니다.

```shell
az login \
  --tenant "<channel tenant ID>" \
  --use-device-code \
  --allow-no-subscriptions
```

그런 다음 다음을 실행합니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "$TEAMS_WORKFLOW_CHANNEL_LINK" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications \
  --target-id teams-release
```

이 명령은 다음을 수행합니다.

1. 채널 링크에서 테넌트 및 Team ID를 파생합니다.
2. `TeamsNotifyApp`을 만들거나 고유하게 재사용합니다.
3. 해당 테넌트 Service Principal을 만듭니다.
4. Microsoft Graph 애플리케이션 역할 ID를 동적으로 확인합니다.
5. `GroupMember.ReadWrite.All`을 추가하고 테넌트 전체 관리자 동의를
   부여합니다.
6. 부트스트랩 ID를 통해 연결 사용자를 한 번 확인합니다.
7. 재사용 가능한 로컬 자격 증명이 없으면 1년 유효한 클라이언트 비밀을
   만듭니다.
8. 클라이언트 자격 증명이 일치하는 앱 전용 Graph 토큰을 발급하는지
   증명합니다.
9. 연결 사용자를 Team의 기반 Microsoft 365 Group에 추가합니다.
10. 앱 식별자와 비밀을 모드 `0600`으로 리포지토리 `.env`에 원자적으로
    기록합니다.
11. 대상을 SQLite에 등록합니다.

클라이언트 비밀은 절대 출력되지 않습니다. `--rotate-secret`으로 다시
실행하여 대체 자격 증명을 만들고 저장하세요. 대체가 성공한 후 Entra
포털에서 사용하지 않는 자격 증명을 제거하세요.

### 최소 부트스트랩 권한

| 작업 | ID | 최소 권한 |
|---|---|---|
| 앱 등록 만들기 | 부트스트랩 앱 생성자 | 테넌트 정책에서 사용자의 앱 등록을 허용하면 디렉터리 역할 불필요. 허용하지 않으면 **Application Developer** |
| 새로 만든 앱과 자격 증명 관리 | 앱 생성자/소유자 | `TeamsNotifyApp` 소유권. 별도 운영자가 자신이 소유하지 않은 애플리케이션을 관리해야 할 때만 **Cloud Application Administrator** 사용 |
| Microsoft Graph 애플리케이션 권한 부여 | 동의 승인자 | **Privileged Role Administrator**. 사용할 수 있는 경우 PIM을 통해 부트스트랩 동안에만 활성화 |
| 흐름 만들기 및 편집 | 흐름 작성자 | 대상 환경의 Power Platform **Environment Maker** |
| Teams 커넥터 권한 부여 | `svc-teams-notification` | Microsoft 365/Teams 및 Power Automate 라이선스가 있는 사용자. Entra 관리자 역할 불필요 |
| 런타임에 Team 멤버십 추가 | `TeamsNotifyApp` 서비스 주체 | Microsoft Graph 애플리케이션 권한 `GroupMember.ReadWrite.All` |
| 알림 제출 | GitLab, Argo CD 또는 다른 생성자 | 라우터 전달자 자격 증명만 필요. Graph 또는 Power Platform 역할 불필요 |

Microsoft Graph 애플리케이션 권한에는 테넌트 전체 관리자 동의가 필요합니다.
**Privileged Role Administrator**는 Microsoft Graph 앱 역할에 동의할 수
있는 최소 권한의 기본 제공 역할입니다. Global Administrator도 사용할 수
있지만 의도적으로 권장하는 부트스트랩 역할은 아닙니다.

따라서 전체 자동화 명령을 실행하는 사용자에게는 앱 등록을 만들 권한과
활성화된 Privileged Role Administrator 역할이 모두 필요합니다. 이 업무는
운영상 분리할 수 있지만 현재의 단일 명령 부트스트랩은 두 기능이 모두
활성화되어 있을 것으로 예상합니다.

Microsoft 참고 자료:

- [작업별 최소 권한 역할](https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-by-task)
- [테넌트 전체 관리자 동의 부여](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent)
- [애플리케이션 및 서비스 주체 개체](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals)
- [Microsoft 365 그룹 구성원 추가](https://learn.microsoft.com/graph/api/group-post-members?view=graph-rest-1.0)

ID는 Power Automate Teams 연결에 바인딩된 계정과 동일해야 합니다. 흐름
공동 소유자를 추가해도 커넥터 실행 ID는 변경되지 않습니다. 표준 채널
액세스는 Team 멤버십을 따릅니다. 비공개 및 공유 채널에는 명시적인 채널
멤버십이 필요할 수 있으며 비공개 채널로의 Flow bot 전송은 계속 지원되지
않습니다.

등록은 현재의 `teams.cloud.microsoft` 채널 링크와 레거시
`teams.microsoft.com` 링크를 수락합니다. 라우터는 원본 링크와 파생된
테넌트 ID, Team ID, 채널 ID 및 채널 이름을 별도 열에 저장합니다. 전송 시
최상위 `teamId`와 `channelId` 및 하나의 Adaptive Card 첨부 파일이 있는
Teams `message` 봉투를 보내며 채널 링크나 콜백 URL은 보내지 않습니다.

한 경로를 팬아웃하려면 고유한 다른 대상 ID로 `add-destination`을
반복하세요. 리포지토리 `.env`는 자동으로 로드됩니다. TeamsNotifyApp이
구성되어 있으면 명령은 저장된 Graph 액세스 토큰을 읽지 않고 새 앱 전용
토큰을 가져옵니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-another-channel \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "<Teams channel link>" \
  --ensure-team-membership
```

다음 명령으로 비밀이 아닌 구성을 검사하세요.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  list-destinations
```

알림을 보내지 않고 전체 로컬 설정을 확인합니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

`doctor`는 Workflow URL을 검증하고 앱 전용 Graph 토큰을 가져와 검증하며,
활성화된 모든 Team에서 연결 사용자의 멤버십을 확인하고 SQLite 파일이
소유자 전용 모드인지 검사합니다. 자격 증명을 절대 출력하지 않습니다.

## 로컬에서 실행

생성자마다 서로 다른 임의 토큰을 만들고 무시되는 `.env` 또는 다른 비밀
저장소에서 공급자 자격 증명을 주입하세요.

```shell
export PYHOOKKIT_GITLAB_ROUTER_TOKEN="$(python -c \
  'import secrets; print(secrets.token_urlsafe(32))')"
export PYHOOKKIT_ARGOCD_ROUTER_TOKEN="$(python -c \
  'import secrets; print(secrets.token_urlsafe(32))')"

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  serve \
  --producer gitlab=PYHOOKKIT_GITLAB_ROUTER_TOKEN \
  --producer argocd=PYHOOKKIT_ARGOCD_ROUTER_TOKEN
```

프로세스는 다음을 노출합니다.

- `GET /healthz`
- `POST /v1/notifications`
- `GET /v1/notifications/{notificationId}`

POST 엔드포인트는 SQLite가 알림과 모든 대상 레코드를 커밋한 후 `202`를
반환합니다. 전송은 워커에서 이루어지며 `202`는 공급자 전송 증거가
아닙니다. 반환된 알림 ID를 조회하여 `queued`, `delivering`, `delivered`,
`partial_failed` 또는 `failed` 상태를 확인하세요.

커밋된 합성 계약을 제출합니다.

```shell
export NOTIFICATION_ROUTER_URL=http://127.0.0.1:8080
export NOTIFICATION_ROUTER_TOKEN="$PYHOOKKIT_GITLAB_ROUTER_TOKEN"

uv run python -m pyhookkit.entrypoints.notification_router_client \
  --producer gitlab \
  --input ../../contracts/test-vectors/scenarios/deployment-result/notification.json
```

원격 클라이언트에는 HTTPS가 필요합니다. 루프백 HTTP는 로컬 개발에만
허용됩니다.

## GitLab 및 Argo CD

GitLab 파이프라인 입력 `notification-path`는 `direct` 또는 `router`를
선택합니다. 마이그레이션 중에는 `direct`를 유지하고 보호 및 마스킹된
`NOTIFICATION_ROUTER_URL`과 `NOTIFICATION_ROUTER_TOKEN` 변수를 구성한 후
`router`를 선택하세요.

Argo CD에는 별도의 `bookinfo-router-sync-failed` 및
`bookinfo-router-sync-succeeded` 템플릿이 포함되어 있습니다. GitLab 알림
디스패치를 우회하려면 합성 라우터 URL을 구성하고
`notification-router-token` 비밀 키를 만든 다음 각 트리거의 `send` 항목을
해당 라우터 템플릿으로 변경하세요. 동일한 이벤트에 두 템플릿 경로를 모두
활성화하지 마세요.

## 전송 보장 및 제한 사항

한 생성자의 중복 제출은 원래 알림 ID를 반환합니다. 해당 생성자의
`eventId`를 다른 콘텐츠에 재사용하면 충돌이 반환됩니다. 구성된 각 대상은
독립적인 최종 결과를 가지므로 하나의 실패한 채널은 성공한 채널을 숨기지
않고 `partial_failed`를 생성합니다.

워커는 만료된 전송 임대를 복구합니다. 따라서 공급자가 메시지를 수락한 후
SQLite가 성공을 저장하기 전에 프로세스가 실패하면 공급자 메시지가 중복될
수 있습니다. Slack 및 Teams Webhook 전송은 공유 트랜잭션 멱등성 키를
제공하지 않습니다. 소비자는 `eventId`와 표시되는 상관관계 ID를 중복 감지
참조로 취급해야 합니다.

토큰, 서명된 콜백 URL, 정규 페이로드 또는 공급자 응답을 로그에 넣지
마세요. HTTP 전송은 요청 로그를 억제하며 영구 저장되는 전송 오류에는
안정적인 분류와 선택적 HTTP 상태만 포함됩니다.
