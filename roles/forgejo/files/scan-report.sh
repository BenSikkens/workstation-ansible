#!/bin/sh
# scan-report - send the result of a trivy / semgrep / gitleaks run to the
# Pushgateway, so it shows up in the Grafana "Security scans" dashboard.
#
#   trivy fs --format json --output trivy.json .
#   scan-report trivy trivy.json
#
#   semgrep scan --config auto --json --output semgrep.json .
#   scan-report semgrep semgrep.json
#
#   gitleaks detect --report-format json --report-path gitleaks.json || true
#   scan-report gitleaks gitleaks.json
#
# Baked into the Forgejo CI image (label `scan`) by Ansible. It NEVER sends the
# content of a finding, only rule, file, line and package: secrets that
# gitleaks/trivy matched stay out of the monitoring stack.
#
# Environment (set by the image / Forgejo Actions):
#   SCAN_REPORT_PUSHGATEWAY    e.g. http://pushgateway:9091 ; empty = do nothing
#   SCAN_REPORT_REPO           repository id; default $GITHUB_REPOSITORY
#   SCAN_REPORT_MAX_FINDINGS   individual findings to list (default 200); the
#                              per-severity counts always cover everything
#   SCAN_REPORT_DRY_RUN=1      print the metrics instead of pushing them
#   SCAN_REPORT_STRICT=1       exit non-zero when pushing fails (default: warn)
#
# Each push REPLACES the previous result for the same repository and tool, so
# findings that were fixed disappear on the next scan.

set -eu

usage() {
  echo "usage: scan-report <trivy|semgrep|gitleaks> <report.json>" >&2
  exit 2
}

[ $# -eq 2 ] || usage
TOOL=$1
REPORT=$2
case "$TOOL" in
  trivy | semgrep | gitleaks) ;;
  *) usage ;;
esac
[ -r "$REPORT" ] || { echo "scan-report: cannot read $REPORT" >&2; exit 2; }

URL=${SCAN_REPORT_PUSHGATEWAY:-}
DRY=${SCAN_REPORT_DRY_RUN:-0}
STRICT=${SCAN_REPORT_STRICT:-0}
MAX=${SCAN_REPORT_MAX_FINDINGS:-200}
REPO=${SCAN_REPORT_REPO:-${GITHUB_REPOSITORY:-${FORGEJO_REPOSITORY:-unknown}}}

if [ -z "$URL" ] && [ "$DRY" != 1 ]; then
  echo "scan-report: no Pushgateway configured (SCAN_REPORT_PUSHGATEWAY is empty); skipping" >&2
  exit 0
fi

# Soft failure: a monitoring problem must not turn a green pipeline red.
fail() {
  echo "scan-report: $1" >&2
  [ "$STRICT" = 1 ] && exit 1
  exit 0
}

COMMIT=${GITHUB_SHA:-}
REF=${GITHUB_REF_NAME:-}
NOW=$(date +%s)

