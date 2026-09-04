# TeamsNotifyApp 부트스트랩

[English](teams-notify-app-bootstrap.md)

`TeamsNotifyApp`은 중앙 라우터에 등록된 Team에 Power Automate 전용 Teams
연결 사용자가 소속돼 있는지 보장하기 위한 단일 테넌트 Entra
애플리케이션이다. Azure Portal의 App registrations와 Enterprise
applications에서 명시적으로 확인하고 관리할 수 있다.

이 앱은 저장된 Azure CLI delegated access token을 대체한다. 중앙 라우터는
Team 멤버십을 등록할 때마다 client credentials로 수명이 짧은 Microsoft
Graph app-only token을 발급한다.

## ID와 권한 경계

부트스트랩을 단순하게 만들기 위해 다음 ID를 하나로 합치지 않는다.

| ID | 책임 | 최소 권한 |
|---|---|---|
| 부트스트랩 앱 생성자 | `TeamsNotifyApp`, Service Principal, client credential 생성 | 테넌트 정책에서 일반 사용자의 앱 등록을 허용하면 디렉터리 역할 불필요, 그렇지 않으면 **Application Developer** |
| 동의 승인자 | Microsoft Graph application permission인 `GroupMember.ReadWrite.All` 승인 | **Privileged Role Administrator**, 가능하면 PIM으로 부트스트랩할 때만 활성화 |
| Flow 작성자 | Power Automate Flow 생성과 Teams connection 연결 | 대상 Power Platform 환경의 **Environment Maker** |
| Teams 연결 사용자 | Teams connector 승인과 카드 전송 | Microsoft 365/Teams 및 Power Automate 라이선스, Entra 관리자 역할 불필요 |
| TeamsNotifyApp runtime | 명시적으로 등록된 Team의 기반 Group에 Teams 연결 사용자 추가 | Microsoft Graph application permission `GroupMember.ReadWrite.All` |
| 알림 생산자 | canonical notification 제출 | 생산자별 중앙 라우터 bearer token만 필요 |

테넌트 정책에서 일반 사용자의 애플리케이션 등록을 허용하면 부트스트랩
앱 생성자는 새 앱의 소유자가 되며 해당 앱의 credential을 관리할 수 있다.
소유자가 아닌 별도 운영자가 앱을 관리해야 할 때만 **Cloud Application
Administrator**가 필요하다.

Microsoft Graph application role에는 테넌트 전체 admin consent가 필요하다.
**Privileged Role Administrator**는 Microsoft Graph application permission
동의를 부여할 수 있는 최소 기본 제공 역할이다. Global Administrator도
가능하지만 일상적인 부트스트랩 역할로 권장하지 않는다.

현재 단일 명령 부트스트랩은 실행 사용자가 앱 등록 권한과 활성화된
Privileged Role Administrator 역할을 모두 갖고 있다고 가정한다. 조직에서
두 책임을 분리할 수 있지만, app-only token을 검증하기 전에 동의 승인자가
admin consent를 완료해야 한다.

공식 참고 문서:

