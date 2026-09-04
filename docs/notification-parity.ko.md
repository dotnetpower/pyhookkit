# 알림 동등성

[English](notification-parity.md)

동등성이란 이벤트, 결과, 필수 사실, 멘션, 링크 및 핵심 사용자 동작을
보존하는 것을 의미합니다. 공급자 페이로드의 JSON이나 시각적 레이아웃이
동일할 필요는 없습니다.

지원되지 않거나 저하된 동작은 조용히 생략하지 말고 명시적으로 보고해야
합니다.

## 표준 경계

`contracts/notification.schema.json`은 공급자 중립적 입력입니다. 도메인
객체와 픽스처에는 논리적 경로와 ID 별칭이 포함될 수 있지만 공급자 페이로드
필드, 대상 URL, Slack ID, Teams ID 또는 SDK 유형은 절대 포함할 수
없습니다.

| 의미 | 표준 필드 |
|---|---|
| 이벤트 ID | `eventId` |
| 논리적 대상 | `route` |
| 결과 | `severity`, `title`, `body` |
| 구조화된 컨텍스트 | 순서가 지정된 `facts` |
| 탐색 | 레이블이 지정된 HTTPS `links` |
| 알림 대상 | 논리적 `mentions` |
| 상관관계 | `threadKey`, `metadata.correlationId` |
| 소스 컨텍스트 | `sourceTimestamp`, `metadata.source` |

## 기능 분류

요청된 모든 동작은 공급자 렌더링 전에 분류됩니다.

- **동등**: 두 공급자 모두 해당 동작을 기본적으로 보존합니다.
- **저하**: 필수 의미는 유지되지만 상호 작용 또는 표현 방식이 다릅니다.
- **고급 어댑터**: 기본 webhook은 해당 동작을 제공할 수 없지만 인증된
  어댑터는 제공할 수 있습니다.
- **미지원**: 구성된 어떤 어댑터도 요청을 보존할 수 없습니다.

예:

| 기능 | Slack | Teams Workflow |
|---|---|---|
| 심각도, 사실, URL 동작 | 동등 | 동등 |
| 사용자 멘션 | 기본 매핑 ID | 기본 매핑 멘션 엔터티 |
| 그룹 멘션 | 기본 사용자 그룹 | 저하된 공지 또는 Graph 확장 |
| 스레드 답글 | 알려진 `thread_ts` | 고급 봇 또는 Graph 어댑터 |
| 업데이트 및 삭제 | Slack Web API | 고급 봇 또는 Graph 어댑터 |

## 검증

각 기본 기능 또는 시나리오에는 다음이 있습니다.

1. 하나의 표준 `notification.json`
2. 고정된 Slack 예상 페이로드
3. 고정된 Teams 예상 페이로드
4. 스키마 검증
5. 필수 사실, 링크, 멘션 및 동작에 대한 의미론적 어설션
6. 거부되거나 지원되지 않는 입력에 대한 부정 테스트

스냅샷 동등성은 공급자별로 적용됩니다. 동등성 테스트는 JSON 형태나 픽셀이
아니라 필수 의미를 비교합니다. 클라이언트 렌더링, 외부 이미지 가져오기,
기본 멘션, 버튼 및 공급자가 생성한 발신자 표시는 여전히 실제 테스트가
필요합니다.

픽스처 카탈로그는
[`contracts/test-vectors/`](../contracts/test-vectors/README.md)를, 전체
알림 예제는
[`examples/python/scenarios/`](../examples/python/scenarios/README.md)를
참조하세요.
