# 중앙 라우터 SQLite 데이터 모델

[English](central-router-sqlite-data-model.md)

이 문서에서는 선택적 중앙 알림 라우터가 경로, 알림 및 대상별 전송 상태를
SQLite에 저장하는 방법을 설명합니다. 테이블 정의의 기준은
[`SqliteRouteStore._initialize()`](../examples/python/src/pyhookkit/adapters/outbound/sqlite_route_store.py#L405-L454)입니다.

## 데이터베이스 생성 및 위치

`notification_router` 명령에 `--database`로 지정한 경로가 데이터베이스
위치입니다. 문서의 기본 예제는 `examples/python/.local/router.sqlite3`을
사용합니다. `SqliteRouteStore`가 처음 열릴 때 필요한 테이블과 인덱스를
자동으로 만들고 데이터베이스 파일 권한을 `0600`으로 설정합니다.

SQLite 연결은 외래 키 검사를 활성화하고 WAL 모드를 사용합니다. 실행 중인
데이터베이스를 백업할 때는 SQLite 백업 API를 사용하거나 프로세스를 중지한
후 데이터베이스와 관련 WAL 파일을 함께 처리하세요.

> [!NOTE]
> SQLite는 단일 프로세스 예제를 위한 기본 구현입니다. 조직에서 PostgreSQL,
> SQL Server 등 선호하는 DB가 있으면 이 데이터 모델을 참고하여 대체할 수
> 있습니다. 현재 저장소에는 SQLite 어댑터만 있으므로 `--database`에 다른 DB
> 연결 문자열을 넣는 것만으로는 전환되지 않습니다. 새 저장소 어댑터를
> [`NotificationRouteStore`](../examples/python/src/pyhookkit/ports/notification_routing.py#L15-L51)에
> 맞게 구현하고 구성 루트에 연결해야 합니다. 알림과 대상 레코드의 원자적
> 생성, `(producer, event_id)` 멱등성, 대상별 상태, 전송 임대 및 외래 키
> 무결성은 동일하게 유지하세요.

## 테이블 관계

```text
route_destinations 1 ───< target_deliveries >─── 1 routed_notifications
      알림 대상                대상별 전송              정규 알림

producer_api_keys                    inbound_integrations
범위 제한 자격 증명 다이제스트       공급자 라우팅 및 비밀 참조
```

하나의 정규 알림은 해당 경로에서 활성화된 각 대상에 하나의
`target_deliveries` 레코드를 만듭니다.

## `route_destinations`

채널별 알림 대상과 공급자 라우팅 메타데이터를 저장합니다.

| 열 | 제약 조건 | 의미 |
|---|---|---|
| `target_id` | 기본 키 | 대상의 소문자 kebab-case 식별자 |
| `route` | 필수 | 정규 알림의 논리 경로 |
| `provider` | 필수 | `slack` 또는 `teams-workflow` |
| `endpoint_environment_variable` | 필수 | 실제 자격 증명이 아니라 URL을 참조할 환경 변수 이름 |
| `channel_link` | 선택 | 등록된 Teams 채널 링크. Slack 대상에서는 `NULL` |
| `tenant_id` | 선택 | 채널 링크에서 파생한 Teams 테넌트 ID |
| `team_id` | 선택 | 채널 링크의 `groupId`에서 파생한 Team ID |
| `channel_id` | 선택 | 채널 링크에서 파생한 Teams 채널 ID |
| `channel_name` | 선택 | 채널 링크에서 파생한 채널 표시 이름 |
| `membership_type` | 선택 | Graph에서 확인한 `standard` 또는 `private` 채널 유형 |
| `enabled` | `0` 또는 `1` | 대상 활성화 상태 |

`(route, enabled)` 인덱스는 알림을 제출할 때 활성 대상을 찾는 데 사용됩니다.
대상 등록은 `target_id`가 같으면 기존 레코드를 갱신합니다.

## `routed_notifications`

중앙 라우터가 수락한 공급자 중립 알림을 저장합니다.

| 열 | 제약 조건 | 의미 |
|---|---|---|
| `notification_id` | 기본 키 | 라우터가 생성한 알림 UUID |
| `producer` | 필수 | 알림을 제출한 생성자 이름 |
| `event_id` | 필수 | 생성자가 제공한 멱등성 ID |
| `payload_json` | 필수 | 검증된 정규 알림 JSON |
| `created_at` | 필수 | UTC 생성 시각 |

`(producer, event_id)`는 고유합니다. 같은 생성자와 `event_id`로 동일한
페이로드를 다시 제출하면 기존 알림을 반환하고, 다른 페이로드를 제출하면
충돌로 거부합니다.

## `target_deliveries`

알림 대상마다 독립적인 전송 상태를 저장합니다.

| 열 | 제약 조건 | 의미 |
|---|---|---|
| `notification_id` | 복합 기본 키, 외래 키 | `routed_notifications`의 알림 |
| `target_id` | 복합 기본 키, 외래 키 | `route_destinations`의 대상 |
| `state` | 필수 | `queued`, `delivering`, `succeeded`, `failed` 중 하나 |
| `attempts` | 0 이상 | 완료된 전송 시도 횟수 |
| `error_kind` | 선택 | 민감 정보가 제거된 안정적인 오류 분류 |
| `status_code` | 선택 | 공급자가 반환한 HTTP 상태 코드 |
| `locked_at` | 선택 | 워커가 전송을 임대한 시각 |
| `updated_at` | 필수 | 마지막 상태 변경 시각 |

`(state, updated_at)` 인덱스는 처리할 전송과 만료된 임대를 찾는 데
사용됩니다. 워커는 `queued`를 `delivering`으로 임대하고, 만료된 임대는 다시
`queued`로 돌립니다. 완료 후 상태는 `succeeded` 또는 `failed`가 됩니다.
따라서 전송 보장은 최소 1회이며, 공급자 성공 직후 프로세스가 중단되면
메시지가 중복될 수 있습니다.

## `producer_api_keys`

서버에서 발급한 API 키의 복원할 수 없는 SHA-256 다이제스트와 민감 정보가
제거된 수명 주기 메타데이터를 저장합니다. `key_id`는 목록에 표시할 수 있지만
원문 `phk_` 값은 발급할 때 한 번만 반환합니다. 키는 하나의 `route` 또는
하나의 `target_id`로 제한합니다. `revoked_at`은 키를 비활성화하고
`last_used_at`은 요청 내용을 보존하지 않고 운영 상태를 확인하는 데
사용합니다.

## `inbound_integrations`

공급자, 생산자, 고정 경로, 선택적 대상, 필요한 경우 Basic 사용자 이름 및
공급자 인증 비밀이 있는 환경 변수 이름을 저장합니다. GitHub Webhook secret,
GitLab signing token 또는 Azure DevOps Basic password 원문은 저장하지
않습니다. `last_received_at`에는 인증에 성공한 이벤트의 수신 시각만
기록합니다.

## 초기화와 마이그레이션

외부 SQL 마이그레이션 파일이나 스키마 버전 테이블은 없습니다. 시작할 때
`CREATE TABLE IF NOT EXISTS`로 구조를 확인하고, 이전 데이터베이스의
`route_destinations`에 Teams 메타데이터 열이 없으면 자동으로 추가합니다.
자세한 구현은
[`_migrate_destination_metadata()`](../examples/python/src/pyhookkit/adapters/outbound/sqlite_route_store.py#L456-L493)을
참조하세요.

스키마 변경 전에는 데이터베이스를 백업하고 새 코드로 `doctor`를 실행하여
경로와 멤버십을 검증하세요. 실행 중인 데이터베이스를 직접 수정하지 마세요.

## 저장되는 데이터와 보안

SQLite에는 다음 비밀을 저장하지 않습니다.

- Slack Webhook URL
- 서명된 Teams Workflow URL
- 라우터 생산자 API 키 원문
- 공급자 Webhook signing secret 및 Basic password
- `TeamsNotifyApp` 클라이언트 비밀

대상 및 인바운드 통합 레코드에는 환경 변수 이름만 저장합니다. 서버가 발급한
생산자 키는 256비트 임의 값이므로 SHA-256 다이제스트만 저장해도 원문을
복원할 수 없습니다. 공급자 비밀과 기존 생산자 토큰은 저장소 루트의 Git에서
제외된 `.env` 또는 배포 비밀 저장소에 둡니다.

SQLite에는 Teams 채널 링크와 정규 알림의 `payload_json`이 저장됩니다.
알림 본문에 비밀이나 불필요한 개인정보를 넣지 마세요. 현재 예제에는 자동
보존 기간이나 삭제 작업이 없으므로 운영 환경에서는 조직의 데이터 보존
정책에 맞는 정리 절차를 별도로 설계해야 합니다.

## 실제 스키마 확인

외부 `sqlite3` CLI 없이 Python 표준 라이브러리로 DDL만 확인할 수 있습니다.
`examples/python`에서 다음 명령을 실행합니다. 이 명령은 행 데이터나 자격
증명을 출력하지 않습니다.

```shell
python3 - <<'PY'
import sqlite3
from pathlib import Path

path = Path(".local/router.sqlite3").resolve()
with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
    rows = connection.execute(
        """
        SELECT type, name, sql
        FROM sqlite_master
        WHERE type IN ('table', 'index') AND sql IS NOT NULL
        ORDER BY type DESC, name
        """
    )
    for object_type, name, sql in rows:
        print(f"-- {object_type}: {name}\n{sql};\n")
PY
```

## 관련 정보

- [중앙 알림 라우터](central-notification-router.ko.md)
- [TeamsNotifyApp 부트스트랩](teams-notify-app-bootstrap.ko.md)
- [보안 가이드](security.ko.md)
