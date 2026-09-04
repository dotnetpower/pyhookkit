# 공급자 구성

[English](configuration.md)

이 저장소는 공급자 대상 자격 증명을 위해 하나의 로컬 환경 파일을
사용합니다.

```shell
cp .env.example .env
```

서명된 URL에는 `&` 같은 셸 문자가 포함될 수 있으므로 각 URL을 큰따옴표
안에 두십시오. 커밋된 `.env.example`은 변수 계약이며, 무시되는 `.env`만
실제 값을 포함할 수 있는 유일한 로컬 파일입니다.

## Slack

다음을 설정합니다.

```dotenv
SLACK_WEBHOOK_URL="<Slack Incoming Webhook URL>"
```

다음이 필요합니다.

1. 관리자가 앱 설치를 허용하는 Slack 워크스페이스
2. 테스트용 합성 채널
3. **Incoming Webhooks**가 활성화된 Slack 앱
4. 워크스페이스에 설치 또는 재설치되고 테스트 채널에 대해 승인된 앱
5. 해당 채널에 발급된 Incoming Webhook URL

현재 Slack UI에서 앱을 생성합니다.

1. [Slack 앱 관리 페이지](https://api.slack.com/apps)를 열고
   **Create an app**을 선택합니다.
2. **Create new app**에서 **Or start your own way** 아래의 **Blank app**을
   선택한 다음 **Continue**를 선택합니다.
3. `PyHookKit Sandbox` 같은 합성 이름을 입력하고 개발 워크스페이스를
   선택한 뒤 앱을 생성합니다.
4. 앱 설정 사이드바에서 **Incoming Webhooks**를 선택합니다.
5. **Activate Incoming Webhooks**를 켭니다.
6. **Add New Webhook to Workspace**를 선택하고 합성 테스트 채널을 고른
   다음 설치를 승인합니다.
7. **Webhook URLs for Your Workspace** 아래에서 생성된 URL을 복사합니다.

이전 Slack 안내에서는 **Blank app**을 **From scratch**라고 부를 수
있습니다. 둘 다 동일한 최소 앱 생성 경로를 의미합니다. 이 예제에서는
**AI agent** 또는 **Starter app**을 선택하지 마세요.

발급된 전체 URL을 `SLACK_WEBHOOK_URL`에 복사합니다. Incoming Webhook은
선택한 워크스페이스와 대상에 바인딩됩니다. 따라서 이 초기 환경 계약에는
채널 이름이나 Slack 채널 ID가 필요하지 않습니다.

### 고급 Slack 예제

부모 메시지 타임스탬프를 이미 알고 있으면 F08은 스레드 Webhook 메시지를
렌더링할 수 있습니다. F09는 Web API 업데이트 및 삭제 페이로드를
보여줍니다. 실제 Web API 전송에는 다음도 필요합니다.

```dotenv
SLACK_BOT_TOKEN="<Bot User OAuth Token>"
SLACK_APP_TOKEN="<Socket Mode app-level token>"
SLACK_SIGNING_SECRET="<Slack app signing secret>"
SLACK_CHANNEL_ID="<Slack channel ID>"
SLACK_TEST_DISPLAY_NAME="<test member display name>"
SLACK_USER_ID="<test Slack member ID>"
SLACK_USER_GROUP_ID="<test Slack user-group ID>"
```

- 앱을 설치하거나 재설치한 후 **OAuth & Permissions → OAuth Tokens for Your
  Workspace**에서 봇 토큰을 찾습니다. 일반적으로 `xoxb-`로 시작합니다.
  비밀 정보로 취급하세요.
- 테스트하는 작업에 필요한 범위만 추가합니다. 전체 합성 매니페스트에는
  `chat:write`, `channels:read`, `groups:read`, `users:read`,
  `usergroups:read`, `files:write`, `reactions:write`,
  `app_mentions:read`가 포함됩니다. 이벤트 예제는 `reactions:read`,
  `channels:history`, `groups:history`도 사용합니다.
- 채널 세부 정보 UI에서 채널 ID를 확인합니다. 채널 ID는 비밀 정보가 아닌
  환경 구성이지만 정규 알림 계약에 포함되어서는 안 됩니다.
- 스레드, 업데이트 또는 삭제 작업의 대상을 지정하려면
  `chat.postMessage`가 반환한 메시지 `ts`를 보관합니다. Incoming Webhook의
  성공 응답 본문은 이 식별자를 반환하지 않습니다.
- F04는 `--send`를 사용할 때만 테스트 멤버 ID와 테스트 사용자 그룹 ID가
  필요합니다. 렌더링에는 합성 식별자가 사용됩니다.
- O02는 이메일 접근을 요청하지 않고 `SLACK_TEST_DISPLAY_NAME`으로 테스트
  멤버를 찾을 수 있습니다. 표시 이름은 활성 상태인 봇이 아닌 멤버
  정확히 한 명으로 확인되어야 합니다.
- HTTP 상호 작용과 Events API 예제에는 서명 비밀이 필요합니다. 더 이상
  사용되지 않는 확인 토큰을 대신 사용하지 마세요.
- Socket Mode에는 `connections:write`가 있는 앱 수준 토큰이 필요합니다.
  해당 값은 일반적으로 `xapp-`로 시작하며 Web API 쓰기에는 여전히 봇
  토큰을 사용합니다.

F08-F09는 합성 페이로드를 렌더링하며 Web API 요청을 수행하지 않습니다.
`slack_operations` 예제에서 실제 Web API 수명 주기를 제공합니다.

[Slack Incoming Webhooks 문서](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)를
사용하여 Incoming Webhook을 생성하고 관리하세요.

## Microsoft Teams

다음을 설정합니다.

```dotenv
TEAMS_WORKFLOW_URL="<Teams Workflow HTTP POST callback URL>"
TEAMS_WORKFLOW_CHANNEL_LINK="<exact approved Microsoft Teams channel link>"
TEAMS_LOGIC_APP_URL="<Azure Logic App HTTP trigger callback URL>"
TEAMS_LOGIC_APP_TEAM_ID="<Microsoft Teams team ID>"
TEAMS_LOGIC_APP_CHANNEL_ID="<Microsoft Teams channel ID>"
EXAMPLE_ASSET_BASE_URL="<direct HTTPS base URL for committed example images>"
TEAMS_ASSET_BASE_URL="<legacy fallback; leave blank for new configuration>"
TEAMS_TEST_USER_ID="<test member Microsoft Entra object ID or UPN>"
TEAMS_TEST_USER_NAME="<test member display name>"
TEAMS_NOTIFY_TENANT_ID="<TeamsNotifyApp tenant GUID>"
TEAMS_NOTIFY_CLIENT_ID="<TeamsNotifyApp application/client GUID>"
TEAMS_NOTIFY_CLIENT_SECRET="<TeamsNotifyApp client secret>"
TEAMS_CONNECTION_USER_ID="<dedicated Teams connection user object GUID>"
NOTIFICATION_ROUTER_URL="<central router HTTPS base URL>"
NOTIFICATION_ROUTER_TOKEN="<producer-specific router bearer token>"
```

다음이 필요합니다.

1. Teams에서 Workflows를 생성할 수 있는 Microsoft 365 계정
2. 테스트용 합성 팀과 채널
3. Teams Webhook 트리거와 요청 본문에서 `teamId`, `channelId` 및 첫 번째
   첨부 파일의 Adaptive Card 콘텐츠를 읽는 동적 게시 작업을 사용하여
   빈 상태에서 생성한 Power Automate 흐름 하나
4. 대상 팀의 멤버인 전용 라이선스 Microsoft 365 사용자가 소유한 승인된
   Teams 연결
5. 공유 또는 프로덕션 환경에서 서비스 주체가 소유할 수 있게 해 주는
   Dataverse 애플리케이션 사용자와 이름이 지정된 운영 공동 소유자 최소
   두 명
6. Workflow를 저장한 후 생성된 HTTP POST 콜백 URL

두 `NOTIFICATION_ROUTER_*` 값은 선택 사항입니다. 생산자가
[중앙 알림 라우터](central-notification-router.ko.md)를 통해 정규 JSON을
제출할 때만 구성하세요. 모든 생산자는 서로 다른 토큰을 사용해야 합니다.

`TEAMS_NOTIFY_*` 및 연결 사용자에 해당하는 네 값은 수동으로 생성하지
마세요.
중앙 라우터의 `bootstrap-teams-app` 명령은 표시되는 단일 테넌트 앱을
생성하거나 재사용하고, 앱 전용 토큰을 검증하고, 사용자를 확인한 뒤 모드
`0600`으로 `.env`에 값을 씁니다. 런타임 등록은 수명이 짧은 Graph 토큰을
자동으로 가져오며 액세스 토큰을 영구 저장하지 않습니다.

생성된 전체 콜백 URL을 `TEAMS_WORKFLOW_URL`에 복사하고, 허용 목록에 있는
정확한 Teams 채널 링크를 `TEAMS_WORKFLOW_CHANNEL_LINK`에 복사합니다. 모든
승인된 대상이 콜백을 공유합니다. 직접 실행하는 예제는 구성된 링크에서 팀
및 채널 ID를 파생합니다. 반면 중앙 라우터는 링크와 링크에서 파생된
메타데이터를 SQLite에 영구 저장합니다.

Azure Logic App 전송의 경우 서명된 HTTP 트리거 URL을 명시적인 팀 및 채널
ID와 별도로 구성합니다. [Logic App Teams 전송 가이드](logic-app-teams-delivery.ko.md)를
따르십시오. 요청 스키마가 다르므로 Logic App 콜백으로
`TEAMS_WORKFLOW_URL`을 대체할 수 없습니다.

공급자 중립적 자산 기본 URL은 이미지 중심의 쌍을 이루는 시나리오와 독립 실행형
Adaptive Card 예제에서 Workflow 및 Logic App 전송 모두에 사용됩니다.
`EXAMPLE_ASSET_BASE_URL`이 비어 있을 때만 호환되는 대체 값으로
`TEAMS_ASSET_BASE_URL`을 읽습니다. 두 `TEAMS_TEST_*` 값은 선택 사항이며
독립 실행형 멘션 예제에서만 사용됩니다. 공유 프로덕션 알림 구성에는 이러한
예제 값을 설정하지 마세요.

[Power Automate Teams Workflow 가이드](power-automate-teams-workflow.ko.md)를
사용하여 빈 상태에서 흐름을 생성하고 스모크 테스트하세요.
Solution 배포, 서비스 주체 소유권 및 채널 접근 도구는
[Teams Workflows 런북](../infra/teams-workflows/README.md)에 있습니다.

반복되는 환경에서는 Power Platform CLI로 검증된 흐름을 Power Platform
Solution으로 배포하고 관리 API를 통해 각 환경의 콜백 URL을 가져옵니다.
한 환경의 서명된 URL을 다른 환경에 복사하거나 Solution 소스에 저장하지
마세요.

## 파일 로드

저장소 루트에서 현재 셸로 값을 로드합니다.

```shell
set -a
. ./.env
set +a
```

자격 증명을 출력하지 않고 값이 존재하는지 확인합니다.

```shell
test -n "$SLACK_WEBHOOK_URL" && echo "Slack destination configured"
test -n "$TEAMS_WORKFLOW_URL" && echo "Teams destination configured"
test -n "$TEAMS_WORKFLOW_CHANNEL_LINK" && echo "Teams channel route configured"
test -n "$TEAMS_LOGIC_APP_URL" && echo "Teams Logic App configured"
```

기본 예제는 기본적으로 페이로드를 렌더링합니다. Slack 작업도 기본적으로
드라이 런이며 네트워크 작업 전에 명시적인 `--live`, `--send`,
`--exercise`, `--upload`, `--serve` 또는 `--listen-once` 플래그가
필요합니다. 엔트리포인트는 컴포지션 경계에서 변수를 읽으며 도메인 및
애플리케이션 코드는 `.env`를 직접 읽지 않습니다.

## 보안 및 교체

- 테스트 채널을 대상으로 하더라도 두 URL을 모두 자격 증명으로 취급합니다.
- 어떤 값도 소스, 테스트, 픽스처, 스크린샷, 로그, 명령 기록, 이슈 또는
  풀 리퀘스트에 붙여 넣지 마세요.
- 디버깅이나 CI 중에 환경 값을 출력하지 마세요.
- URL이 노출되면 Slack Webhook을 취소 또는 교체하거나 Teams Workflow
  콜백 URL을 다시 생성한 다음 승인된 비밀 저장소를 업데이트하세요.
- 프로덕션 배포에서는 `.env`를 복사하는 대신 비밀 관리자를 통해 동일한
  변수를 주입해야 합니다.
- 구체적인 고급 어댑터에 필요한 경우에만 봇 토큰, OAuth 자격 증명, 테넌트
  ID 또는 클라이언트 자격 증명을 추가하세요.
