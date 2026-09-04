# Azure Logic App Teams 전송

[English](logic-app-teams-delivery.md)

이 가이드는 직접 ID 방식의 Logic App 어댑터를 배포하고 운영하는 방법을
설명합니다. 호출자가 대상 Team 및 Channel ID를 이미 소유하고 있거나 Teams
전송을 Azure 인프라로 관리해야 할 때 사용하세요.

중앙 라우터가 채널 링크를 저장하고 여기에서 파생된 Team 및 Channel ID를
제공하는 경우에는 Power Automate Workflow가 더 간단한 기본 선택입니다.
[Power Automate Teams Workflow 가이드](power-automate-teams-workflow.ko.md)를
참조하세요.

## 요청 계약

HTTP 트리거는 다음 요청을 수락합니다.

```json
{
  "teamId": "<Teams team ID>",
  "channelId": "<Teams channel ID>",
  "eventId": "<provider-neutral event ID>",
  "card": {
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": []
  }
}
```

Logic App은 Teams 관리형 커넥터를 호출하기 전에 필수 라우팅 및 카드 필드를
검증합니다.

- 유효한 요청 및 게시 성공: HTTP `201`
- 유효하지 않은 요청: HTTP `400`
- Teams 커넥터 실패 또는 시간 초과: HTTP `502`

PyHookKit은 공급자 응답 식별자를 폐기하고 공급자 중립적 상태와 시도 횟수만
반환합니다.

## 사전 요구 사항

- Logic App을 위한 Azure 리소스 그룹
- 동일한 구독 및 지역에 있고 권한이 부여된
  `Microsoft.Web/connections` Microsoft Teams 연결
- 대상 Team 및 Channel ID
- `Microsoft.Logic/workflows` 배포 권한
- 서명된 콜백 URL을 위한 승인된 비밀 저장소

연결 권한 부여는 명시적인 부트스트랩 단계입니다. Bicep은 이미 권한이 부여된
연결을 참조하며 OAuth 동의를 포함하거나 재현하지 않습니다. 연결은 다른
리소스 그룹에 있어도 되지만 동일한 구독 및 지역에 있어야 하며 Logic App과
함께 삭제해서는 안 됩니다.

## 배포

자격 증명을 출력하지 않고 권한이 부여된 연결 리소스 ID를 확인합니다.

```shell
TEAMS_CONNECTION_ID="$(
  az resource show \
    --resource-group <connection-resource-group> \
    --name <teams-connection-name> \
    --resource-type Microsoft.Web/connections \
    --api-version 2016-06-01 \
    --query id \
    --output tsv
)"
```

워크플로를 배포합니다.

```shell
az deployment group create \
  --name pyhookkit-logic-app \
  --resource-group rg-notify \
  --template-file infra/azure/logic-apps/main.bicep \
  --parameters \
    logicAppName=logic-notify-teams \
    teamsConnectionResourceId="$TEAMS_CONNECTION_ID"
```

템플릿은
[`workflow-definition.json`](../infra/azure/logic-apps/workflow-definition.json)을
로드하고, 트리거 및 커넥터 입출력의 보안 처리를 활성화하며, 서명된 콜백
URL을 배포 출력으로 반환하지 않습니다.

## 배포된 구성 검사

Bicep 템플릿과 커밋된 워크플로 정의가 정보의 기준 원본입니다. Portal은
배포를 검사하고 검증하는 데 사용하고, 클릭으로 구성한 별도의 사본을
유지하는 데 사용하지 마세요.

1. Azure Portal에서 배포된 Logic App을 엽니다.
2. **Development Tools → Logic app designer**를 선택합니다.
3. 두 검증 분기를 모두 확인하려면 **Expand all**을 선택합니다.

활성 워크플로는 HTTP 요청을 수락하고 라우팅 및 카드 필드를 검증하며, 유효한
카드를 Teams에 게시하고 모든 경로에서 명시적인 상태를 반환합니다.

![검증, Teams 전송 및 응답 분기가 펼쳐진 Logic App 워크플로](assets/logic-app-teams-delivery/logic-app-workflow-expanded.png)

**When a HTTP request is received → Settings**를 선택합니다. 콜백과 알림
데이터가 실행 진단에 나타나지 않도록 **Secure inputs**와 **Secure outputs**
를 모두 켜야 합니다.

![보안 입력 및 출력을 사용하도록 설정한 Logic App HTTP 트리거](assets/logic-app-teams-delivery/logic-app-trigger-security.png)

**Post card to channel → Parameters**를 선택하고 다음을 확인합니다.

| 필드 | 값 |
|---|---|
| **Post as** | `Flow bot` |
| **Post in** | `Channel` |
| **Team** | `triggerBody()?['teamId']` |
| **Channel** | `triggerBody()?['channelId']` |
| **Adaptive Card** | `string(triggerBody()?['card'])` |

![동적 경로와 Adaptive Card 입력이 있는 Logic App Teams 작업](assets/logic-app-teams-delivery/logic-app-teams-action.png)

문서화를 위해 트리거의 **Parameters** 탭을 열거나 캡처하지 마세요. 이 탭에는
서명된 콜백 URL이 표시됩니다.

## 콜백 가져오기 및 저장

콜백을 승인된 비밀 저장소 명령으로 직접 가져오세요. 배포 아티팩트에
출력하거나 저장하지 마세요.

```shell
SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
TEAMS_LOGIC_APP_URL="$(
  az rest \
    --method post \
    --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/rg-notify/providers/Microsoft.Logic/workflows/logic-notify-teams/triggers/When_a_HTTP_request_is_received/listCallbackUrl?api-version=2016-06-01" \
    --query value \
    --output tsv
)"
```

