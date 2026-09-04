# Teams Adaptive Card 디자인

[English](teams-adaptive-cards.md)

PyHookKit은 Teams Workflow 전송에 Adaptive Card 1.4를 사용합니다. 현재
Teams는 더 새로운 스키마 버전을 지원하지만 보수적인 기준선을 사용하면 웹,
데스크톱, 모바일 및 임베디드 화면 간의 차이를 줄일 수 있습니다.

구현은 공식
[Adaptive Cards 디자인 모범 사례](https://adaptivecards.microsoft.com/?topic=design-best-practices)와
[Teams 카드 참조](https://learn.microsoft.com/microsoftteams/platform/task-modules-and-cards/cards/cards-reference)를
따릅니다.

## 디자인 기준선

- 결과와 기본 제목을 맨 앞에 둡니다.
- 크기, 굵기, 의미론적 색상 및 간격을 사용하여 계층 구조를 확립합니다.
- 기본 보기는 간결하게 유지하고 진단 정보에는 점진적 공개를 사용합니다.
- 고정된 카드 또는 열 너비를 사용하지 않고 열을 세 개 넘게 사용하지
  않습니다. PyHookKit은 유연한 열을 최대 두 개 사용합니다.
- `fallbackText` 및 `speak` 요약을 포함합니다.
- 모든 이미지에 의미 있는 `altText`를 제공합니다.
- 공개 HTTPS CDN에 이미지를 호스팅합니다. PNG, JPEG 또는 GIF를 사용하고
  크기는 1024 x 1024픽셀과 1MB 이하여야 합니다. 리디렉션과 SVG는 피합니다.
- `TextBlock`에서는 HTML보다 Markdown을 우선합니다. Teams는 일부만
  지원하므로 Markdown 헤더, 표, 이미지, 서식이 미리 지정된 텍스트 또는
  인용문에 의존하지 마십시오.
- 구체적이고 레이블이 명확한 작업을 소수만 사용합니다.
- 넓은 데스크톱 레이아웃과 좁은 모바일 레이아웃을 모두 검증합니다.

Workflow 갤러리는 Flow 봇 호스트에서 검증된 `Action.OpenUrl` 및
`Action.ToggleVisibility` 작업만 허용합니다. `Action.Submit`,
`Action.Execute` 및 서버 측 상태가 필요한 기타 작업에는 적절한 봇이나
다른 인증된 어댑터가 필요하며 갤러리 검증에서 허용되지 않습니다.

## 갤러리

공급자별 예제는 `examples/python/teams_adaptive_cards` 아래에 있습니다.

| ID | 패턴 | 보여주는 요소 |
|---|---|---|
| T00 | 시각적 계층 구조 | 이모지 헤더, 의미론적 색상, 간결한 콜아웃 |
| T01 | 메트릭 대시보드 | 유연한 2열 메트릭 타일 |
| T02 | 히어로 이미지 | 반응형 이미지, 대체 텍스트, 캡션, 대체 콘텐츠 |
| T03 | 점진적 공개 | `Action.ToggleVisibility` 및 `Action.OpenUrl` |
| T04 | 사용자 멘션 | `<at>` 텍스트 및 Teams 멘션 엔터티 |
| T05 | 진행 타임라인 | 완료, 활성 및 대기 중인 시각적 상태 |
| T06 | 이미지 갤러리 | 출처가 명시된 저장소 호스팅 샘플 이미지 세 개 |

`examples/python`에서 카드를 렌더링합니다.

```shell
uv run python teams_adaptive_cards/01_metrics_dashboard/teams.py
```

구성된 빈 상태 기반 Workflow를 통해 전송합니다.

```shell
uv run python teams_adaptive_cards/01_metrics_dashboard/teams.py --send
```

이미지 중심 예제를 전송하려면 `EXAMPLE_ASSET_BASE_URL`이 필요합니다.
기존 `TEAMS_ASSET_BASE_URL` 이름은 호환되는 대체 값으로 유지됩니다. 직접
HTTPS CDN 또는 GitHub 원시 URL을 통해 게시된
`teams_adaptive_cards/assets` 디렉터리를 가리키도록 설정합니다. T04에는
`TEAMS_TEST_USER_ID`와 `TEAMS_TEST_USER_NAME`이 필요합니다. 이러한 런타임
값은 무시되는 `.env` 또는 승인된 비밀/구성 저장소에 두어야 하며 픽스처에는
절대로 두어서는 안 됩니다.
동일한 값이 Adaptive Card `<at>` 토큰 및 Teams 멘션 엔터티와 일치해야
하므로 표시 이름은 `<`, `>` 또는 `&`가 없는 일반 텍스트여야 합니다.

커밋된 고양이 이미지는 CC BY 4.0에 따라 MicrosoftDocs/AdaptiveCards
저장소에서 가져왔습니다. 원본 경로, 수정 사항 및 라이선스 링크는
[자산 저작자 표시](../examples/python/teams_adaptive_cards/assets/ATTRIBUTION.md)에
있습니다. 편집용 히어로 이미지는 MIT License에 따라 공식
OfficeDev/Microsoft-Teams-Adaptive-Card-Samples 저장소에서 변경 없이
재배포됩니다.

## Workflow 저작자 표시

카드 디자인으로 Teams **Get template** 바닥글을 제어할 수 없습니다.
갤러리 템플릿 흐름은 **Original template** 관계를 유지하며 Adaptive Card
페이로드 외부에서 바닥글을 받습니다. 저작자 표시가 없어야 할 때는
[Power Automate Teams Workflow 가이드](power-automate-teams-workflow.ko.md)의
검증된 빈 상태 기반 흐름을 사용하십시오.

## 검증

자동화된 테스트는 다음을 적용합니다.

- Teams 메시지 봉투당 유효한 Adaptive Card 첨부 파일 하나
- Adaptive Card 1.4
- 비어 있지 않은 `fallbackText` 및 `speak`
- 고정된 열 너비 없음
- 열 세 개 이하
- 비어 있지 않은 `altText`가 있는 HTTPS 이미지
- 지원되는 Webhook 작업 유형만 사용
- 최상위 작업 세 개 이하

이미지 가져오기, 멘션, 버튼 동작, 모바일 레이아웃 및 호스트별 렌더링에는 실제
검증이 여전히 필요합니다.
