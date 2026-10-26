# Role: monitor_app

Registers **one** application with the monitoring stack. Source:
`roles/monitor_app/`. It is a helper: it is not listed in `site.yml` and has no
tag; other roles call it with `include_role`. The worked example, the steps and
troubleshooting are in [monitoring other applications](../features/monitoring-apps.md).

```yaml
- name: Work out where this role's dashboard file is
  ansible.builtin.set_fact:
    myapp_dashboard: "{{ role_path }}/files/myapp-dashboard.json"

- name: Monitor myapp
  ansible.builtin.include_role:
    name: monitor_app
  vars:
    monitor_app_name: myapp
    monitor_app_targets: ["127.0.0.1:9100"]
    monitor_app_dashboards: ["{{ myapp_dashboard }}"]
```

The `set_fact` step matters: variables passed to `include_role` are evaluated
inside `monitor_app`, where `{{ role_path }}` would point at the wrong role.

## What it writes

- `/etc/alloy/targets.d/<name>.yml`, a scrape-target file Alloy re-reads every
  30 s.
- `~monitoring/monitoring-config/app-dashboards/<name>/*.json`, a Grafana
  folder named after the app, read by the `apps` provider every 30 s.
  `${DS_PROMETHEUS}` / `${DS_LOKI}` placeholders are rewritten to this stack's
  data sources.

Dashboard folders and files are given the SELinux type `container_file_t`. The
Grafana container's `:Z` mount relabels only at container start, so files added
later would otherwise give "Permission denied" in Grafana.

If the monitoring stack is not installed, the role says so and does nothing;
run the calling role again afterwards. `monitor_app_state: absent` removes the
target file and dashboards.

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `monitor_app_name` | required | `job`/`app` label, Grafana folder, file names. Lowercase letters, digits, `-`, `_`; starts with a letter |
| `monitor_app_state` | `present` | `absent` removes |
| `monitor_app_targets` | `[]` | `host:port` as seen from this machine |
| `monitor_app_metrics_path` | `/metrics` | |
| `monitor_app_scheme` | `http` | or `https` |
| `monitor_app_labels` | `{}` | extra labels on every series |
| `monitor_app_dashboards` | `[]` | dashboard JSON files on the Ansible side |
| `monitor_app_fix_datasources` | `true` | rewrite `${DS_...}` placeholders |
| `monitor_app_user` | `monitoring` | |
| `monitor_app_config_dir` | `/home/<user>/monitoring-config` | |
| `monitor_app_targets_dir` | `/etc/alloy/targets.d` | |

## Used by

- the [monitoring](monitoring.md) role, for [cv-microfrontend](../features/cv-microfrontend.md);
- `examples/demo_metrics/`, the worked example.

Projects that only bring dashboards do not need it: see
[homelab add monitoring](../features/homelab-add-monitoring.md).
