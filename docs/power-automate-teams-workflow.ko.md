# Power Automate Teams Workflow

[English](power-automate-teams-workflow.md)

이 가이드에서는 Slack Incoming Webhook처럼 HTTP 요청으로 Teams 표준 채널에
알림을 보내는 공통 Power Automate 흐름을 만듭니다. 하나의 흐름이 요청의
Team 및 Channel 식별자와 Adaptive Card를 받아 게시 계정의 Microsoft Teams
연결로 해당 대상에 카드를 게시합니다.

가장 적은 단계로 첫 알림을 보내려면 먼저 [10분 Teams Webhook 빠른
시작](teams-webhook-quickstart.ko.md)을 사용하세요. 이 문서는 모든 UI 선택,
권한 경계 및 운영 고려 사항이 필요할 때 참조하는 상세 가이드입니다.

여러 Team에 게시 계정을 자동으로 추가해야 할 때만 [TeamsNotifyApp
부트스트랩](teams-notify-app-bootstrap.ko.md)을 참조하세요.
Azure 관리형 워크플로에서 직접 Team 및 Channel ID 라우팅을 사용하려면
[Azure Logic App Teams 전송 가이드](logic-app-teams-delivery.ko.md)를
사용하세요.

## 빈 흐름에서 만들어야 하는 이유

**Send webhook alerts to a channel** 갤러리 템플릿 대신 빈 상태에서 만든
흐름을 사용하세요.

라이브 테스트를 통해 두 흐름 모두 서식 있는 Adaptive Card 및 네이티브
사용자 멘션을 렌더링함을 확인했습니다. 갤러리 템플릿은 Adaptive Card
페이로드 외부에 소유자 표시와 **Get template** 바닥글도 삽입합니다.
페이로드를 변경해도 제거할 수 없습니다. 빈 상태에서 만든 흐름에는
**Original template** 관계가 없었으며 검증된 환경에서 해당 바닥글이
표시되지 않았습니다.

## 필수 조건

- Power Automate 클라우드 흐름을 만들 권한
- 대상 Team에 권한이 부여된 Microsoft Teams 연결
- 빠른 테스트를 위한 Teams 라이선스가 있는 기존 사용자 또는 공유·운영
   환경을 위한 전용 게시 계정
- 게시 계정이 멤버로 속한 하나 이상의 표준 Teams 채널
- 직접 스모크 테스트를 위한 Python 3

실제 Team 이름, 채널 이름, ID 또는 콜백 URL을 커밋된 파일이나 스크린샷에
넣지 마세요.

### 테넌트와 계정 경계

이 가이드에서 Azure 테넌트, Microsoft Entra 테넌트 및 Microsoft 365
테넌트는 별도의 사용자 디렉터리가 아닙니다. 대상 Microsoft Entra 테넌트가
사용자와 앱 등록을 소유하고, Microsoft 365/Teams는 같은 디렉터리의
라이선스가 있는 사용자에게 서비스를 제공합니다. Power Platform 환경도 같은
테넌트에 속합니다.

이 구성에서는 대상 Team과 채널, Power Platform 환경, Teams 연결 사용자 및
`TeamsNotifyApp`을 채널 링크의 테넌트 ID와 같은 Entra 테넌트에 두세요.
Power Automate 워크플로 경로에는 Azure 구독 또는 Azure RBAC 역할이
필요하지 않습니다. Azure Portal과 Azure CLI는 Entra ID 및 Microsoft Graph
관리 인터페이스로만 사용합니다. Azure 구독은 [Azure Logic App
Teams 전송](logic-app-teams-delivery.ko.md)을 선택할 때만 필요합니다.

흐름 작성자는 대상 Power Platform 환경의 **Environment Maker**이고, Teams
연결 사용자는 같은 테넌트의 Microsoft 365/Teams 라이선스가 있는 일반
사용자입니다. 두 계정은 같을 필요가 없으며 어느 쪽에도 Azure 구독
Contributor 또는 Owner가 필요하지 않습니다. 계정 생성 자체는 **User
Administrator**, 기존 계정의 라이선스 할당만 수행하는 경우에는 **License
Administrator**가 담당할 수 있습니다.

## ID 및 권한 설정

작성, 소유권, 커넥터 실행 및 런타임 호출에 별도의 ID를 사용하세요. 한 ID에
액세스 권한을 부여해도 다른 ID에는 부여되지 않습니다.

