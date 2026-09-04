# 문서

[English](README.md)

이 디렉터리에는 사용자를 위한 아키텍처, 설정, 운영, 마이그레이션 지침이
있습니다. 공급자 또는 인프라 구현 세부 정보는 해당 정보가 구성하는
`infra/` 아래 자산과 함께 둡니다.

## 여기서 시작하기

| 목표 | 문서 |
|---|---|
| 첫 번째 쌍으로 구성된 예제 실행 | [시작하기](getting-started.ko.md) |
| 로컬 공급자 값 구성 | [공급자 구성](configuration.ko.md) |
| SQLite 중앙 라우터 실행 | [중앙 알림 라우터](central-notification-router.ko.md) |
| 표시되는 Graph 앱 부트스트랩 | [TeamsNotifyApp 부트스트랩](teams-notify-app-bootstrap.ko.md) |
| 의미론적 동등성 이해 | [알림 동등성](notification-parity.ko.md) |
| Teams ID 구성 및 배달 흐름 생성 | [Power Automate Teams 워크플로](power-automate-teams-workflow.ko.md) |
| 라우팅된 Teams 배달 배포 | [Azure Logic App Teams 배달](logic-app-teams-delivery.ko.md) |
| 전체 AKS 시나리오 실행 | [통합 Bookinfo 시나리오](integrated-bookinfo-scenario.ko.md) |
| 인프라 경계 이해 | [인프라](infrastructure.ko.md) |
| Teams 배달 어댑터 비교 | [Teams 배달 옵션](teams-delivery-options.ko.md) |
| Teams 카드 설계 | [Teams Adaptive Cards](teams-adaptive-cards.ko.md) |
| Slack 기능 살펴보기 | [Slack 예제](slack-examples.ko.md) |
| 자격 증명 경계 검토 | [보안](security.ko.md) |
| 공급자 마이그레이션 계획 | [마이그레이션](migration.ko.md) |

## 문서 자산

- [문서 자산](assets/README.ko.md)
- [클라이언트 캡처 갤러리](assets/card-previews/README.ko.md)
- [통합 시나리오 캡처](assets/integrated-scenario/README.ko.md)
- [Azure Logic App Teams 배달 캡처](assets/logic-app-teams-delivery/README.ko.md)
- [Power Automate Teams 워크플로 캡처](assets/power-automate-teams-workflow/README.ko.md)

## 문서 경계

- `docs/`는 사용자가 무엇을 선택하며 어떻게 운영하는지 설명합니다.
- `infra/**/README.md`는 구체적인 인프라 자산을 프로비저닝, 연결, 검증,
  제거하는 방법을 설명합니다.
- `examples/python/**/README.md`는 실행 가능한 예제 또는 카탈로그 하나를
  설명합니다.
- `contracts/**/README.md`는 언어 중립적인 스키마와 픽스처를 설명합니다.

커밋되는 모든 지침에서는 합성 이름, ID, URL, 경로, 대상을 사용합니다.
자격 증명, 콜백 서명, 계정 ID 또는 실제 환경 식별자가 포함된 스크린샷이나
명령 출력을 절대 추가하지 마세요.
