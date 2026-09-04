# PyHookKit

[English](README.md)

Slack과 Microsoft Teams에 의미적으로 동등한 알림을 타입 안전하게
전달하고, 공급자 간 마이그레이션을 통제된 방식으로 진행하기 위한
프로젝트다.

## Slack과 Teams 동등성

PyHookKit은 각 공급자의 네이티브 표현 모델을 사용하면서 알림의 의미를
보존한다. 하나의 canonical notification을 서로 다른 payload 형태로
렌더링하며, 시각적 모양이 동일한 것을 동등성으로 정의하지 않는다.

| 항목 | Slack | Microsoft Teams |
|---|---|---|
| 카드 모델 | Block Kit block을 포함하는 Incoming Webhook attachment | Adaptive Card 1.4 attachment를 포함하는 Workflow message |
| 심각도 | 색상이 있는 attachment rail | 중앙 정렬된 의미 레이블과 색상 |
| 사실 정보 | 2열 `mrkdwn` field | 스타일이 적용된 `ColumnSet` fact panel |
| 사용자 멘션 | 어댑터가 해석한 `<@USER_ID>` | 어댑터가 해석한 `<at>` 텍스트와 mention entity |
| 그룹 멘션 | 네이티브 `<!subteam^GROUP_ID>` | 추가 Graph 멤버 확장 설정 필요 |
| 링크 action | Block Kit URL button | `Action.OpenUrl` |
| 답글과 lifecycle | 지원되는 경우 `thread_ts`, `chat.update`, `chat.delete` | 명시적인 Workflow fallback/unsupported 카드, 변경 작업에는 bot 또는 Graph 필요 |
| 전달 | Incoming Webhook 또는 Slack Web API | Teams Workflow callback URL 또는 route가 지정된 Azure Logic App |

### 권장 Teams 전달 방식

Teams 예제는 빈 상태에서 생성한 Power Automate Workflow를 기준으로 한다.
Flow는 **When a Teams webhook request is received**에서 Adaptive Card
envelope를 받고, **Post card in a chat or channel**을 통해 설정된 채널에
카드 내용을 게시한다.

채널 알림의 기본 권장 방식이다. 중앙 라우터는 승인된 채널 링크와 추출된
메타데이터를 저장하고, `teamId`와 `channelId`를 포함한 Adaptive Card
message envelope를 하나의 공유 Flow callback으로 전달한다.

실제 테스트에서 풍부한 카드와 네이티브 사용자 멘션이 정상 동작했고,
gallery template Workflow가 추가하는 소유자 attribution과 **Get
template** footer가 표시되지 않음을 확인했다. Gallery template은 빠른
개념 검증에 유용하며, Azure Logic Apps는 Azure 관리형 배포나 호출자가
Team 및 Channel ID를 이미 갖고 있는 경우에 더 적합하다.

실제 답글, 업데이트, 삭제 또는 통제된 발신자 ID가 필요하면 Teams bot이나
Microsoft Graph 어댑터를 사용해야 한다.

검증된 trigger, action, Adaptive Card expression, credential 처리,
스크린샷 및 smoke test는 [Power Automate Teams Workflow 설정
가이드](docs/power-automate-teams-workflow.md)를 따른다. 요청별 Team 및
채널 route가 필요한 경우 [Azure Logic App Teams 전달
가이드](docs/logic-app-teams-delivery.md)를 사용한다. 테스트한 대안과
trade-off는 [Teams 전달 방식](docs/teams-delivery-options.md)을 참고한다.

### 통합 전달 시나리오

인프라 예제는 Istio 없이 Bookinfo를 AKS에서 실행하고, 책임을 중복하지
않으면서 세 전달 control plane을 연결한다. GitHub는 staging 승인을,
GitLab은 GitOps revision 검증 및 승격을, Argo CD는 AKS reconciliation을
담당한다. 승인, 배포, incident 및 maintenance 이벤트는 GitLab job이
Power Automate를 통해 렌더링하고 전송하기 전까지 공급자 중립 계약을
유지한다.