최초 흐름을 포털에서 수동으로 만드는 데 필요한 사람은 **흐름 작성자**,
**Teams 연결 사용자**, **운영 공동 소유자**뿐입니다. 아래 표의 부트스트랩
관리자와 Dataverse 애플리케이션 사용자는 검증된 흐름을 Solution으로 반복
배포할 때 추가되는 운영 ID이며, 최초 흐름 작성의 필수 조건이 아닙니다.

| ID | 필요한 액세스 | 필요하지 않은 액세스 |
|---|---|---|
| 부트스트랩 관리자 | Solution, 애플리케이션 사용자, 보안 역할 및 연결 참조 만들기 | 일상적인 흐름 실행 |
| Dataverse 애플리케이션 사용자 | Solution 인식 흐름 소유. 필요한 Process 행 읽기, 업데이트, 할당 및 활성화. 동일한 주체가 배포할 때 Solution 가져오기 및 게시 | Microsoft 365 라이선스, Teams 멤버십 또는 연결 사용자의 암호 |
| Teams 연결 사용자 | 적절한 Microsoft 365 및 Power Automate 사용 권한. 대상 Power Platform 환경에 로그인. Microsoft Teams 연결 권한 부여. 모든 대상 Team의 멤버십 | 테넌트 관리자 역할 또는 흐름 소유권 |
| 운영 공동 소유자 | 실행을 검사하고 흐름을 편집, 활성화 또는 비활성화하고 복구하기 위한 대상 환경 액세스 및 공동 소유자 액세스 | 다른 사용자의 연결 자격 증명을 변경할 액세스 |
| 런타임 호출자 | 비밀 저장소에서 서명된 콜백 URL을 읽고 라우팅된 요청 계약 전송 | Power Automate, Dataverse, Teams 또는 Microsoft Graph 권한 |
| 채널 인벤토리 호출자 | 인프라 런북에 설명된 범위가 있는 위임 또는 애플리케이션 Microsoft Graph 토큰 | 흐름 소유권 또는 콜백 액세스 |

초기 부트스트랩 후 애플리케이션 사용자에 대한 사용자 지정 Dataverse 보안
역할을 만드세요. 이 통합에서 소유하는 Solution 배포 작업과 Process 행만
포함해야 합니다. 부트스트랩 관리자는 배포를 증명하기 위해 일시적으로 더
넓은 역할을 사용할 수 있지만 사용자 지정 역할이 성공하면 해당 역할을
제거해야 합니다. 애플리케이션 사용자를 System Administrator로 두지
마세요.

다음과 같이 Teams 연결 사용자를 구성하세요.

1. Microsoft 365 라이선스가 있는 전용 사용자를 만들거나 지정합니다.
   퇴사하는 직원의 계정이나 테넌트 관리자를 사용하지 마세요.
2. 승인된 대상이 포함된 모든 Team에 사용자를 구성원으로 추가합니다.
   Teams 커넥터 작업은 비공개 채널 게시를 지원하지 않지만 비공개 또는 공유
   채널을 검색하려면 명시적 멤버십도 필요합니다.
3. 대상 Power Platform 환경에 해당 사용자로 로그인하고
   **Connections**를 열어 Microsoft Teams 연결을 만든 다음 테넌트의 동의,
   MFA 및 Conditional Access 요구 사항을 완료합니다.
4. Solution의 Microsoft Teams 연결 참조를 해당 연결에 바인딩합니다. 연결
   참조는 배포 시점의 간접 참조이며 사용자의 OAuth 연결을 애플리케이션
   인증으로 복사하거나 변환하지 않습니다.
5. 이름이 지정된 운영 공동 소유자를 두 명 이상 추가합니다. 이들이 실행
   기록을 검사하고 흐름을 관리할 수 있는지 확인하되 연결 사용자의 암호를
   제공하지 마세요. 공동 소유자는 다른 사용자가 만든 연결의 자격 증명을
   업데이트할 수 없습니다.

### 호출 및 실행 동작

HTTP 트리거 설정과 Teams 커넥터는 실행의 서로 다른 부분에 권한을
부여합니다.

1. 런타임 호출자는 서명된 콜백 URL을 제시하여 **When a Teams webhook
   request is received**를 호출합니다. **Who can trigger the flow?**가
   **Anyone**으로 설정된 경우 현재 PyHookKit 어댑터는 Microsoft Entra
   액세스 토큰을 보내지 않습니다.
2. 중앙 라우터는 구성된 채널 링크를 검증하고 해당 메타데이터를 저장하며
   파생된 `teamId`와 `channelId`만 보냅니다. 직접 예제는 Flow를 호출하기
   전에 구성된 링크에서 동일한 필드를 파생합니다.
