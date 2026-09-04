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