다음과 같이 구성합니다.

```dotenv
TEAMS_LOGIC_APP_URL="<signed callback URL>"
TEAMS_LOGIC_APP_TEAM_ID="<Teams team ID>"
TEAMS_LOGIC_APP_CHANNEL_ID="<Teams channel ID>"
```

GitLab에서는 세 값을 모두 보호된 변수로 추가하고
`TEAMS_LOGIC_APP_URL`을 마스킹하세요.

## 전송 어댑터 선택

기본값은 계속 `workflow`입니다. 필요한 경우에만 Logic App을 선택하세요.

### 자동화 CLI

```shell
uv run python -m pyhookkit.entrypoints.scenario_cli \
  deployment-result teams \
  --teams-delivery logic-app \
  --event-id deploy-example-1042 \
  --correlation-id deploy-example-1042 \
  --service bookinfo \
  --deployment-environment staging \
  --revision 9f3a2c1 \
  --duration "2m 18s" \
  --completed-at 2026-08-28T03:15:00Z \
  --deployment-url https://deployments.example.com/runs/1042 \
  --send
```

Power Automate를 사용하려면 `--teams-delivery`를 생략하거나 `workflow`로
설정하세요.

### GitLab

파이프라인 입력을 제공합니다.

```text
teams-delivery=workflow
```

또는:

```text
teams-delivery=logic-app
```

유지 관리 일정과 표준 알림 작업은 선택한 값을 동일한 시나리오 CLI로
전달합니다.

### GitHub 승인 워크플로

`bookinfo-release.yml`을 디스패치할 때 **Teams delivery adapter**를
선택하세요. 승인 알림과 승인된 프로모션 요청은 동일한 선택을 GitLab으로
전달합니다.

### Argo CD 배포 결과

`argocd-notifications-cm`에서 `teamsDelivery`를 설정합니다.

```yaml
data:
  context: |
    argocdUrl: https://argocd.example.com
    teamsDelivery: logic-app
```

기본값을 복원하려면 `workflow`로 되돌리세요.

### AKS 인시던트 프로브

일회성 Job을 적용하기 전에 `TEAMS_DELIVERY`를 패치합니다.

```yaml
env:
  - name: TEAMS_DELIVERY
    value: logic-app
```

## 스모크 테스트

먼저 유효하지 않은 요청을 거부하고 HTTP `400`을 반환하는지 확인합니다. 그런
다음 시나리오 하나를 전송합니다.

```shell
cd examples/python
set -a
. ../../.env
set +a
uv run python scenarios/deployment_result/teams.py --send-logic-app
```

다음을 확인합니다.

1. CLI가 `state: succeeded`를 반환합니다.
2. Logic App 실행 상태가 `Succeeded`입니다.
3. Teams 카드가 Workflow 전송과 동일한 의미 체계 필드를 보존합니다.
4. 콜백 URL, 커넥터 입력 및 공급자 출력이 로그에 나타나지 않습니다.

디자이너의 **Run history** 탭을 엽니다. 참조 검증에서는 직접 시나리오뿐
아니라 GitHub, GitLab, Argo CD 및 AKS 자동화 경로에서도 성공적인 실행이
생성되었습니다.

![알림 실행에 성공한 Logic App 실행 기록](assets/logic-app-teams-delivery/logic-app-run-history.png)

성공한 실행을 열고 HTTP 트리거, 검증, Teams 게시 및 `Response created`
단계가 모두 성공했는지 확인합니다.

![라우팅된 전체 전송 경로를 보여 주는 성공한 Logic App 실행](assets/logic-app-teams-delivery/logic-app-run-success.png)

검증된 환경에서는 Logic App을 통해 배포, 인시던트, 유지 관리 및 승인
시나리오가 성공적으로 전송되었습니다. 또한 선택 사항이 없는 파이프라인이
여전히 Power Automate Workflow 기본값을 사용하는 것도 검증했습니다.

## 검증된 참조 배포

라이브 검증에서는 Korea Central의 `rg-notify`에 `logic-notify-teams`를
배포하고 연결된 Teams 관리형 API 연결을 재사용했습니다.

검증 결과는 다음과 같습니다.

- Bicep 재배포는 멱등성을 보장합니다.
- 배포된 워크플로 정의가 커밋된 JSON과 일치합니다.
- 유효하지 않은 입력은 `400`을 반환합니다.
- 유효한 입력은 Teams 메시지 식별자와 함께 `201`을 반환합니다.
- 네 가지 시나리오 전송이 모두 공급자 중립적 성공을 반환합니다.
- GitLab은 명시적 `logic-app`과 기본 `workflow` 모두에서 성공합니다.
- GitHub 승인 및 프로모션은 `logic-app`에서 성공합니다.
- AKS 인시던트 프로브는 `logic-app`에서 성공합니다.
- Argo CD 배포 결과 알림은 `logic-app`에서 성공합니다.
- 관찰된 Logic App 검증 실행은 실패 없이 완료되었습니다.

실제 콜백 URL, Team ID, Channel ID, 연결 ID, 실행 ID 및 메시지 식별자는
커밋된 증거 자료에서 의도적으로 제외합니다.

## 회전 또는 제거

노출이 의심되면 HTTP 트리거 콜백을 다시 생성하고 승인된 비밀 저장소를
업데이트하세요. 연결 권한 부여는 별도로 회전합니다.

Logic App만 제거합니다.

```shell
az resource delete \
  --resource-group rg-notify \
  --name logic-notify-teams \
  --resource-type Microsoft.Logic/workflows
```

Logic App을 제거해도 공유된 Teams API 연결은 삭제되지 않습니다.
