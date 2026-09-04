# TeamsNotifyApp 부트스트랩

[English](teams-notify-app-bootstrap.md)

`TeamsNotifyApp`은 중앙 라우터에 등록된 Team에 Power Automate 전용 Teams
연결 사용자가 소속돼 있는지 보장하기 위한 단일 테넌트 Entra
애플리케이션입니다. Azure Portal의 **App registrations**와 **Enterprise
applications**에서 명시적으로 확인하고 관리할 수 있습니다.

이 앱은 저장된 Azure CLI 위임 액세스 토큰을 대체합니다. 중앙 라우터는
Team 멤버십을 등록할 때마다 클라이언트 자격 증명으로 수명이 짧은 Microsoft
Graph 앱 전용 토큰을 발급합니다.

`TeamsNotifyApp`은 Azure 구독에 생성되는 Azure 리소스가 아닙니다. 대상
Team과 채널을 소유한 Microsoft 365 테넌트와 동일한 Microsoft Entra
테넌트의 앱 등록 및 서비스 주체입니다. "Microsoft 365 사용자"는 같은
Entra 테넌트의 사용자에게 Teams 라이선스를 할당한 계정이며 별도의 사용자
디렉터리가 아닙니다. Azure CLI 로그인은 이 Entra 테넌트를 대상으로 하며,
Azure 구독 또는 Azure RBAC 역할은 필요하지 않습니다.

## ID와 권한 경계

부트스트랩을 단순화하기 위해 다음 ID를 하나로 합치지 마세요.

| ID | 책임 | 최소 권한 |
|---|---|---|
| 부트스트랩 앱 생성자 | `TeamsNotifyApp`, 서비스 주체 및 클라이언트 자격 증명 생성 | 테넌트 정책에서 일반 사용자의 앱 등록을 허용하면 디렉터리 역할이 필요하지 않습니다. 허용하지 않으면 **Application Developer**가 필요합니다. |
| 동의 승인자 | Microsoft Graph 애플리케이션 권한 `GroupMember.ReadWrite.All` 승인 | **Privileged Role Administrator**. 가능하면 부트스트랩할 때만 PIM으로 활성화합니다. |
| 흐름 작성자 | Power Automate 흐름 생성 및 Teams 연결 바인딩 | 대상 Power Platform 환경의 **Environment Maker** |
| Teams 연결 사용자 | Teams 커넥터 승인 및 카드 전송 | Microsoft 365/Teams 및 Power Automate 라이선스. Entra 관리자 역할은 필요하지 않습니다. |
| `TeamsNotifyApp` 런타임 | 명시적으로 등록된 Team의 기반 그룹에 Teams 연결 사용자 추가 | Microsoft Graph 애플리케이션 권한 `GroupMember.ReadWrite.All` |
| 알림 생산자 | 정규 알림 제출 | 생산자별 중앙 라우터 전달자 토큰만 필요 |

테넌트 정책에서 일반 사용자의 애플리케이션 등록을 허용하면 부트스트랩
앱 생성자는 새 앱의 소유자가 되며 해당 앱의 자격 증명을 관리할 수 있습니다.
소유자가 아닌 별도 운영자가 앱을 관리해야 할 때만 **Cloud Application
Administrator**가 필요합니다.

Microsoft Graph 애플리케이션 역할에는 테넌트 전체 관리자 동의가
필요합니다. **Privileged Role Administrator**는 Microsoft Graph
애플리케이션 권한 동의를 부여할 수 있는 최소 기본 제공 역할입니다. Global
Administrator도 사용할 수 있지만 일상적인 부트스트랩 역할로 권장하지
않습니다.

현재 단일 명령 부트스트랩은 실행 사용자가 앱 등록 권한과 활성화된
Privileged Role Administrator 역할을 모두 가지고 있다고 가정합니다.
조직에서 두 책임을 분리할 수 있지만, 앱 전용 토큰을 검증하기 전에 동의
승인자가 관리자 동의를 완료해야 합니다.

공식 참고 문서:

- [작업별 최소 권한 역할](https://learn.microsoft.com/entra/identity/role-based-access-control/delegate-by-task)
- [테넌트 전체 관리자 동의 부여](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent)
- [애플리케이션 및 서비스 주체 개체](https://learn.microsoft.com/entra/identity-platform/app-objects-and-service-principals)
- [Microsoft 365 그룹에 멤버 추가](https://learn.microsoft.com/graph/api/group-post-members?view=graph-rest-1.0)
- [Microsoft Graph 권한 참고](https://learn.microsoft.com/graph/permissions-reference)

## 수동 사전 준비

**실행 주체:** 대상 Power Platform 환경의 흐름 작성자와 Teams 연결
사용자입니다.

1. Power Automate 흐름을 빈 상태에서 생성합니다.
2. **When a Teams webhook request is received** 트리거를 사용합니다.
3. **Post card in a chat or channel**을 다음과 같이 설정합니다.
   - **Post as**: `Flow bot`
   - **Post in**: `Channel`
   - **Team**: `triggerBody()?['teamId']`
   - **Channel**: `triggerBody()?['channelId']`
   - **Adaptive Card**:
     `first(triggerBody()?['attachments'])?['content']`
4. 전용 `svc-teams-notification` 계정으로 로그인해 Microsoft Teams
  연결을 생성합니다.
5. 생성된 콜백 URL 전체를 Git에서 제외된 저장소 루트 `.env`에
  저장합니다.

   ```dotenv
  TEAMS_WORKFLOW_URL="<서명이 포함된 콜백 URL 전체>"
   ```

Power Automate 연결 승인은 MFA와 조건부 액세스를 요구할 수 있으므로
대화형 단계로 유지합니다. 앱 부트스트랩으로 사용자 Teams 연결을
애플리케이션 인증으로 변경할 수는 없습니다.

## 부트스트랩

**실행 주체:** 앱 등록 권한과 관리자 동의 권한이 있는 부트스트랩
사용자입니다.

부트스트랩 및 동의 권한이 있는 ID로 한 번 로그인합니다.

```shell
az login \
  --tenant "<채널 테넌트 GUID>" \
  --use-device-code \
  --allow-no-subscriptions
```

`examples/python`에서 실행합니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<최초 Teams 채널 링크>" \
  --connection-user "svc-teams-notification@example.com" \
  --route release-notifications
```

이 명령은 다음 작업을 자동으로 수행합니다.

1. 채널 링크에서 테넌트, Team, 채널 및 표시 이름을 추출합니다.
2. Azure CLI가 해당 테넌트의 Graph 토큰을 발급할 수 있는지 확인합니다.
3. `TeamsNotifyApp`을 생성하거나 이름이 정확히 일치하는 기존 앱 하나를
  재사용합니다.
4. 해당 테넌트의 서비스 주체를 생성하거나 재사용합니다.
5. 권한 GUID를 하드코딩하지 않고 현재 Microsoft Graph 앱 역할 ID를
  조회합니다.
6. `GroupMember.ReadWrite.All`을 앱에 구성합니다.
7. 서비스 주체 앱 역할 할당을 직접 생성하고 다시 조회하여 관리자 동의가
  실제로 저장되었는지 확인합니다.
8. Teams 연결 사용자를 Entra 개체 ID로 변환합니다.
9. 재사용할 수 있는 로컬 자격 증명이 없으면 1년 클라이언트 암호를
  생성합니다.
10. 클라이언트 자격 증명 토큰의 테넌트, 클라이언트 ID 및 `roles`를
   검증합니다.
11. 생성된 값을 저장소 루트 `.env`에 원자적으로 기록하고 권한을
   `0600`으로 설정합니다.
12. Teams 연결 사용자를 Team의 기반 Microsoft 365 그룹에 멱등적으로
   추가합니다.
13. SQLite에 경로를 저장합니다.

자격 증명을 생성한 후 토큰 검증이나 `.env` 저장이 실패하면 새 자격 증명을
자동으로 삭제합니다. 클라이언트 암호 값은 출력하지 않습니다.

자동 생성되는 설정:

```dotenv
TEAMS_NOTIFY_TENANT_ID="<tenant GUID>"
TEAMS_NOTIFY_CLIENT_ID="<TeamsNotifyApp client GUID>"
TEAMS_NOTIFY_CLIENT_SECRET="<생성된 secret>"
TEAMS_CONNECTION_USER_ID="<connection 사용자 object GUID>"
```

테넌트 ID는 채널 링크에서 가져옵니다. 서비스 사용자 개체 ID는 부트스트랩
중 한 번만 조회하여 저장합니다. 따라서 `TeamsNotifyApp` 런타임에 테넌트
전체 사용자 조회 권한을 부여할 필요가 없습니다.

## 포털에서 구성 확인

**실행 주체:** `TeamsNotifyApp` 소유자입니다.

Microsoft Entra 관리 센터에서 다음을 확인합니다.

1. **App registrations**에서 `TeamsNotifyApp`을 선택합니다.
2. **API permissions**에서 Microsoft Graph의
  `GroupMember.ReadWrite.All`이 **Application** 권한인지 확인합니다.
3. 상태가 **Granted for \<tenant\>**인지 확인합니다.
4. **Enterprise applications**에서 `TeamsNotifyApp`을 선택합니다.
5. **Permissions**에서 같은 애플리케이션 권한을 확인합니다.
6. **Owners**에 이름이 명시된 운영 소유자를 최소 두 명 유지합니다.
7. **Certificates & secrets**에서 예상한 PyHookKit 자격 증명만 남아 있는지
  확인합니다.

Teams 연결 사용자는 별도 ID입니다. Power Automate의 Teams 작업 하단에서
**Connected to**가 해당 서비스 계정인지 확인합니다.

## 채널 추가

**실행 주체:** 중앙 라우터 운영자입니다.

저장소의 `.env`는 자동으로 로드됩니다. Graph 액세스 토큰을 직접 복사하거나
내보낼 필요가 없습니다.

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

등록 과정에서는 다른 테넌트의 링크를 거부하고, 새 앱 전용 토큰을 발급하며,
기존 멤버십을 확인합니다. 사용자가 없을 때만 일반 그룹 멤버로 추가하므로
명령을 반복해도 안전합니다.

표준 채널은 Team 멤버십을 따릅니다. 비공개 및 공유 채널에는 명시적인 채널
멤버십이 추가로 필요할 수 있습니다. 이 구성에서는 비공개 채널에 Flow
bot으로 전송하는 기능을 지원하지 않습니다.

## 진단

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  doctor
```

정상 결과는 다음 항목이 유효함을 의미합니다.

- Workflow URL
- 클라이언트 자격 증명 토큰 발급
- 토큰의 테넌트 및 클라이언트 ID
- 필요한 Graph 애플리케이션 역할
- 활성화된 모든 Teams 대상의 서비스 계정 멤버십
- SQLite 파일 권한 `0600`

`doctor`는 알림을 전송하지 않으며 자격 증명을 출력하지 않습니다.

## 클라이언트 암호 회전

다음과 같이 부트스트랩을 다시 실행합니다.

```shell
uv run python -m pyhookkit.entrypoints.notification_router \
  --database .local/router.sqlite3 \
  bootstrap-teams-app \
  --channel-link "<기존 Teams 채널 링크>" \
  --connection-user "svc-teams-notification@example.com" \
  --target-id teams-example-channel \
  --rotate-secret
```

부트스트랩과 `doctor`가 성공하면 Entra에서 이전 자격 증명을 삭제합니다.
새 앱 전용 토큰이 검증되기 전까지는 작동하는 자격 증명을 최소 하나
유지합니다.

## 장애 복구 및 제거

- 앱 토큰 발급이 `401`을 반환하면 클라이언트 자격 증명을 회전합니다.
- 토큰에 `roles`가 없으면 서비스 주체 앱 역할 할당과 테넌트 전체 관리자
  동의를 확인합니다.
- 멤버십 작업이 `403`을 반환하면 `GroupMember.ReadWrite.All` 동의를
  확인합니다.
- 멤버십은 성공하지만 Teams 게시가 실패하면 Power Automate Teams
  연결을 다시 승인하고 서비스 계정으로 연결되었는지 확인합니다.
- `TeamsNotifyApp`을 삭제하기 전에 멤버십 자동 등록을 중지하고 부트스트랩
  또는 복구 절차에서 해당 앱을 사용하지 않는지 확인합니다.
- 앱 등록을 삭제하면 서비스 주체와 자격 증명도 제거됩니다. 그런 다음
  `.env`에서 자동 생성된 앱 및 연결 사용자 값 네 개를 삭제합니다.
