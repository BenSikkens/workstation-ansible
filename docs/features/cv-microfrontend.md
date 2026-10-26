# Monitoring cv-microfrontend on k3s

Part of the [monitoring role](../roles/monitoring.md): `tasks/cv_microfrontend.yml`
and the last block of `templates/config.alloy.j2`.

Two independent pieces, both optional and both switched on by a file existing:

## 1. Metrics and logs of the pods (Alloy)

If `/etc/alloy/k3s-cv-metrics.kubeconfig` exists when the monitoring role runs,
Alloy also collects the `cv-microfrontend` namespace of k3s:

- metrics from pods annotated `prometheus.io/scrape: "true"` (job `k3s-pods`,
  scraped on the pod IP, metrics port 9100 by default);
- all container logs (Loki label `source="k3s"`), read through the Kubernetes
  API with a read-only service account.

Without the file nothing is added to the Alloy config.

Set up:

1. Create the kubeconfig with the CV project's `scripts/metrics-kubeconfig.sh`.
2. Make it readable by the `alloy` user, for example `root:alloy`, mode `0640`.
3. Make sure k3s is running: `homelab up k3s`.
4. `ansible-playbook site.yml --tags monitoring --ask-become-pass`.

## 2. The application dashboard

If the dashboard file exists, the monitoring role registers it through
[monitor_app](../roles/monitor_app.md) as a Grafana folder `cv-microfrontend`.
Default file:
`/home/<desktop_user>/Repositories/cv-microfrontend/monitoring/cv-application-dashboard.json`.
If the file is missing the step is skipped. The same dashboard can also be
added without Ansible via [homelab add monitoring](homelab-add-monitoring.md).

## Settings

In `roles/monitoring/defaults/main.yml`:

| Variable | Default |
|---|---|
| `monitoring_k3s_cv_kubeconfig` | `/etc/alloy/k3s-cv-metrics.kubeconfig` |
| `monitoring_k3s_cv_namespace` | `cv-microfrontend` |
| `monitoring_k3s_cv_metrics_port` | `9100` (dropped from the log targets so each log is read once) |
| `monitoring_cv_dashboard` | path above |

## Troubleshooting

- Dashboard folder empty or "Permission denied" in Grafana: the files need the
  SELinux type `container_file_t`. `monitor_app` sets it; for files placed by
  hand run `sudo chcon -R -t container_file_t <folder>`.
- No logs/metrics: check `sudo journalctl -u alloy -e` and Alloy's debug page
  (`http://127.0.0.1:12345`).
