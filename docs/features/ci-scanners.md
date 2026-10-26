# Security scanners in CI: semgrep, gitleaks, trivy

Tasks: `roles/forgejo/tasks/ci_image.yml`, `roles/forgejo/templates/Containerfile.j2`.
Part of the [forgejo role](../roles/forgejo.md); runs on the
[Forgejo runner](forgejo-runner.md).

Jobs run in throwaway containers, so tools installed on the host would be
invisible to them. Instead the role builds one local image,
`localhost/forgejo-ci:latest` (a `node:22-bookworm` base, so `actions/checkout`
works, plus the scanners) in `git`'s Podman storage and offers it to workflows
as the runner label `scan`:

```yaml
jobs:
  scan:
    runs-on: scan
    steps:
      - uses: actions/checkout@v4
      - run: gitleaks detect --source . --no-banner
      - run: trivy fs --exit-code 1 --severity HIGH,CRITICAL .
      - run: semgrep scan --config p/default --error
```

To show results on the Grafana dashboard as well, see
[scan results on the dashboard](scan-report.md).

## Choosing the tools

In `group_vars/all.yml` (default: all `true`):

```yaml
forgejo_runner_install_semgrep: true
forgejo_runner_install_gitleaks: true
forgejo_runner_install_trivy: true
```

Set one to `false`, re-run the playbook, and the image is rebuilt without that
tool. If all three are `false`, nothing is built and the `scan` label is
dropped from the runner. A previously built image stays in Podman storage;
remove it with `sudo -u git podman rmi localhost/forgejo-ci:latest`.

## How each tool gets in

- **gitleaks** and **trivy** are static Go binaries copied out of their official
  images (`forgejo_gitleaks_image` = `docker.io/zricethezav/gitleaks:latest`,
  `forgejo_trivy_image` = `docker.io/aquasec/trivy:latest`).
- **semgrep** has no standalone binary, so it is pip-installed into a venv.

The image is built once and then reused, so scanner versions do not move on
their own. To pick up newer ones, remove the image as above and re-run the
playbook. The first build takes a few minutes. The `Containerfile` is rendered
with a backup and the image is rebuilt only when it changed or is missing.

## Behaviour to know

- Trivy downloads its vulnerability database at scan time (every job starts
  from a clean container).
- Semgrep's `--config auto` talks to semgrep.dev; a pinned ruleset such as
  `p/default`, or your own rules file, does not need to.

## Settings

| Variable | Default |
|---|---|
| `forgejo_ci_image_enabled` | true if any scanner is enabled |
| `forgejo_ci_label` | `scan` |
| `forgejo_ci_image_name` | `localhost/forgejo-ci:latest` |
| `forgejo_ci_build_dir` | `/home/git/forgejo-ci-image` |
| `forgejo_ci_base_image` | `docker.io/library/node:22-bookworm` |
