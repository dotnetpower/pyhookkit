# Microsoft Teams Webhook 알림 가이드

[English](README.md)

Slack Incoming Webhook처럼 HTTP 요청 하나로 Microsoft Teams 표준 채널에
Adaptive Card 알림을 보낼 수 있습니다. 첫 알림에는 별도 라우터나 Microsoft
Graph 앱이 필요하지 않습니다.

## 가장 빠른 시작

[10분 Teams Webhook 빠른 시작](teams-webhook-quickstart.ko.md)을 따라 다음
세 작업을 완료하세요.

1. **게시 계정을 Team에 추가합니다.** Power Automate의 Teams 작업은 연결에
  로그인한 사용자 권한으로 실행되므로 Teams 라이선스와 Team 멤버십이 있는
  계정이 필요합니다.
2. **공통 Power Automate 흐름을 만듭니다.** Webhook 요청에서 Team, 채널 및
  Adaptive Card를 읽어 게시하는 흐름 하나를 모든 표준 채널에서 공유합니다.
3. **표준 라이브러리 스크립트로 테스트합니다.** 채널 링크와 흐름 콜백 URL만
  설정하여 첫 카드를 전송합니다. `pyhookkit` 패키지나 서버를 실행하지
  않습니다.

> [!NOTE]
> 10분은 Power Automate 권한, 라이선스가 있는 게시 계정 및 표준 채널이 이미
> 준비된 상태를 기준으로 합니다. 운영 환경에서는 개인 계정 대신
> `svc-teams-notification` 같은 전용 일반 사용자를 권장합니다.

## 각 구성 요소가 필요한 이유

| 구성 요소 | 필요한 이유 | 필수 여부 |
|---|---|---|
| Microsoft 365 게시 계정 | Teams 커넥터가 이 사용자의 권한과 Team 접근 권한으로 카드를 게시합니다. | 필수. 빠른 테스트에는 기존 라이선스 사용자를 사용할 수 있습니다. |
| 공통 Power Automate 흐름 | 서명된 HTTP URL을 만들고 요청의 목적지와 Adaptive Card를 Teams 작업에 연결합니다. | 필수 |
| `TeamsNotifyApp` Graph 앱 | 게시 계정을 여러 Team의 기반 Microsoft 365 그룹에 자동으로 추가합니다. | 선택 사항. 첫 전송은 Team 소유자가 수동으로 추가할 수 있습니다. |
| PyHookKit 라우터 | 기존 Slack 알림 생산자를 통제된 경로로 전환하거나 여러 Slack·Teams 대상으로 팬아웃합니다. | 선택 사항 |

`TeamsNotifyApp`은 메시지를 게시하지 않으며 Power Automate의 사용자 연결을
대체하지 않습니다. 대상 Team이 적으면 Graph 권한을 추가하지 말고 수동
멤버십을 유지하세요.

## 작업별 문서

| 목표 | 문서 |
|---|---|
| 10분 안에 첫 Teams 알림 보내기 | [Teams Webhook 빠른 시작](teams-webhook-quickstart.ko.md) |
| 스크린샷을 보며 공통 흐름 만들기 | [Power Automate Teams 워크플로](power-automate-teams-workflow.ko.md) |
| Adaptive Card 디자인하기 | [Teams Adaptive Card 디자인](teams-adaptive-cards.ko.md) |
| Teams 전송 방식 비교하기 | [Teams 전송 옵션](teams-delivery-options.ko.md) |
| 콜백과 자격 증명 보호하기 | [보안](security.ko.md) |
| 여러 Team의 게시 계정 멤버십 자동화하기 | [TeamsNotifyApp 부트스트랩](teams-notify-app-bootstrap.ko.md) |
| 선택적 팬아웃 라우터 실행하기 | [중앙 알림 라우터](central-notification-router.ko.md) |
| Slack과 Teams 의미 동등성 이해하기 | [알림 동등성](notification-parity.ko.md) |

## 고급 운영 및 예제

- [공급자 구성](configuration.ko.md)
- [Slack 예제](slack-examples.ko.md)
- [Azure Logic App Teams 전송](logic-app-teams-delivery.ko.md)
- [인프라](infrastructure.ko.md)
- [통합 Bookinfo 시나리오](integrated-bookinfo-scenario.ko.md)
- [마이그레이션](migration.ko.md)

커밋되는 모든 지침에서는 합성 이름, ID, URL, 경로 및 대상을 사용합니다.
자격 증명, 콜백 서명, 계정 ID 또는 실제 환경 식별자가 포함된 화면이나 명령
출력을 추가하지 마세요.