3. Teams 작업은 연결 참조에서 선택한 포함된 Microsoft Teams 연결을
   사용합니다. 콜백 호출자의 액세스나 Dataverse 흐름 소유자의 액세스가
   아니라 연결 사용자의 Teams 액세스로 실행됩니다.
4. 흐름은 임의의 대상 ID에 권한을 부여하지 않습니다. 콜백 URL은 중앙
   라우터 또는 승인된 다른 호출자만 사용할 수 있도록 하세요. 또한 Teams
   서비스는 연결 사용자의 현재 Team 및 채널 액세스를 적용합니다. 동적
   Team 또는 Channel 값은 해당 액세스를 확장할 수 없습니다.

트리거에서 **Any user in my tenant** 또는 **Specific users in my tenant**를
선택하는 것은 그대로 적용할 수 있는 강화 변경이 아닙니다. 해당 모드에는
현재의 서명된 URL 어댑터가 구현하지 않는 OAuth 지원 호출자와 토큰 검증이
필요합니다. 콜백 비밀 저장소, 라우터 측 대상 허용 목록, 생성자별 라우터
자격 증명 및 노출이 의심될 때의 콜백 순환을 함께 사용하는 경우에만
**Anyone**을 유지하세요.

### 권한 변경 및 복구

| 변경 | 예상되는 영향 | 복구 |
|---|---|---|
| 연결 사용자가 Team 멤버십을 잃음 | 해당 Team 또는 채널로 보내는 새 게시물이 Teams 작업에서 실패 | 승인된 멤버십을 복원하거나 대체 연결을 바인딩한 다음 스모크 테스트 |
| 연결이 취소 또는 삭제되었거나 로그인이 필요함 | 트리거는 여전히 실행을 시작할 수 있지만 Teams 작업은 실패 | 기존 연결의 권한을 다시 부여하거나 새 연결을 연결 참조에 바인딩 |
| 연결 사용자의 라이선스 또는 계정이 제거됨 | 더 이상 전송 연속성이 지원되지 않으며 연결을 사용하지 못하게 될 수 있음 | 계정 사용 권한을 복원하거나 준비된 대체 사용자 및 연결로 마이그레이션 |
| 애플리케이션 사용자가 비활성화되거나 Dataverse 역할을 잃음 | 소유자 할당, 배포, 활성화 또는 이후 관리가 실패할 수 있음 | 애플리케이션 사용자를 다시 활성화하거나 사용자 지정 역할을 복원한 다음 소유자 검증 다시 실행 |
| 공동 소유자가 제거됨 | 런타임 연결 및 콜백 동작은 변경되지 않음 | 남은 복구 경로가 없어지기 전에 이름이 지정된 다른 공동 소유자 추가 |
| 콜백 URL이 노출됨 | URL을 가진 누구나 연결 사용자의 액세스로 전송을 시도할 수 있음 | 콜백을 재생성하거나 교체하고 승인된 비밀 저장소만 업데이트한 다음 이전 값 취소 |

수락된 HTTP 요청을 전송 증거로 취급하지 마세요. ID, 멤버십, 연결 또는 콜백
변경 후에는 Power Automate 실행, 대상 카드 및 템플릿 표시가 없는지
확인하세요.

## 흐름 만들기

