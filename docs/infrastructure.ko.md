# 인프라

[English](infrastructure.md)

인프라 자산은 구현 언어와 독립적입니다. 선언적 구성은 `infra` 아래에 두고,
OAuth 동의, 생성된 자격 증명 및 기타 명령형 단계는 명시적인 부트스트랩
런북에 둡니다.

자격 증명, 콜백 URL, 상태 및 실제 환경 매개 변수는 커밋하면 안 됩니다.

Teams Workflow 인프라는 한 번 작성하고 ALM을 반복하는 모델을 따릅니다.
빈 상태에서 검증된 흐름을 Power Platform Solution에 넣고 Power Platform
CLI로 배포하며 연결 참조와 환경 변수를 사용해 구성해야 합니다. 생성된 콜백
URL은 활성화 후 가져와서 비밀 저장소에 직접 기록합니다.

헤드리스 배포 로드맵과 템플릿 바닥글 검증 체크리스트는
[Teams Workflows 런북](../infra/teams-workflows/README.md)을 참조하세요.

## AKS Bookinfo 알림 환경

통합 예제는 Istio를 설치하지 않고 Bookinfo를 소규모 다중 서비스
워크로드로 사용합니다. GitHub는 배포 승인을, GitLab은 CI와 알림 발송을,
Argo CD는 AKS 조정을 담당합니다. 이렇게 하면 공급자 자격 증명이 GitHub,
Argo CD 템플릿 및 Bookinfo 네임스페이스에 들어가지 않습니다. Teams 콜백
자격 증명은 보호된 GitLab 변수로만 존재합니다.

플랫폼 경계를 넘는 것은 표준 JSON입니다. GitHub, Argo CD 및 클러스터 내
프로브는 Slack 또는 Teams 페이로드를 만들지 않습니다. GitLab 작업이 표준
입력을 검증하고 쌍 예제에서 사용하는 것과 동일한 PyHookKit 렌더러를
호출합니다.

다음 순서로 부트스트랩합니다.

1. 최소 [AKS 클러스터](../infra/azure/bicep/README.md)를 프로비저닝합니다.
2. [Bookinfo GitOps 자산](../infra/gitops/bookinfo/README.md)으로 GitLab
   프로젝트를 생성합니다.
3. [GitLab 파이프라인](../infra/integrations/gitlab/README.md)을 구성합니다.
4. [Argo CD](../infra/integrations/argocd/README.md)를 설치하고 구성합니다.
5. 보호된 [GitHub 승인 워크플로](../infra/integrations/github/README.md)를
   추가합니다.
6. 빈 상태에서 [Power Automate Teams 워크플로](power-automate-teams-workflow.ko.md)를
   구성합니다.

첫 번째 반복에서는 전체 Prometheus 스택 대신 내부 상태 프로브를
의도적으로 사용합니다. Argo CD, Istio, 관리형 모니터링, Key Vault CSI 및
비공개 이벤트 서비스는 각각의 기능이 실제로 필요할 때 독립적으로 도입할 수
있습니다.

전체 실행 순서와 민감 정보가 제거된 실제 캡처는
[통합 Bookinfo 시나리오](integrated-bookinfo-scenario.ko.md)에 있습니다.
Power Automate는 기본 배달 어댑터로 유지되며,
[Logic App Teams 배달 가이드](logic-app-teams-delivery.ko.md)는 선택적인
라우팅 어댑터를 설명합니다.
