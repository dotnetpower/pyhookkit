# 시작하기

[English](getting-started.md)

## 로컬 공급자 구성

무시되는 로컬 구성 파일을 생성합니다.

```shell
cp .env.example .env
```

[공급자 구성](configuration.ko.md)의 설명에 따라 `SLACK_WEBHOOK_URL`,
`TEAMS_WORKFLOW_URL`, `TEAMS_WORKFLOW_CHANNEL_LINK`를 입력합니다. 처음의
렌더링 전용 예제는 이 값들이 비어 있어도 실행할 수 있습니다.

## PyHookKit을 설치하지 않고 실행

F00 부트스트랩 예제는 Python 표준 라이브러리만 사용하여 원시 공급자 HTTP
요청을 보여 줍니다.

```shell
cd examples/python
python fundamentals/00_http_request/slack.py
python fundamentals/00_http_request/teams.py
```

명령은 기본적으로 공급자 페이로드를 렌더링합니다. `.env`를 로드한 후 둘 중
하나를 의도적으로 배달하려면 `--send`를 추가합니다.

## PyHookKit 쌍 예제 실행

라이브러리를 사용하는 첫 번째 예제는
`examples/python/fundamentals/01_hello_world` 아래에 있습니다.

`examples/python`에서 Python 개발 의존성을 설치한 다음 쌍으로 구성된 Slack
및 Teams 스크립트를 실행합니다. 예제는 합성 페이로드를 사용하며 실제 자격
증명이 필요하지 않습니다.

```shell
cd examples/python
uv sync --extra dev --python 3.12
uv run python fundamentals/01_hello_world/slack.py
uv run python fundamentals/01_hello_world/teams.py
```

Slack F01-F07과 F10은 `.env`가 로드된 후 `--send`도 허용합니다. 멘션,
스레드 또는 변경 예제를 전송하기 전에 [Slack 예제](slack-examples.ko.md)를
참조하세요.

Teams 예제를 전송하기 전에 빈 상태에서
[Power Automate Teams 워크플로](power-automate-teams-workflow.ko.md)를
생성합니다. Teams 예제는 실제 자격 증명 없이 렌더링되며 `--send` 또는
`--send-logic-app`이 지정된 경우에만 전송됩니다.

GitHub, GitLab, Argo CD, AKS 전체 데모는
[통합 Bookinfo 시나리오](integrated-bookinfo-scenario.ko.md)를 따르세요.