1. [Power Automate](https://make.powerautomate.com)를 엽니다.
2. Teams 연결을 소유한 환경을 선택합니다.
3. **Create**를 선택한 다음 **Create from blank**를 선택합니다.
4. `PyHookKit Routed Teams Flow`와 같이 환경 중립적인 이름을 흐름에
   지정합니다.
5. **When a Teams webhook request is received**를 추가합니다.
6. 이 예제에서 사용하는 서명된 콜백 URL 모델에 대해 **Who can trigger the
   flow?**를 **Anyone**으로 설정합니다. **Specific users in my tenant**가
   더 강력하지만 현재 콜백 클라이언트 계약의 범위를 벗어나는 OAuth 지원
   호출자가 필요합니다.

예상되는 트리거 본문 형태는
[`power-automate-trigger.schema.json`](../infra/teams-workflows/power-automate-trigger.schema.json)에
문서화되어 있습니다. 이 설계에서 Teams Webhook 트리거에는 사용자 지정
스키마 필드가 없습니다. 아래 식을 사용하여 최상위 라우팅 속성을 읽으세요.

더 엄격한 생성자 측 계약은
[`routed-request.schema.json`](../infra/teams-workflows/routed-request.schema.json)로
유지됩니다. 본문은 최상위 `teamId`와 `channelId` 속성 및 하나의 Adaptive
Card 첨부 파일이 있는 Teams `message` 봉투입니다. 중앙 라우터는 채널
링크를 유지하고 해당 테넌트, Team, 채널 및 표시 이름 메타데이터를 별도로
저장합니다. 서명된 워크플로 URL은 SQLite에 저장되지 않습니다.

![Teams Webhook 트리거 및 카드 게시 작업이 있는 Power Automate 흐름.](assets/power-automate-teams-workflow/power-automate-flow-designer.png)

## 대상 검증

채널 링크를 Power Automate로 보내지 말고 중앙 라우터에 등록하세요. 등록은
현재의 `teams.cloud.microsoft` 링크 및 레거시 `teams.microsoft.com`
링크를 수락합니다. GUID 형식의 `groupId` 하나와 GUID 형식의 `tenantId`
하나, 지원되는 채널 ID 및 비어 있지 않은 채널 이름이 필요합니다. SQLite는
원본 링크와 파생된 메타데이터를 별도 열에 저장합니다.

워크플로 콜백은 권한 있는 전송 자격 증명입니다. 흐름은 라우터가 제공한
검증된 `teamId`와 `channelId`를 신뢰하므로 해당 URL을 일반 생성자에게
노출하지 마세요.

## Teams 작업 구성

트리거 바로 뒤에 **Post card in a chat or channel**을 추가합니다. Team 및
Channel 컨트롤에서 **Enter custom value**를 선택합니다.

다음과 같이 작업 필드를 설정하세요.

| 필드 | 값 |
|---|---|
| **Post as** | `Flow bot` |
| **Post in** | `Channel` |
| **Team** | `triggerBody()?['teamId']` |
| **Channel** | `triggerBody()?['channelId']` |
| **Adaptive Card** | `first(triggerBody()?['attachments'])?['content']` |

![Power Automate Teams 카드 게시 작업 설정.](assets/power-automate-teams-workflow/power-automate-teams-action.png)

Teams Webhook 트리거에는 메시지 봉투가 필요합니다. Power Automate는 대상
선택을 위해 라우팅 속성을 읽지만 Teams 작업은 첫 번째 첨부 파일의
`content` 개체만 Adaptive Card로 받아야 합니다. `triggerBody()`를 전달하면
카드 대신 봉투가 전송되어 작업에서 알림을 게시하지 않습니다.

## 콜백 저장 및 보관

1. **Save**를 선택합니다.
2. 트리거를 다시 열고 생성된 **HTTP URL**을 복사합니다.
3. 쿼리 문자열에 콜백 서명이 포함되므로 전체 URL을 자격 증명으로
   취급합니다.
4. GitLab에서 **Settings → CI/CD → Variables**를 엽니다.
5. 다음 설정으로 콜백을 추가합니다.
   - 키: `TEAMS_WORKFLOW_URL`
   - 표시 여부: **Masked**
   - 보호: **Protected**
   - 확장: 비활성화
6. URL을 GitHub, Argo CD, Kubernetes 매니페스트, 스크린샷, 명령 출력 또는
   리포지토리 파일에 저장하지 마세요.
7. 선택한 채널 링크를 동일하게 보호된 환경에
   `TEAMS_WORKFLOW_CHANNEL_LINK`로 저장합니다. 자격 증명이 아니라
   구성이지만 실제 테넌트 및 대상 식별자를 포함합니다.
8. 흐름을 공유 또는 장기 통합으로 사용하기 전에 이름이 지정된 운영 공동
   소유자를 두 명 이상 추가합니다.

## 스모크 테스트

`examples/python`에서 전송하기 전에 렌더링합니다.

```shell
uv run python scenarios/deployment_result/teams.py
```

페이로드에 합성 데이터만 포함되어 있는지 확인하세요. 그런 다음 무시되는
로컬 환경을 로드하고 의도적으로 전송합니다.

```shell
set -a
. ../../.env
set +a
uv run python scenarios/deployment_result/teams.py --send
```

CLI는 다음을 반환해야 합니다.

```json
{
  "state": "succeeded",
  "attempts": 1
}
```

다음 네 가지 결과를 모두 확인하세요.

1. 카드가 예상한 Teams 채널에 표시됩니다.
2. 구성되지 않은 경로에 대한 라우터 요청은 워크플로에 도달하기 전에
   거부됩니다.
3. 카드에 소유자 표시 또는 **Get template** 바닥글이 없습니다.
4. 해당 Power Automate 실행이 **Succeeded** 상태입니다.

## 런타임 증거

검증된 흐름이 활성화되어 있습니다. 실행 기록에는 통합 시나리오에서 사용한
Webhook 요청이 성공적으로 완료된 것으로 표시됩니다.

![Power Automate 흐름 세부 정보 및 성공한 실행 기록.](assets/power-automate-teams-workflow/power-automate-flow-history.png)

## 문제 해결

### 카드에 Get template 바닥글이 있음

흐름 세부 정보 페이지를 열고 **Original template**이 있는지 확인합니다.
해당 관계가 있으면 빈 상태에서 흐름을 다시 만드세요. 흐름의 이름을
바꾸거나 Adaptive Card를 변경하거나 콜백 URL을 복사해도 템플릿
메타데이터는 제거되지 않습니다.

### 요청은 성공하지만 카드가 표시되지 않음

라우터 대상에 파생된 Team 및 Channel ID가 포함되어 있고 Teams 작업이
활성화되어 있으며 해당 연결이 유효하고 연결 사용자가 Team과 채널에
액세스할 수 있는지 확인하세요. 해당 실행을 열고 요청 본문이나 연결 세부
정보를 이슈에 복사하지 않은 채 작업 상태를 검사하세요.

작업에서 `AADSTS500014` 또는 `ResourceDisabledInTenant`가 보고되면 테넌트
구성을 변경하기 전에 작업 출력에서 리소스를 식별합니다. **Microsoft Entra
ID** > **Enterprise applications**에서 해당 Microsoft 자사 엔터프라이즈
애플리케이션을 확인하세요.

| 리소스 또는 애플리케이션 ID | 엔터프라이즈 애플리케이션 |
|---|---|
| `https://publishers.crm.dynamics.com` 또는 `00000007-0000-0000-c000-000000000000` | Dataverse |
| `ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b` | Microsoft Teams Graph Service |
| `https://api.spaces.skype.com` 또는 `cc15fd57-2c6c-4117-a88c-83b1d56b4bbe` | Microsoft Teams Services |
| `00000003-0000-0ff1-ce00-000000000000` | Office 365 SharePoint Online |

테넌트 정책 및 라이선스에서 허용되는지 확인한 후 오류에 명시된
애플리케이션만 활성화하세요. Microsoft Entra 토큰 발급에 변경 사항이
반영될 때까지 기다린 다음 기존 Teams 연결에 다시 권한을 부여하고 합성
카드를 다시 실행하세요. `202 Accepted` 트리거 응답은 Teams 작업이
성공했다는 증거가 아닙니다.

작업이 `Teams has been disabled on the tenant`와 함께 `Unauthorized`를
반환하는 경우 테넌트에 Teams를 포함하는 활성 Microsoft 365 구독이
필요하며 연결 사용자에게 활성화된 Teams 서비스 플랜이 필요합니다.
엔터프라이즈 애플리케이션을 활성화하는 것으로 구독 또는 사용자 라이선스를
대체할 수 없습니다.

### Power Automate에서 요청을 거부함

호출자가 최상위 `teamId`와 `channelId` 및 하나의 Adaptive Card 첨부 파일이
있는 Teams `message` 봉투를 보내는지 확인하세요. Logic App 요청은 카드를
`card` 아래에 래핑하며 엔드포인트 URL만 바꿔서 전송할 수 없습니다.

### 이미지가 렌더링되지 않음

Teams는 공개 HTTPS를 통해 이미지 URL을 가져올 수 있어야 합니다. 런타임
전송은 `EXAMPLE_ASSET_BASE_URL`을 통해 커밋된 합성 마커를 확인합니다.

## 수명 주기 및 자동화

첫 번째 흐름에서는 Microsoft 연결을 선택하고 권한을 부여해야 합니다. 반복
환경의 경우 검증된 흐름을 Power Platform Solution에 배치하고 구체적인
연결을 연결 참조로 교체한 다음 Power Platform CLI로 배포하세요.

생성된 콜백 URL은 환경별 런타임 상태로 유지됩니다. 활성화 후 URL을
가져와 대상 비밀 저장소에 직접 기록하세요.

ALM 로드맵, 소유권 요구 사항 및 바닥글 검증 체크리스트는 [Teams Workflows
인프라 런북](../infra/teams-workflows/README.md)을 참조하세요.

Microsoft의 소유권 및 연결 의미 체계는 [클라우드 흐름
공유](https://learn.microsoft.com/power-automate/create-team-flows),
[클라우드 흐름 소유자 변경](https://learn.microsoft.com/power-automate/change-cloud-flow-owner),
[Solution 인식 클라우드
흐름](https://learn.microsoft.com/power-automate/guidance/coding-guidelines/understand-benefits-solution-aware-flows)
및 [Teams에서 메시지
보내기](https://learn.microsoft.com/power-automate/teams/send-a-message-in-teams)에
문서화되어 있습니다.
