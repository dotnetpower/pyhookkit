# Teams 전송 옵션

[English](teams-delivery-options.md)

Teams Workflows는 초기 동등성 목표입니다. Workflow 웹후크가 제공할 수 없는
동작에는 Logic Apps, 리소스별 동의가 적용된 Microsoft Graph 또는 Teams 봇과
같은 고급 어댑터를 사용합니다.

선택한 어댑터는 지원하는 기능과 소유권 요구 사항을 명시해야 합니다.

## Azure Logic App 전송

Logic App 전송은 엔드포인트만 바꾸는 방식이 아닙니다. 두 HTTP 계약은 서로
다릅니다.

| 영역 | Power Automate Workflow | Azure Logic App `post-card` |
|---|---|---|
| 요청 본문 | `teamId`, `channelId` 및 Adaptive Card 첨부 파일 하나를 포함하는 Teams `message` 봉투 | `teamId`, `channelId`, 선택적 `eventId` 및 내부 `card` |
| 라우팅 | 라우터에 저장된 채널 링크를 명시적 ID로 변환 | 요청마다 명시적인 Team 및 Channel ID 사용 |
| 엔드포인트 성공 | Workflow 2xx 상태 | `post-card`가 Teams 메시지 식별자와 함께 `201` 반환 |
| 인증 | 서명된 Workflow 콜백 URL | 서명된 Logic App 트리거 URL 및 권한이 부여된 Teams API 연결 |

PyHookKit은 하나의 `TeamsMessageRenderer`를 유지하고 전송 경계만 조정합니다.
`--send-logic-app`을 사용하고 Logic App URL을 `TEAMS_WORKFLOW_URL`에 넣지
마세요. 어댑터는 콜백 URL을 검증하고 민감 정보를 가리며, 정확히 하나의
Adaptive Card 첨부 파일을 추출하고, 구성된 라우팅을 추가한 뒤, Workflow
전송에서 사용하는 것과 동일하게 민감 정보가 제거된 공급자 중립적 전송
결과를 반환합니다. 두 어댑터 모두 모든 2xx 응답을 성공으로 처리합니다.
공급자 페이로드가 결과 계약으로 유출되지 않도록 공급자 응답 본문과 메시지
식별자를 의도적으로 폐기합니다.

두 어댑터 모두 속도 제한, 일시적인 `5xx` 응답 및 전송 실패에 대해 최대
세 번까지 재시도합니다. `429`에서는 `Retry-After`가 우선 적용되며, 그
외에는 지터를 적용한 제한적 지수 백오프를 사용합니다. 검증, 인증, 권한 및
기타 영구적 실패는 재시도하지 않습니다.

```shell
uv run python scenarios/deployment_result/teams.py --send-logic-app
```

트리거 스키마와 인프라 자산은
[Logic App 런북](../infra/azure/logic-apps/README.md)을 참조하세요. 배포,
선택, 라이브 테스트 및 제거에 대해서는
[Logic App Teams 전송 가이드](logic-app-teams-delivery.ko.md)를 참조하세요.

계약 테스트는 라이브러리를 사용하는 모든 Teams 예제를 두 어댑터 모두에서
실행하고, 변환된 내부 Adaptive Card가 변경되지 않았는지 확인합니다. 원시
F00 예제에는 표준 라이브러리 요청 빌더에 대해 동등한 검증이 있습니다.

## Workflow 수명 주기

Microsoft 연결 선택과 동의 부여는 환경별 작업이므로 최초의 라우팅된
Workflow는 수동으로 생성합니다. 하나의 콜백이 라우팅된 카드 본문을
수신하므로 알림 채널마다 별도의 Flow가 필요하지 않습니다.

반복 배포의 경우 Power Platform Solution에 흐름을 패키징하고 연결 참조를
사용하여 Power Platform CLI로 배포하세요. 연결 권한 부여와 소유권을
명시적인 부트스트랩 요구 사항으로 취급하고, 생성된 콜백 URL을 비밀 저장소에
직접 기록하세요.

빈 상태에서 만든 최초 흐름을 내보낸 뒤에는 Power Automate 포털을
열지 않고도 이후 환경을 프로비저닝할 수 있습니다.

1. Power Platform CLI로 Solution을 패키징하고 가져옵니다.
2. Teams 연결 참조를 바인딩합니다.
3. 흐름을 활성화합니다.
4. `listCallbackUrl`을 통해 트리거 URL을 가져옵니다.
5. 환경의 비밀 저장소에 직접 저장합니다.
6. 바닥글 및 리치 카드 스모크 테스트를 실행합니다.

Power Platform CLI는 Solution 아티팩트를 배포하지만 단계별 흐름 디자이너를
제공하지는 않습니다. Dataverse 워크플로 JSON을 통한 직접 생성은 버전에
민감한 고급 대안이며 권장되는 부트스트랩 경로가 아닙니다.

