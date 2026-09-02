#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: deploy-solution.sh [options]

Required:
  --solution-folder PATH
  --solution-zip PATH
  --package-type Unmanaged|Managed|Both
  --environment URL_OR_ID
  --teams-connection-id ID
  --team-schema-name NAME
  --team-id GUID
  --channel-schema-name NAME
  --channel-id ID

Optional ownership verification:
  --flow-id GUID
  --application-id GUID
  Requires DATAVERSE_ACCESS_TOKEN in the environment.

Optional channel inventory:
  --channel-report PATH
  --include-incoming
  Requires MICROSOFT_GRAPH_ACCESS_TOKEN in the environment.

Optional live delivery:
  --smoke-test
  Requires TEAMS_WORKFLOW_URL in the environment.
EOF
}

solution_folder=""
solution_zip=""
package_type=""
environment=""
teams_connection_id=""
team_schema_name=""
team_id=""
channel_schema_name=""
channel_id=""
flow_id=""
application_id=""
channel_report=""
include_incoming=false
smoke_test=false

while (($# > 0)); do
  case "$1" in
    --solution-folder) solution_folder="${2:-}"; shift 2 ;;
    --solution-zip) solution_zip="${2:-}"; shift 2 ;;
    --package-type) package_type="${2:-}"; shift 2 ;;
    --environment) environment="${2:-}"; shift 2 ;;
    --teams-connection-id) teams_connection_id="${2:-}"; shift 2 ;;
    --team-schema-name) team_schema_name="${2:-}"; shift 2 ;;
    --team-id) team_id="${2:-}"; shift 2 ;;
    --channel-schema-name) channel_schema_name="${2:-}"; shift 2 ;;
    --channel-id) channel_id="${2:-}"; shift 2 ;;
    --flow-id) flow_id="${2:-}"; shift 2 ;;
    --application-id) application_id="${2:-}"; shift 2 ;;
    --channel-report) channel_report="${2:-}"; shift 2 ;;
    --include-incoming) include_incoming=true; shift ;;
    --smoke-test) smoke_test=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for required_name in \
  solution_folder solution_zip package_type environment teams_connection_id \
  team_schema_name team_id channel_schema_name channel_id; do
  if [[ -z "${!required_name}" ]]; then
    echo "error: --${required_name//_/-} is required" >&2
    exit 2
  fi
done

if [[ ! -d "$solution_folder" ]]; then
  echo "error: solution folder does not exist: $solution_folder" >&2
  exit 2
fi
if [[ "$package_type" != "Unmanaged" && "$package_type" != "Managed" && "$package_type" != "Both" ]]; then
  echo "error: --package-type must be Unmanaged, Managed, or Both" >&2
  exit 2
fi
if [[ -n "$flow_id" || -n "$application_id" ]]; then
  if [[ -z "$flow_id" || -z "$application_id" ]]; then
    echo "error: --flow-id and --application-id must be supplied together" >&2
    exit 2
  fi
  if [[ ! "$environment" =~ ^https://[^/]+/?$ ]]; then
    echo "error: --environment must be a Dataverse HTTPS URL for ownership assignment" >&2
    exit 2
  fi
  if [[ -z "${DATAVERSE_ACCESS_TOKEN:-}" ]]; then
    echo "error: DATAVERSE_ACCESS_TOKEN is required for ownership assignment" >&2
    exit 2
  fi
fi
if [[ -n "$channel_report" && -z "${MICROSOFT_GRAPH_ACCESS_TOKEN:-}" ]]; then
  echo "error: MICROSOFT_GRAPH_ACCESS_TOKEN is required for channel inventory" >&2
  exit 2
fi
if [[ "$smoke_test" == true && -z "${TEAMS_WORKFLOW_URL:-}" ]]; then
  echo "error: TEAMS_WORKFLOW_URL is required for the smoke test" >&2
  exit 2
fi

command -v pac >/dev/null || {
  echo "error: Microsoft Power Platform CLI (pac) is required" >&2
  exit 127
}
command -v python3 >/dev/null || {
  echo "error: Python 3.12 or newer is required" >&2
  exit 127
}
if [[ "$smoke_test" == true ]]; then
  command -v uv >/dev/null || {
    echo "error: uv is required for the smoke test" >&2
    exit 127
  }
fi

temporary_directory="$(mktemp -d)"
trap 'rm -rf -- "$temporary_directory"' EXIT
generated_settings="$temporary_directory/generated-settings.json"
prepared_settings="$temporary_directory/prepared-settings.json"

mkdir -p -- "$(dirname -- "$solution_zip")"
pac auth list >/dev/null
pac solution pack \
  --zipfile "$solution_zip" \
  --folder "$solution_folder" \
  --packagetype "$package_type"
pac solution create-settings \
  --solution-zip "$solution_zip" \
  --settings-file "$generated_settings"
python3 "$SCRIPT_DIR/prepare-deployment-settings.py" \
  --input "$generated_settings" \
  --output "$prepared_settings" \
  --teams-connection-id "$teams_connection_id" \
  --team-schema-name "$team_schema_name" \
  --team-id "$team_id" \
  --channel-schema-name "$channel_schema_name" \
  --channel-id "$channel_id"
pac solution import \
  --path "$solution_zip" \
  --environment "$environment" \
  --settings-file "$prepared_settings" \
  --publish-changes \
  --activate-plugins

if [[ -n "$flow_id" ]]; then
  python3 "$SCRIPT_DIR/set-flow-owner.py" assign \
    --environment-url "$environment" \
    --flow-id "$flow_id" \
    --application-id "$application_id"
fi

if [[ -n "$channel_report" ]]; then
  graph_arguments=(
    --team-id "$team_id"
    --output "$channel_report"
  )
  if [[ "$include_incoming" == true ]]; then
    graph_arguments+=(--include-incoming)
  fi
  python3 "$SCRIPT_DIR/list-team-channels.py" "${graph_arguments[@]}"
fi

if [[ "$smoke_test" == true ]]; then
  repository_root="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
  pushd "$repository_root/examples/python" >/dev/null
  uv run python scenarios/deployment_result/teams.py --send
  popd >/dev/null
fi

echo "Power Platform Solution deployment verified."