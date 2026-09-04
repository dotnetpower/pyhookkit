# Slack 예제

[English](slack-examples.md)

Slack 참조는 종속성 없는 HTTP 요청에서 시작하여 라이브러리 기반 렌더링을
거쳐 명시적인 Web API 경계까지 진행됩니다. `examples/python`에서 명령을
실행하십시오.

## 원시 HTTP 부트스트랩

F00은 `pyhookkit` 대신 Python 표준 라이브러리를 사용합니다. 기본적으로
요청을 렌더링하며 `--send`를 지정할 때만 전송합니다.

```shell
python fundamentals/00_http_request/slack.py
python fundamentals/00_http_request/slack.py --send
```

## 렌더링 및 전송

F01-F07과 F10은 기본적으로 JSON을 렌더링합니다.

```shell
uv run python fundamentals/03_rich_card/slack.py
```

저장소 루트의 `.env`를 로드한 후 Incoming Webhook 메시지를 의도적으로
전송하려면 `--send`를 추가합니다.

```shell
uv run python fundamentals/03_rich_card/slack.py --send
```

`SLACK_WEBHOOK_URL`이 존재하고 값을 출력하지 않은 채 Slack에 속하는지
검증하려면 `--check-route`를 사용합니다.

```shell
uv run python fundamentals/07_routing/slack.py --check-route
```

## 카탈로그

| ID | 예제 | Slack 동작 | 실제 실행 요구 사항 |
|---|---|---|---|
| F00 | 원시 HTTP 요청 | 표준 라이브러리 JSON POST | Incoming Webhook |
| F01 | Hello World | 최소 `text` 페이로드 | Incoming Webhook |
| F02 | 기본 알림 | 헤더, 본문, 심각도 색상, 타임스탬프 | Incoming Webhook |
| F03 | 리치 카드 | Block Kit 팩트 및 컨텍스트 | Incoming Webhook |
| F04 | 멘션 | 사용자 및 사용자 그룹 별칭 확인 | Incoming Webhook 및 구성된 신원 식별자 |
| F05 | 링크 및 작업 | HTTPS `button` 작업 | Incoming Webhook |
| F06 | 이미지 | 외부 HTTPS 이미지 및 대체 텍스트 | Incoming Webhook 및 공개적으로 접근 가능한 이미지 |
| F07 | 라우팅 | 엔트리포인트에서 논리적 경로 확인 | Incoming Webhook 환경 매핑 |
| F08 | 스레드 또는 답글 | 알고 있는 부모 `thread_ts` 추가 | 영구 저장된 부모 타임스탬프 |
| F09 | 업데이트 및 삭제 | `chat.update` 및 `chat.delete` 본문 렌더링 | Web API 봇 토큰, 전송은 아직 활성화되지 않음 |
| F10 | 오류 및 재시도 | 민감 정보를 제거한 분류 및 제한된 재시도 | Incoming Webhook |

## Web API 및 인바운드 작업

공급자별 운영 예제는 `examples/python/slack_operations` 아래에 있습니다.
기본적으로 드라이 런입니다.

```shell
uv run python slack_operations/00_auth_test/slack.py --live
uv run python slack_operations/01_channels/slack.py --live
uv run python slack_operations/02_identities/slack.py \
  --live --display-name example-owner
uv run python slack_operations/03_message_lifecycle/slack.py --exercise
```

확인된 멤버를 검증한 후 신원 확인 예제에 `--send-mention`을 추가할 수
있습니다.
커밋된 기본값에는 실제 표시 이름이나 Slack ID가 포함되지 않습니다.

| ID | 작업 | Slack API / 동작 |
|---|---|---|
| O00 | 인증 | 토큰을 노출하지 않는 `auth.test` |
| O01 | 채널 및 멤버 | 커서로 페이지를 나누는 `conversations.list/members` |
| O02 | 신원 검색 | `users.list`, `usergroups.list`, 선택적 멘션 |
| O03 | 메시지 수명 주기 | 보관된 `ts`를 사용한 게시, 답글, 업데이트 및 삭제 |
| O04 | 채널/브로드캐스트 멘션 | 채널 링크 및 명시적인 광범위 멘션 허용 목록 |
| O05 | 대화형 승인 | 블록 작업, HMAC 서명 및 리플레이 검증 |
| O06 | 파일 업로드 | 외부 업로드 URL, 바이너리 업로드, 완료 |
| O07 | 반응 | 처리 상태 추가/제거 |
| O08 | 예약/임시 | 예약/삭제 및 사용자 대상 임시 메시지 |
| O09 | Events HTTP | 서명된 URL 검증 및 이벤트 승인 응답 |
| O10 | Socket Mode | WebSocket 열기, 한 번 수신, 엔벌로프 확인 응답 |

비공개 채널은 토큰에 접근 권한이 있을 때만 나타납니다. 컬렉션 예제는
`next_cursor`를 따르며 API 응답 하나가 완전하다고 가정하지 않습니다.
Slack Web API 실패는 HTTP 200과 `{"ok": false}`를 반환할 수 있으므로
`chat.postMessage` 응답은 Incoming Webhook 응답과 별도로 파싱됩니다.