수동 생성 및 스모크 테스트는
[Power Automate Teams Workflow 가이드](power-automate-teams-workflow.ko.md)를
참조하고, 배포 자동화와 소유권은
[Teams Workflows 런북](../infra/teams-workflows/README.md)을 참조하세요.

## 렌더링 및 귀속 표시

`TeamsMessageRenderer`는 심각도 스타일, 제목, 팩트, 이미지, 소스 컨텍스트,
링크 및 사용자 멘션 엔터티를 포함하는 Adaptive Card 1.4 페이로드를
생성합니다. Teams Workflow는 메일 그룹을 직접 멘션할 수 없습니다. 그룹
알림은 고급 구성입니다. Microsoft Graph를 통해 구성원을 확인한 다음 각
구성원을 개별 멘션으로 렌더링하세요. 이를 위해서는 애플리케이션 자격 증명,
`GroupMember.Read.All`에 대한 관리자 동의, 멤버십과 28 KB 카드 크기 제한에
대한 명시적인 처리가 필요합니다. 해당 어댑터가 구성되기 전에는 구성 필요
안내와 함께 그룹 별칭이 계속 표시됩니다.
Workflow 웹후크에서는 스레드 지정 및 메시지 변경도 사용할 수 없습니다.
F08은 요청된 스레드 키와 함께 눈에 보이는 새 메시지 대체 동작을 렌더링하고,
F09는 지원되지 않음을 명시적으로 안내합니다. 실제 답글, 업데이트 및 삭제에는
Teams 메시지 식별자를 영구 저장하고 적절한 권한을 갖춘 봇 또는 Microsoft
Graph 어댑터가 필요합니다.

시각적 계층 구조는 다음을 사용합니다.

- 전체 폭의 Microsoft 편집 샘플 이미지
- 이모지 없이 가운데 정렬된 심각도 레이블과 제목
- 가운데에 은은하게 배치된 PyHookKit 경로 컨텍스트
- 반응형 2열 팩트 타일
- 밝은 멘션 패널
- 접근 가능한 대체 텍스트와 캡션이 있는 이미지
- 간결한 소스 및 타임스탬프 텍스트
- 명확한 레이블이 붙은 `Action.OpenUrl` 버튼

Teams에서 이미지를 렌더링하려면 이미지 URL에 공개 HTTPS로 접근할 수 있어야
합니다. 커밋된 페이로드는 합성 마커를 사용합니다. 라이브 전송에서는 해당
마커를 `EXAMPLE_ASSET_BASE_URL`에서 변환하며, `TEAMS_ASSET_BASE_URL`은
호환 가능한 대체 값으로 유지됩니다.

공식 모범 사례 기준과 독립 실행형 예제 갤러리는
[Teams Adaptive Card 디자인](teams-adaptive-cards.ko.md)을 참조하세요.

라이브 테스트에서 확인된 결과는 다음과 같습니다.

| 전송 흐름 | 리치 카드 | 네이티브 사용자 멘션 | `Get template` |
|---|---:|---:|---:|
| Teams Workflow 갤러리 템플릿 | 예 | 예 | 표시됨 |
| 빈 상태에서 만든 Power Automate 흐름 | 예 | 예 | 표시되지 않음 |

갤러리 바닥글은 알림 페이로드가 아니라 Teams에서 생성합니다. 페이로드를
변경해도 제거할 수 없습니다. 현재 빈 상태에서 만든 Flow에는 바닥글이
표시되지 않습니다. 발신자 신원과 귀속 표시를 계약에 따라 제어해야 하는
경우에는 Teams 봇이나 적합한 Graph 어댑터를 사용하세요.

Power Automate는 흐름 세부 정보 페이지에서 인과 관계의 차이를 보여 줍니다.
템플릿에서 생성된 흐름에는 **Original template** 관계가 있지만, 검증된 빈
상태에서 만든 흐름에는 없습니다. 바닥글의 **Get template** 링크는 해당 원본
템플릿으로 연결됩니다. 따라서 배포 검증 시 흐름 이름이나 복사된 작업 정의에
의존하지 말고 세부 정보 페이지와 실제 게시된 카드를 모두 확인해야 합니다.

이 바닥글은
[Microsoft 365 Roadmap 393923](https://www.microsoft.com/microsoft-365/roadmap?featureid=393923)에서
추적하는 Teams Workflow 템플릿 검색 기능입니다. 이 기능은 템플릿에서 생성된
흐름에 적용되며 수신 웹후크 페이로드 외부에 있습니다. 이름 변경, 메타데이터가
불확실한 복제 또는 Adaptive Card 요소 변경은 신뢰할 수 있는 제거 방법이
아닙니다.