- [작업별 최소 권한 역할](https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-by-task)
- [테넌트 전체 admin consent 부여](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent)
- [Application 및 Service Principal 객체](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals)
- [Microsoft 365 Group에 멤버 추가](https://learn.microsoft.com/graph/api/group-post-members?view=graph-rest-1.0)
- [Microsoft Graph 권한 참고](https://learn.microsoft.com/graph/permissions-reference)

## 수동 사전 준비

1. Power Automate Flow를 빈 Flow로 생성한다.
2. **When a Teams webhook request is received** trigger를 사용한다.
3. **Post card in a chat or channel**을 다음과 같이 설정한다.
   - **Post as**: `Flow bot`
   - **Post in**: `Channel`
   - **Team**: `triggerBody()?['teamId']`
   - **Channel**: `triggerBody()?['channelId']`
   - **Adaptive Card**:
     `first(triggerBody()?['attachments'])?['content']`
4. 전용 `svc-teams-notification` 계정으로 로그인해 Microsoft Teams
   connection을 생성한다.
5. 생성된 callback URL 전체를 Git에서 제외된 저장소 루트 `.env`에
   저장한다.

   ```dotenv
   TEAMS_WORKFLOW_URL="<서명이 포함된 callback URL 전체>"
   ```

Power Automate connection 승인은 MFA와 Conditional Access를 요구할 수
있으므로 대화형 단계로 유지한다. 앱 부트스트랩으로 사용자 Teams
connection을 application authentication으로 변경할 수는 없다.

## 부트스트랩

부트스트랩 및 동의 권한이 있는 ID로 한 번 로그인한다.

```shell
az login \
  --tenant "<채널 테넌트 GUID>" \
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

이 명령은 다음 작업을 자동으로 수행한다.

1. 채널 링크에서 tenant, Team, channel, 표시 이름을 추출한다.
2. Azure CLI가 해당 tenant의 Graph token을 발급할 수 있는지 확인한다.
3. `TeamsNotifyApp`을 생성하거나 이름이 정확히 일치하는 기존 앱 하나를
   재사용한다.
4. 해당 tenant의 Service Principal을 생성하거나 재사용한다.
5. 권한 GUID를 하드코딩하지 않고 현재 Microsoft Graph app-role ID를
   조회한다.
6. `GroupMember.ReadWrite.All`을 앱에 구성한다.
7. Service Principal app-role assignment를 직접 생성하고 다시 조회해
   admin consent가 실제로 저장됐는지 확인한다.
8. Teams connection 사용자를 Entra object ID로 변환한다.
9. 재사용할 수 있는 로컬 credential이 없으면 1년 client secret을
   생성한다.
10. client-credentials token의 tenant, client ID, `roles`를 검증한다.
11. 생성된 값을 저장소 루트 `.env`에 원자적으로 기록하고 권한을
    `0600`으로 설정한다.
12. Teams connection 사용자를 Team의 기반 Microsoft 365 Group에
    멱등적으로 추가한다.
13. SQLite에 route를 저장한다.

credential 생성 후 token 검증이나 `.env` 저장이 실패하면 새 credential을
자동으로 삭제한다. client secret 값은 출력하지 않는다.

자동 생성되는 설정:

```dotenv
TEAMS_NOTIFY_TENANT_ID="<tenant GUID>"
TEAMS_NOTIFY_CLIENT_ID="<TeamsNotifyApp client GUID>"
TEAMS_NOTIFY_CLIENT_SECRET="<생성된 secret>"
TEAMS_CONNECTION_USER_ID="<connection 사용자 object GUID>"
```

tenant ID는 채널 링크에서 얻는다. 서비스 사용자 object ID는 부트스트랩
중 한 번만 조회해 저장하므로 TeamsNotifyApp runtime에 테넌트 전체 사용자
조회 권한을 부여할 필요가 없다.

## Portal 확인

Microsoft Entra 관리 센터에서 다음을 확인한다.

1. **App registrations**에서 `TeamsNotifyApp`을 선택한다.
2. **API permissions**에서 Microsoft Graph의
   `GroupMember.ReadWrite.All`이 **Application** permission인지 확인한다.
3. 상태가 **Granted for \<tenant\>**인지 확인한다.
4. **Enterprise applications**에서 `TeamsNotifyApp`을 선택한다.
5. **Permissions**에서 같은 application permission을 확인한다.
6. **Owners**에 이름이 명시된 운영 소유자를 최소 두 명 유지한다.
7. **Certificates & secrets**에서 예상한 PyHookKit credential만 남아
   있는지 확인한다.

Teams connection 사용자는 별도 ID다. Power Automate의 Teams action
하단 **Connected to**가 해당 서비스 계정인지 확인한다.

## 채널 추가

저장소 `.env`는 자동으로 로드된다. Graph access token을 직접 복사하거나
export할 필요가 없다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  add-destination \
  --target-id teams-example-channel \
  --route release-notifications \
  --provider teams-workflow \
  --endpoint-env TEAMS_WORKFLOW_URL \
  --channel-link "<Teams 채널 링크>" \
  --ensure-team-membership
```

등록 과정은 다른 tenant의 링크를 거부하고, 새 app-only token을 발급하며,
기존 멤버십을 확인한다. 사용자가 없을 때만 일반 Group 멤버로 추가하므로
명령을 반복해도 안전하다.

표준 채널은 Team 멤버십을 따른다. 비공개 및 공유 채널에는 명시적인 채널
멤버십이 추가로 필요할 수 있다. 이 구성에서는 비공개 채널에 Flow bot으로
전송하는 기능을 지원하지 않는다.

## 진단

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

정상 결과는 다음 항목이 유효함을 의미한다.

- Workflow URL
- client-credentials token 발급
- token의 tenant 및 client ID
- 필요한 Graph application role
- 활성화된 모든 Teams destination의 서비스 계정 멤버십
- SQLite 파일 권한 `0600`

`doctor`는 알림을 전송하지 않으며 credential을 출력하지 않는다.

## Client secret 회전

다음과 같이 bootstrap을 다시 실행한다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<기존 Teams 채널 링크>" \
  --connection-user "svc-teams-notification@example.com" \
  --target-id teams-example-channel \
  --rotate-secret
```

bootstrap과 `doctor`가 성공하면 Entra에서 이전 credential을 삭제한다.
새 app-only token이 검증되기 전까지는 작동하는 credential을 최소 하나
유지한다.

## 장애 복구 및 제거

- App token 발급이 `401`을 반환하면 client credential을 회전한다.
- Token에 `roles`가 없으면 Service Principal app-role assignment와
  tenant-wide admin consent를 확인한다.
- 멤버십 작업이 `403`을 반환하면 `GroupMember.ReadWrite.All` 동의를
  확인한다.
- 멤버십은 성공하지만 Teams 게시가 실패하면 Power Automate Teams
  connection을 다시 승인하고 서비스 계정으로 연결됐는지 확인한다.
- TeamsNotifyApp을 삭제하기 전에 멤버십 자동 등록을 중지하고,
  부트스트랩이나 복구 절차에서 해당 앱을 사용하지 않는지 확인한다.
- App Registration을 삭제하면 Service Principal과 credential도 제거된다.
  그 후 `.env`에서 자동 생성된 앱 및 연결 사용자 값 네 개를 삭제한다.
