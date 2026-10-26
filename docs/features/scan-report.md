# Scan results on the Grafana dashboard (`scan-report`)

Script: `roles/forgejo/files/scan-report.sh`, baked into the
[CI image](ci-scanners.md). Dashboard: **Security scans** in the *Homelab*
folder of [monitoring](../roles/monitoring.md).

The CI image (label `scan`) ships a helper, `scan-report`, and knows where the
Pushgateway is (reached over the internal `forgejo` Podman network, not a
published port). Have the scanner write JSON, then report it:

```yaml
jobs:
  scan:
    runs-on: scan
    steps:
      - uses: actions/checkout@v4
      - run: |
          trivy fs --format json --output trivy.json .
          scan-report trivy trivy.json
      - run: |
          semgrep scan --config p/default --json --output semgrep.json .
          scan-report semgrep semgrep.json
      - run: |
          gitleaks detect --no-banner --report-format json --report-path gitleaks.json || true
          scan-report gitleaks gitleaks.json
```

## Where the numbers go

The metrics are `scan_findings{severity}`, `scan_finding_info{...}` (one series
per finding), `scan_last_run_timestamp_seconds` and `scan_run_info`.
The Pushgateway (a container under `git`, set up by the monitoring role only
when Forgejo is installed) holds the latest result per repository and tool.
Alloy scrapes it and Prometheus stores it; Grafana shows current findings per
severity, per repository and tool, a history graph and a table of individual
findings (rule, file, line, package, fixed version) with filters.

## Behaviour

- Each push **replaces** the previous result for that repository and tool, so
  fixed findings disappear on the next scan. The history graph shows how the
  counts moved.
- Only rule, file, line and package are sent. **Never the matched text**, so a
  secret found by gitleaks does not end up in Grafana or Loki.
- It never fails your pipeline: if the Pushgateway is down it prints a warning
  and exits 0 (`SCAN_REPORT_STRICT=1` changes that). A scan that finds issues
  still passes or fails as the scanner's own exit code decides; run the scanner
  with `|| true`, as above, if you only want reporting.
- At most 200 findings per scan are listed individually
  (`SCAN_REPORT_MAX_FINDINGS`); the per-severity counts always cover all.
- `SCAN_REPORT_DRY_RUN=1 scan-report trivy trivy.json` prints what would be sent.

## If results do not appear

1. Is the Pushgateway running? `homelab status monitoring` lists it. It only
   exists when Forgejo was installed before the monitoring role ran; if not,
   re-run `ansible-playbook site.yml --tags monitoring --ask-become-pass`.
2. Run the job step with `SCAN_REPORT_DRY_RUN=1` to see what would be sent.
3. In Grafana *Explore* (data source Prometheus), query `scan_findings`. The
   metrics are pushed under the Pushgateway job `forgejo_scan` (grouped by
   repository and tool). If there is nothing, Alloy is not scraping the
   Pushgateway (`sudo journalctl -u alloy -e`).