아키텍처와 부트스트랩 순서는 [인프라
가이드](docs/infrastructure.md#aks-bookinfo-notification-environment)를
참고한다.

[통합 Bookinfo 시나리오](docs/integrated-bookinfo-scenario.md)에는 실제
승인, GitOps 승격, Argo CD reconciliation, incident, maintenance 및
Teams 전달 증거가 포함돼 있다.

### 선택적 중앙 라우터

GitLab과 Argo CD는 같은 canonical contract를 작은 SQLite 기반 중앙
라우터에 제출할 수 있다. 중앙 라우터는 기존 Slack 및 Teams 어댑터를
재사용하면서 생산자 인증, 하나의 route에서 여러 destination으로의
fan-out, 대상별 상태, 멱등적인 접수를 제공한다. 직접 전달은 명시적인
마이그레이션 및 fallback 경로로 유지한다.

Route 설정, 로컬 실행 및 생산자 통합은 [중앙 알림 라우터
가이드](docs/central-notification-router.md)를 참고한다. Portal에서
확인 가능한 앱 등록, 운영자 최소 권한, 자동 환경 설정 및 멤버십 진단은
[TeamsNotifyApp 한국어 부트스트랩
가이드](docs/teams-notify-app-bootstrap.ko.md)를 사용한다.

## Teams end-to-end 설정

이 절차는 새 tenant에서 시작해 하나의 canonical notification이 SQLite
중앙 라우터, Power Automate, Microsoft Teams를 거쳐 전달되는 단계까지
다룬다. 별도 안내가 없다면 저장소 루트에서 명령을 실행한다.

### 사전 요구사항

| 요구사항 | 목적 |
|---|---|
| Python 3.12 및 `uv` | PyHookKit 설치와 실행 |
| Azure CLI | `TeamsNotifyApp` 생성 및 검증 |
| Teams가 포함된 Microsoft 365 tenant | 대상 Team과 채널 소유 |
| Power Platform 환경 | Power Automate Flow와 Teams connection 소유 |
| `svc-teams-notification` 같은 라이선스가 있는 전용 사용자 | Teams connector 승인 및 알림 게시 |
| Teams 채널 링크 | tenant, Team, channel 및 표시 이름 메타데이터 추출 |
| 부트스트랩 ID | App registration 생성 및 Graph application consent 부여 |

부트스트랩 ID에는 다음 최소 권한이 필요하다.

- tenant 정책에서 일반 사용자의 앱 등록을 허용하면 디렉터리 역할 불필요,
  그렇지 않으면 **Application Developer**
- 새 `TeamsNotifyApp`의 credential을 관리하기 위한 앱 소유권
- Microsoft Graph `GroupMember.ReadWrite.All` application permission에
  tenant-wide consent를 부여하기 위한 **Privileged Role Administrator**

가능하면 PIM을 사용해 부트스트랩할 때만 Privileged Role Administrator를
활성화한다. Flow 작성자에게는 Power Platform **Environment Maker**가
필요하다. Teams 연결 사용자는 Microsoft 365/Teams 및 Power Automate
라이선스가 필요하지만 Entra 관리자 역할은 필요하지 않다.

### 1단계: 프로젝트 설치

```shell
cp .env.example .env
chmod 600 .env

cd examples/python
uv sync --extra dev --python 3.12
cd ../..
```

Git에서 제외된 `.env`에는 로컬 credential이 저장된다. 이 파일을 커밋하거나
출력하거나 채팅 또는 issue에 첨부하지 않는다.

### 2단계: Teams 연결 사용자 및 채널 준비

1. 전용 `svc-teams-notification` 사용자를 생성하거나 지정한다.
2. tenant에서 요구하는 Microsoft 365/Teams 및 Power Automate 라이선스를
   할당한다.
3. 일반 사용자로 유지하고 Entra 관리자 역할을 부여하지 않는다.
4. Teams에서 최초 표준 채널을 열고 **기타 옵션** > **채널 링크
   가져오기**를 선택한 뒤
   `https://teams.cloud.microsoft/l/channel/...` 전체 링크를 보관한다.

채널 링크에는 tenant ID, Team 기반 Group ID, channel ID, channel name이
포함된다. PyHookKit은 이 값들을 검증하고 SQLite에 별도 컬럼으로 저장한다.

### 3단계: Power Automate Flow 생성 및 구성

1. [Power Automate](https://make.powerautomate.com)를 열고 대상 환경을
   선택한다.
2. **만들기**를 선택하고 빈 상태에서 자동화된 cloud Flow를 생성한다.
3. `PyHookKit Routed Teams Flow`처럼 환경 중립적인 이름을 사용한다.
4. **When a Teams webhook request is received** trigger를 추가한다.
5. 서명된 callback 모델을 사용하기 위해 **Who can trigger the flow?**를
   **Anyone**으로 설정한다.
6. Trigger 바로 다음에 **Post card in a chat or channel**을 추가한다.
7. **Change connection**에서 `svc-teams-notification`으로 로그인한다.
   **Connected to**에 표시되는 계정의 Team 접근 권한으로 action이
   실행된다.
8. Action을 다음과 같이 설정한다.

   | 필드 | 값 |
   |---|---|
   | **Post as** | `Flow bot` |
   | **Post in** | `Channel` |
   | **Team** | 사용자 지정 식 `triggerBody()?['teamId']` |
   | **Channel** | 사용자 지정 식 `triggerBody()?['channelId']` |
   | **Adaptive Card** | 식 `first(triggerBody()?['attachments'])?['content']` |

9. Flow를 저장한다.
10. Trigger를 다시 열고 모든 query parameter와 서명을 포함한 **HTTP
    URL** 전체를 복사한다.
11. 복구를 위해 이름이 명시된 Flow 공동 소유자를 최소 두 명 추가한다.
    공동 소유권은 Teams connection 실행 ID를 변경하지 않는다.

Adaptive Card 값으로 `triggerBody()`를 사용하면 안 된다. Trigger body는
Teams message envelope이며 첫 번째 attachment의 `content`만 카드다.

### 4단계: Workflow callback 저장

Callback URL 전체를 저장소 루트 `.env`에 추가한다.

```dotenv
TEAMS_WORKFLOW_URL="<서명된 Power Automate HTTP URL 전체>"
```

이 URL은 credential로 취급한다. 중앙 라우터 SQLite DB에는 callback 값이
아니라 환경변수 이름만 저장한다.

### 5단계: Azure Portal에 TeamsNotifyApp 등록

다음 단계의 자동 부트스트랩으로 앱을 생성할 수도 있다. Portal에서
소유권과 권한을 명시적으로 검토하려면 먼저 다음과 같이 생성한다.

1. **Microsoft Entra ID** > **App registrations** > **New registration**을
   연다.
2. 이름을 `TeamsNotifyApp`으로 설정한다.
3. **Accounts in this organizational directory only**를 선택한다.
4. Redirect URI는 비워 두고 **Register**를 선택한다.
5. **API permissions** > **Add a permission** > **Microsoft Graph** >
   **Application permissions**를 연다.
6. `GroupMember.ReadWrite.All`을 검색해 선택한다.
7. **Add permissions**를 선택한다.
8. **Privileged Role Administrator** 사용자가 **Grant admin consent for
   \<tenant\>**를 선택하고 승인한다.
9. **Owners**에 이름이 명시된 운영 소유자를 최소 두 명 추가한다.

필요한 멤버십 권한보다 범위가 큰 `Group.ReadWrite.All`은 추가하지 않는다.
외부 secret manager가 credential을 관리하는 경우가 아니라면 client
secret을 수동으로 생성하지 않는다. 부트스트랩 명령이 로컬 예제
credential을 생성하고 검증한 뒤 보호한다.

### 6단계: 앱과 최초 route 부트스트랩

부트스트랩 ID로 로그인한다. Azure subscription은 필요하지 않다.

```shell
az login \
  --tenant "<채널 링크의 tenant ID>" \
  --use-device-code \
  --allow-no-subscriptions
```

`examples/python`에서 실행한다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<최초 Teams 채널 링크>" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications
```

이 명령은 `TeamsNotifyApp`과 Service Principal을 생성하거나 재사용하고,
Graph app-role assignment를 검증하며, client credential을 생성 및
검증한다. 이어서 연결 사용자 object ID를 조회하고 생성된 값을 권한
`0600`의 `.env`에 기록하며, 사용자가 Team에 없을 때 추가하고, SQLite에
route를 저장한다. Secret 값은 출력하지 않는다.

자동 생성되는 값:

```dotenv
TEAMS_NOTIFY_TENANT_ID="<tenant GUID>"
TEAMS_NOTIFY_CLIENT_ID="<TeamsNotifyApp client GUID>"
TEAMS_NOTIFY_CLIENT_SECRET="<생성된 secret>"
TEAMS_CONNECTION_USER_ID="<연결 사용자 object GUID>"
```

### 7단계: Azure Portal 및 Power Automate 확인

**App registrations** > `TeamsNotifyApp`에서 다음을 확인한다.

- **API permissions**에 Microsoft Graph `GroupMember.ReadWrite.All`이
  **Application** permission으로 존재한다.
- 상태가 **Granted for \<tenant\>**다.
- 예상한 owner 및 credential만 존재한다.

**Enterprise applications** > `TeamsNotifyApp`에서 다음을 확인한다.

- Service Principal이 표시된다.
- 같은 application permission이 승인돼 있다.

Power Automate에서 다음을 확인한다.

- Flow가 활성화돼 있다.
- Teams action의 **Connected to**가 `svc-teams-notification`이다.
- Team, Channel, Adaptive Card 식이 3단계의 값과 정확히 일치한다.

### 8단계: 추가 채널 등록

명령은 `.env`를 불러오고 새 app-only Graph token을 발급하며, Team
멤버십을 보장하고 채널 메타데이터를 저장한다.

```shell
cd examples/python

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-example-channel \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "<추가 Teams 채널 링크>" \
  --ensure-team-membership
```

채널마다 고유한 target ID를 사용해 반복한다. 동일한 route를 사용하는
destination은 같은 알림을 서로 독립적으로 수신한다.

### 9단계: 진단 실행

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

정상 결과 예시:

```json
{
  "state": "healthy",
  "workflowUrl": "valid",
  "graphAppToken": "valid",
  "teamsDestinations": 2,
  "memberships": "verified",
  "databaseMode": "0600"
}
```

`doctor`는 callback 형식, app-only token, token tenant/client와 role,
활성화된 모든 Team의 멤버십, SQLite 권한을 검증한다. 알림은 보내지
않는다.

### 10단계: End-to-end 테스트 전송

터미널 1에서 `examples/python`으로 이동한 뒤 실행한다.

```shell
export PYHOOKKIT_LOCAL_ROUTER_TOKEN="$(
  python -c 'import secrets; print(secrets.token_urlsafe(32))'
)"

uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  serve \
  --producer local=PYHOOKKIT_LOCAL_ROUTER_TOKEN
```

터미널 2에서 같은 token을 사용한다.

```shell
cd examples/python
export NOTIFICATION_ROUTER_URL="http://127.0.0.1:8080"
export NOTIFICATION_ROUTER_TOKEN="<동일한 로컬 라우터 token>"

uv run python -m pyhookkit.entrypoints.notification_router_client \
  --producer local \
  --input ../../contracts/test-vectors/scenarios/deployment-result/notification.json
```

제출 명령은 `202`에 해당하는 `queued` 상태와 notification ID를 반환한다.
최종 상태를 조회한다.

```shell
curl --fail --silent \
  -H "X-PyHookKit-Producer: local" \
  -H "Authorization: Bearer $NOTIFICATION_ROUTER_TOKEN" \
  "$NOTIFICATION_ROUTER_URL/v1/notifications/<notification ID>"
```

`delivered`와 destination마다 하나의 `succeeded` 항목을 확인한다. Power
Automate에서는 destination별로 하나의 실행이 성공했는지, Teams에서는
설정된 모든 채널에 카드가 정확히 한 번 표시되는지 확인한다.

Secret 회전, 장애 복구 및 제거 방법은 [TeamsNotifyApp 한국어 부트스트랩
가이드](docs/teams-notify-app-bootstrap.ko.md)를 참고한다.

### 예제 범위

| 예제 | Slack | Microsoft Teams |
|---|---|---|
| [F00 Raw HTTP request](examples/python/fundamentals/00_http_request) | 표준 라이브러리 webhook POST | 표준 라이브러리 Workflow POST |
| [F01 Hello World](examples/python/fundamentals/01_hello_world) | 최소 text payload | 최소 Adaptive Card |
| [F02 Basic notification](examples/python/fundamentals/02_basic_notification) | 제목, 본문, 심각도, timestamp | Adaptive Card 제목, 본문, 심각도, timestamp |
| [F03 Rich card](examples/python/fundamentals/03_rich_card) | Block Kit fact와 context | Adaptive Card fact panel과 context |
| [F04 Mention](examples/python/fundamentals/04_mention) | 네이티브 사용자 및 사용자 그룹 멘션 | 네이티브 사용자 멘션, 그룹 확장에는 Graph 설정 필요 |
| [F05 Link and action](examples/python/fundamentals/05_link_and_action) | Block Kit URL button | `Action.OpenUrl` |
| [F06 Image](examples/python/fundamentals/06_image) | 대체 텍스트가 있는 외부 이미지 block | 대체 텍스트가 있는 Adaptive Card 이미지 |
| [F07 Routing](examples/python/fundamentals/07_routing) | 논리적 route를 webhook으로 해석 | 논리적 route를 Workflow로 해석 |
| [F08 Thread or reply](examples/python/fundamentals/08_thread_or_reply) | 알려진 부모 `thread_ts` | 명시적인 새 메시지 fallback, 답글에는 bot 또는 Graph 필요 |
| [F09 Update and delete](examples/python/fundamentals/09_update_and_delete) | Web API 변경 payload | 명시적인 unsupported 안내, bot 또는 Graph 필요 |
| [F10 Error and retry](examples/python/fundamentals/10_error_and_retry) | 삭제된 민감 정보와 제한된 재시도 | 삭제된 민감 정보와 제한된 재시도 |
| [Deployment result](examples/python/scenarios/deployment_result) | 쌍을 이루는 Block Kit 시나리오 | 쌍을 이루는 Adaptive Card 시나리오 |
| [Incident alert and acknowledgment](examples/python/scenarios/incident_alert_acknowledgment) | 네이티브 사용자 그룹 멘션과 링크 2개 | 그룹 설정 안내와 `Action.OpenUrl` action 2개 |
| [Approval request](examples/python/scenarios/approval_request) | 네이티브 사용자 멘션과 검토 링크 | 네이티브 사용자 mention entity와 검토 action |
| [Maintenance notice](examples/python/scenarios/maintenance_notice) | 네이티브 사용자 그룹 멘션과 상태 링크 | 그룹 설정 안내와 상태 action |

## 클라이언트 스크린샷

`examples/python/teams_adaptive_cards/assets/`의 PNG 파일은 카드 콘텐츠이며
클라이언트 캡처가 아니다. 실제 Slack 또는 Teams 클라이언트 캡처만
[`docs/assets/card-previews/`](docs/assets/card-previews/README.md)에
추가한다. 이 갤러리를 합성 HTML이나 renderer preview로 채우지 않는다.

| 예제 | Slack | Microsoft Teams |
|---|---|---|
| [F01 Hello World](examples/python/fundamentals/01_hello_world) | <img src="./docs/assets/card-previews/hello-world-slack.png" alt="Slack Hello World 알림"> | <img src="./docs/assets/card-previews/hello-world-teams.png" alt="Microsoft Teams Hello World 알림"> |
| [F02 Basic notification](examples/python/fundamentals/02_basic_notification) | <img src="./docs/assets/card-previews/basic-notification-slack.png" alt="Slack 기본 알림"> | <img src="./docs/assets/card-previews/basic-notification-teams.png" alt="Microsoft Teams 기본 알림"> |
| [F03 Rich card](examples/python/fundamentals/03_rich_card) | <img src="./docs/assets/card-previews/rich-card-slack.png" alt="Slack rich card 알림"> | <img src="./docs/assets/card-previews/rich-card-teams.png" alt="Microsoft Teams rich card 알림"> |
| [F04 Mention](examples/python/fundamentals/04_mention) | <img src="./docs/assets/card-previews/mention-slack.png" alt="Slack 멘션 알림"> | <img src="./docs/assets/card-previews/mention-teams.png" alt="Microsoft Teams 멘션 알림"><ul><li><sub>그룹 알림에는 추가 Microsoft Graph 멤버 확장 설정이 필요하다.</sub></li><li><sub>논리적 alias를 대입하면 멘션 대상을 잘못 표시할 수 있으므로 Teams는 설정된 사용자 이름을 표시한다.</sub></li></ul> |
| [F05 Link and action](examples/python/fundamentals/05_link_and_action) | <img src="./docs/assets/card-previews/link-and-action-slack.png" alt="Slack 링크 및 action 알림"> | <img src="./docs/assets/card-previews/link-and-action-teams.png" alt="Microsoft Teams 링크 및 action 알림"> |
| [F06 Image](examples/python/fundamentals/06_image) | <img src="./docs/assets/card-previews/image-slack.png" alt="Slack 이미지 알림"> | <img src="./docs/assets/card-previews/image-teams.png" alt="Microsoft Teams 이미지 알림"> |
| [F07 Routing](examples/python/fundamentals/07_routing) | <img src="./docs/assets/card-previews/route-slack.png" alt="Slack route 알림"> | <img src="./docs/assets/card-previews/route-teams.png" alt="Microsoft Teams route 알림"> |
| [Deployment result](examples/python/scenarios/deployment_result) | _스크린샷 준비 중: `deployment-result-slack.png`_ | <img src="./docs/assets/card-previews/deployment-result-teams.png" alt="Microsoft Teams Bookinfo 배포 결과"> |
| [Incident alert and acknowledgment](examples/python/scenarios/incident_alert_acknowledgment) | _스크린샷 준비 중: `incident-alert-acknowledgment-slack.png`_ | <img src="./docs/assets/card-previews/incident-alert-acknowledgment-teams.png" alt="Microsoft Teams Bookinfo incident 알림"> |
| [Approval request](examples/python/scenarios/approval_request) | _스크린샷 준비 중: `approval-request-slack.png`_ | <img src="./docs/assets/card-previews/approval-request-teams.png" alt="Microsoft Teams Bookinfo 배포 승인 요청"> |
| [Maintenance notice](examples/python/scenarios/maintenance_notice) | _스크린샷 준비 중: `maintenance-notice-slack.png`_ | <img src="./docs/assets/card-previews/maintenance-notice-teams.png" alt="Microsoft Teams 예정된 maintenance 알림"> |

## 저장소 구조

- [`contracts/`](contracts/README.md): 언어 중립 schema와 공급자 쌍 test vector
- [`docs/`](docs/README.md): 공개 사용법, 아키텍처, 보안 및 마이그레이션
  가이드
- [`examples/`](examples/README.md): 참조 구현과 예제
- [`infra/`](infra/README.md): 공급자 설정, runtime 인프라, 통합 및 정책 검사

예제는 capability 또는 scenario별로 구성한다. 동등성이 완성된 경우 Slack과
Teams entrypoint는 형제 파일이며 동일한 canonical notification을 사용한다.

사용자 대상 문서, 인프라, 테스트 및 실행 가능한 예제 디렉터리는 모두
README entrypoint를 갖는다. Source package 디렉터리, 고정된 fixture leaf
디렉터리, 생성된 cache 및 중첩된 이미지 전용 asset 디렉터리는 로컬 파일을
중복 생성하지 않고 가장 가까운 상위 README에서 설명한다.

## 로컬 설정

`.env.example`을 Git에서 제외된 `.env`로 복사한 후 합성 테스트 destination을
위한 Slack Incoming Webhook URL과 Teams Workflow callback URL을 추가한다.
정확한 값과 설정 단계는 [공급자 설정](docs/configuration.md)을, F01-F10
목록은 [Slack 예제](docs/slack-examples.md)를 참고한다.

## 상태

Python 배포 이름과 import namespace는 모두 `pyhookkit`이다. 아직 PyPI에
배포되지 않았다.

Slack과 Teams의 기본 capability 및 scenario 예제가 완성돼 있다. Teams
Workflow에 동등한 기능이 없는 경우 공급자 차이를 명시한다. 커밋된 모든
값은 합성 값이며, runtime credential과 실제 destination 설정은 저장소
외부에 둔다.

서드파티 예제 asset과 라이선스는
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)에 정리돼 있다.
