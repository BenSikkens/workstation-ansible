# Role: monitoring

Grafana, Prometheus and Loki, fed by Grafana Alloy, per-user Podman exporters
and a Pushgateway. Tag: `monitoring`. Source: `roles/monitoring/`. Skip it
entirely with `monitoring_enabled: false` in `group_vars/all.yml` (nothing
already installed is removed). Everything listens on `127.0.0.1`.

## Components

| Piece | Runs as | Job |
|---|---|---|
| Grafana | container, user `monitoring` | the dashboards, `http://localhost:3001` |
| Prometheus | container, user `monitoring` | metrics database (30 days) |
| Loki | container, user `monitoring` | log database (14 days) |
| Pushgateway | container, user `git` | holds the latest [scan results](../features/scan-report.md) CI jobs push. Only deployed when Forgejo is installed |
| Grafana Alloy | system service (Grafana RPM repo) | collects host metrics, scrapes the exporters, the Pushgateway and the files in `/etc/alloy/targets.d/`, ships the systemd journal to Loki |
| `prometheus-podman-exporter` | systemd user service, one per Podman user (`git` and your desktop user) | per-container CPU, memory, network, disk |

## Logging in

Open `http://localhost:3001` and log in as `admin`. The password is generated on
the first run, stored as a Podman secret, and kept in a file only `monitoring`
and root can read:

```bash
sudo cat /home/monitoring/.grafana-admin-password
```

## Dashboards

Three dashboards are provisioned into the *Homelab* folder from
`roles/monitoring/files/dashboards/`. They are read-only in the UI; use *Save
as* for your own copy, because changes are overwritten by the playbook.

- **Security scans** (`security-scans.json`): current findings per severity, per
  repository and tool, a history graph and a table of the individual findings
  with filters. Fed by [scan-report](../features/scan-report.md).
- **Containers** (`containers.json`): state, CPU, memory, network in/out and disk
  I/O per container, for every monitored Podman user.
- **Host and logs** (`host-and-logs.json`): CPU, memory, disk, load, host
  network traffic, log volume by level and a searchable log view with container
  and unit filters (including an "errors and failures" panel).

Two Grafana providers are configured: `homelab` (the three above) and `apps`
(everything under `monitoring-config/app-dashboards/`, one folder per app,
registered by [monitor_app](monitor_app.md) or
[homelab add monitoring](../features/homelab-add-monitoring.md)). Dashboard
files are re-read every 30 s; data source files are read only when Grafana
starts.

## What it does, in order

1. Installs podman dependencies; creates the `monitoring` user with lingering and
   a running systemd user manager.
2. Creates the config directories and renders Prometheus' and Loki's config, the
   Grafana data sources (`prometheus`, `loki`) and dashboard providers;
   installs the dashboards.
3. Generates the Grafana admin password (once) and stores it as a Podman secret.
4. Deploys the Quadlet units (network, Prometheus, Loki, Grafana) and starts
   them; restarts Grafana when its configuration changed.
5. `tasks/agents.yml`: Pushgateway (if Forgejo exists), Podman exporters (for
   users that exist), Grafana's RPM repository and key, Alloy, the journal
   access for the `alloy` user, `/etc/alloy/targets.d`, the Alloy config, and
   starts Alloy.
6. `tasks/cv_microfrontend.yml`: the [cv-microfrontend](../features/cv-microfrontend.md)
   dashboard, if its file exists.

## Settings (`roles/monitoring/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `monitoring_user` | `monitoring` | service user |
| `monitoring_grafana_image` / `_prometheus_image` / `_loki_image` / `_pushgateway_image` | `grafana:13.0`, `prom/prometheus:v3.14.0`, `loki:3.7.7`, `pushgateway:v1.11.4` | bump deliberately; Grafana and Loki migrate their data forward |
| `monitoring_grafana_port` | `3001` | |
| `monitoring_prometheus_port` | `9094` | not 9090: Cockpit uses it |
| `monitoring_loki_port` / `monitoring_pushgateway_port` | `3100` / `9091` | |
| `monitoring_prometheus_retention` | `30d` | |
| `monitoring_loki_retention` | `336h` | 14 days |
| `monitoring_podman_exporters` | `git` on 9882, desktop user on 9883 | Podman users whose containers are graphed |
| `monitoring_podman_exporters_extra` | `[]` | more users, `{user: nextcloud, port: 9884}`; see [monitoring other applications](../features/monitoring-apps.md) |
| `monitoring_config_dir` | `/home/monitoring/monitoring-config` | generated config, bind-mounted read-only |
| `monitoring_alloy_repo_baseurl` / `_gpgkey` | `https://rpm.grafana.com` | |
| `monitoring_k3s_cv_*`, `monitoring_cv_dashboard` | see [cv-microfrontend](../features/cv-microfrontend.md) | |

## Not covered

- Monitoring data is **not** part of the [Forgejo backup](../features/forgejo-backup.md).
  It lives in the `monitoring` user's Podman volumes (`prometheus-data`,
  `loki-data`, `grafana-data`); losing it loses history only.
- Container logs are read from the systemd journal, where Quadlet services
  already write. Containers started by hand (`podman run`) are in the journal
  only if they use the journald log driver.
- Grafana has no TLS and is not exposed beyond localhost; see
  [networking](../features/networking.md).
- k3s workloads other than cv-microfrontend.

## Related

- [Monitoring other applications](../features/monitoring-apps.md)
- [monitor_app](monitor_app.md)
- `homelab up|down monitoring` ([homelab command](../features/homelab-command.md))