## 멘션 구성

커밋된 F04 출력은 합성 Slack 식별자를 사용합니다. F04를 전송하기 전에
무시되는 `.env`에 실제 테스트 ID를 설정합니다.

```dotenv
SLACK_USER_ID="<test Slack member ID>"
SLACK_USER_GROUP_ID="<test Slack user-group ID>"
```

사용자의 Slack 프로필 메뉴에서 **Copy member ID**를 사용하여 멤버 ID를
찾습니다. 승인된 디렉터리/구성 프로세스를 통해 사용자 그룹 ID를 찾습니다.
어느 변수든 비어 있으면 예제는 `--send`를 거부하므로 합성 멘션이 작동한
것처럼 조용히 가장할 수 없습니다.

정규 입력은 `example-owner`와 `example-responders`만 유지합니다. 공급자
식별자는 Slack 컴포지션 경계 내부에 남습니다.

## 스레드, 업데이트 및 삭제 경계

Incoming Webhook은 `ok`를 반환하지만 게시된 메시지 타임스탬프는 반환하지
않습니다. 따라서 F08은 이전에 저장된 합성 부모 참조를 사용한 렌더링을
보여줍니다.

F09는 의도적으로 렌더링만 수행합니다. 실제 업데이트 및 삭제 작업에는
다음이 필요합니다.

- `chat:write`가 있는 `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`
- 해당 봇이 원래 작성한 메시지에서 반환된 `ts`

다른 앱이나 사용자가 소유한 메시지에 Web API 변경 작업을 사용하지
마십시오.

## 안정성 동작

F10 대상은 다음과 같이 동작합니다.

- 명시적인 연결, 읽기, 쓰기 및 풀 타임아웃을 설정합니다.
- 지수 백오프보다 `Retry-After`를 우선합니다.
- 지터를 추가하고 지수 지연과 공급자가 지시한 대기 시간을 별도로 제한하며
  시도 횟수를 제한합니다.
- 전송 계층 오류, `429` 및 일시적인 `5xx`를 재시도합니다.
- 잘못된 페이로드, 인증, 권한 또는 영구적인 공급자 오류는 재시도하지
  않습니다.
- Webhook URL, 원시 요청 또는 응답 본문이 없는 공급자 중립적 결과를
  반환합니다.

Web API 호출은 Slack JSON 오류 코드를 분류하면서 동일하게 제한된
`Retry-After` 동작을 적용합니다. 게시 및 Incoming Webhook은 채널당 초당
약 한 개의 메시지 속도로 조절해야 하며 정확한 버스트 허용량을 가정해서는
안 됩니다.

## 대화형 및 이벤트 전송

O05는 실제 `block_actions` 버튼을 렌더링하고 변경되지 않은 요청 본문을
대상으로 Slack의 v0 HMAC 서명을 검증하는 콜백 서버를 포함합니다. O09는
Events API URL 챌린지와 콜백에 동일한 검증을 구현합니다. 둘 다 5분보다
오래된 요청을 거부합니다. O10은 방화벽 뒤에서 개발할 때 사용하는 대체
Socket Mode 경로이며 `SLACK_APP_TOKEN`이 필요합니다.

## 파일

O06은 현재 절차를 사용합니다.

1. `files.getUploadURLExternal`
2. Slack에서 발급한 `files.slack.com` URL로 바이너리 POST
3. `files.completeUploadExternal`

사용이 중단된 `files.upload` 메서드는 의도적으로 보여주지 않습니다.

## 공급자 제한

렌더러는 Slack 제한을 명시적으로 유지합니다.

- 긴 본문 텍스트는 섹션 블록으로 나눕니다.
- 팩트는 필드 열 개씩 묶어 나눕니다.
- 버튼 레이블은 75자로 제한됩니다.
- 헤더 제목은 150자로 제한됩니다.
- Slack의 필드 제한인 2,000자를 초과하는 렌더링된 `mrkdwn` 팩트는 공급자
  거부를 유발하는 대신 명시적으로 실패합니다.
- 탐색 작업은 HTTPS URL만 허용합니다.
- 이미지 대체 텍스트는 필수입니다.
- ID 매핑이 없으면 멘션을 삭제하는 대신 실패합니다.

[Slack Incoming Webhooks 문서](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks)와
[`chat.update`](https://docs.slack.dev/reference/methods/chat.update) /
[`chat.delete`](https://docs.slack.dev/reference/methods/chat.delete) 참조를
확인하십시오. 운영 예제는 공식
[`conversations.list`](https://docs.slack.dev/reference/methods/conversations.list/),
[메시지 서식](https://docs.slack.dev/messaging/formatting-message-text/),
[요청 검증](https://docs.slack.dev/authentication/verifying-requests-from-slack/),
[Socket Mode](https://docs.slack.dev/apis/events-api/using-socket-mode/) 및
[속도 제한](https://docs.slack.dev/apis/web-api/rate-limits/) 지침을
따릅니다.