if ! BODY=$(jq -r \
  --arg tool "$TOOL" \
  --argjson max "$MAX" \
  --argjson now "$NOW" \
  --arg commit "$COMMIT" \
  --arg ref "$REF" '
  # --- normalisation -------------------------------------------------------
  def norm:
    (. // "unknown") | tostring | ascii_downcase
    | if . == "critical" or . == "high" or . == "medium" or . == "low" then .
      else "info" end;
  def semgrep_norm:
    (. // "") | tostring | ascii_downcase
    | if . == "critical" then "critical"
      elif . == "error" or . == "high" then "high"
      elif . == "warning" or . == "medium" then "medium"
      elif . == "low" or . == "info" then "low"
      else "info" end;
  def rank: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}[.];

  # Prometheus label value: no control characters, max 200 chars, and
  # backslash / double quote escaped (JSON string escaping is identical).
  def lbl: tostring | gsub("[\u0000-\u001f\u007f]"; " ") | .[0:200] | tojson | .[1:-1];

  # --- one normalised list of findings, per tool -------------------------------
  (
    if $tool == "trivy" then
      [ (.Results // [])[] | (.Target // "") as $t | (
          ((.Vulnerabilities // [])[] | {
             sev: (.Severity | norm), rule: (.VulnerabilityID // "unknown"),
             file: $t, line: "",
             pkg: ((.PkgName // "") + (if .InstalledVersion then "@" + .InstalledVersion else "" end)),
             fixed: (.FixedVersion // "") }),
          ((.Secrets // [])[] | {
             sev: (.Severity | norm), rule: (.RuleID // "secret"),
             file: $t, line: ((.StartLine // "") | tostring), pkg: "", fixed: "" }),
          ((.Misconfigurations // [])[] | select((.Status // "FAIL") == "FAIL") | {
             sev: (.Severity | norm), rule: (.ID // "misconfiguration"),
             file: $t, line: "", pkg: "", fixed: "" })
        ) ]
    elif $tool == "semgrep" then
      [ (.results // [])[] | {
          sev: (.extra.severity | semgrep_norm), rule: (.check_id // "unknown"),
          file: (.path // ""), line: ((.start.line // "") | tostring), pkg: "", fixed: "" } ]
    else
      # gitleaks: a top-level array (or null when clean). A leaked secret is
      # always reported as "high"; only rule, file and line are kept.
      [ (. // [])[] | {
          sev: "high", rule: (.RuleID // "secret"),
          file: (.File // ""), line: ((.StartLine // "") | tostring), pkg: "", fixed: "" } ]
    end
  ) as $all

  | ($all | unique_by([.sev, .rule, .file, .line, .pkg])
          | sort_by([(.sev | rank), .rule, .file, .line])) as $uniq
  | ($uniq | .[0:$max]) as $listed

  | (
      ["# TYPE scan_findings gauge"]
      + [ ["critical", "high", "medium", "low", "info"][] as $s
          | "scan_findings{severity=\"\($s)\"} \([$uniq[] | select(.sev == $s)] | length)" ]
      + ["# TYPE scan_findings_truncated gauge",
         "scan_findings_truncated \(if ($uniq | length) > $max then 1 else 0 end)"]
      + ["# TYPE scan_finding_info gauge"]
      + [ $listed[]
          | "scan_finding_info{severity=\"\(.sev)\",rule=\"\(.rule | lbl)\",file=\"\(.file | lbl)\",line=\"\(.line | lbl)\",pkg=\"\(.pkg | lbl)\",fixed=\"\(.fixed | lbl)\"} 1" ]
      + ["# TYPE scan_last_run_timestamp_seconds gauge",
         "scan_last_run_timestamp_seconds \($now)",
         "# TYPE scan_run_info gauge",
         "scan_run_info{commit=\"\($commit | lbl)\",ref=\"\($ref | lbl)\"} 1"]
    ) | join("\n")
' "$REPORT"); then
  fail "could not read $REPORT as a $TOOL report; nothing pushed"
fi

COUNTS=$(printf '%s\n' "$BODY" | sed -n 's/^scan_findings{severity="\([a-z]*\)"} \([0-9]*\)$/\1=\2/p' | tr '\n' ' ')

if [ "$DRY" = 1 ]; then
  printf '%s\n' "$BODY"
  exit 0
fi

# Repository ids contain "/"; the Pushgateway grouping key wants a plain token.
REPO_KEY=$(printf '%s' "$REPO" | tr -c 'A-Za-z0-9._-' '_')

if printf '%s\n' "$BODY" | curl -fsS --max-time 15 -X PUT --data-binary @- \
  "$URL/metrics/job/forgejo_scan/repo/$REPO_KEY/tool/$TOOL"; then
  echo "scan-report: $TOOL results for $REPO pushed ($COUNTS)"
else
  fail "could not push to $URL"
fi
