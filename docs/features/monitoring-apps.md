# Adding applications to the monitoring

How to get an application you install later into the Grafana / Prometheus /
Loki stack from this repo. Start with the worked example (section 2); the rest
is reference.

Grafana is at `http://localhost:3001`. The monitoring stack must be installed
first (`ansible-playbook site.yml --tags monitoring --ask-become-pass`).

**Shortcut for a project that only brings dashboards:** if you just have
Grafana dashboard files (and maybe a data source file) in a project folder, you
do not need a role. Run `homelab add monitoring ~/Repositories/myproject/monitoring`
and they are in Grafana within about 30 seconds (see [homelab add monitoring](homelab-add-monitoring.md)). That covers the dashboards and data
sources only; getting the application's *metrics* into Prometheus still needs
section 2 below (or a hand-written target file, section 4).

## 1. What is monitored without you doing anything

| You install... | Monitored automatically | Needs a step from you |
|---|---|---|
| a Quadlet container under `git` or your own user | container state, CPU, memory, network, disk (**Containers** dashboard) and its logs (**Host and logs**) | nothing |
| a systemd service on the host | its logs (everything in the journal), host load | its own metrics, if it has any (section 2) |
| a container under a **new** service user | its logs | add the user to `monitoring_podman_exporters_extra` (section 5) |
| an app that serves Prometheus metrics (`/metrics`) | nothing yet | register its endpoint (section 2) |
| a k3s workload | logs of k3s itself only | not covered, see section 7 |

So there are two separate things: **container and log monitoring** comes for
free, **the application's own metrics** (requests, queue length, ...) only
exist if the application serves them and you register them.

How the pieces fit: Alloy (a service on the host) scrapes every endpoint listed
in `/etc/alloy/targets.d/*.yml` and forwards the numbers to Prometheus. Grafana
reads Prometheus and shows dashboards. Registering an application means putting
one small file into `/etc/alloy/targets.d/`; Alloy re-reads that directory every
30 seconds, so nothing needs restarting.

## 2. Worked example: a new application, end to end

The repo contains a small example role, `examples/demo_metrics/`. It runs a
container that serves metrics and registers it, with a dashboard. It lives
outside `roles/` so it never runs by accident. The "application" is
`prom/statsd-exporter`, only because it is a tiny image that serves metrics
out of the box; for your own application you replace the image, the port and
the dashboard.

What the role contains:

| File | Purpose |
|---|---|
| `defaults/main.yml` | image, port, which user runs it |
| `templates/demo-metrics.container.j2` | the Quadlet unit. The important line is `PublishPort=127.0.0.1:9102:9102` |
| `tasks/main.yml` | installs and starts the container, then includes `monitoring.yml` |
| `tasks/monitoring.yml` | **the whole monitoring integration** (below) |
| `files/demo-metrics-dashboard.json` | the Grafana dashboard |

### Step 1: copy it in and enable it

```bash
cd ~/Repositories/fedora-workstation-setup
cp -r examples/demo_metrics roles/demo_metrics
```

Add it to `site.yml`, below `monitoring` (and above `homelab`), like the other
roles:

```yaml
    - { role: demo_metrics, tags: [demo_metrics] }
```

### Step 2: run just this role

```bash
ansible-playbook site.yml --tags demo_metrics --ask-become-pass
```

### Step 3: what the monitoring part does

This is all of `tasks/monitoring.yml`; copy it into your own role and change the
name, the port and the dashboard file:

```yaml
- name: Work out where the dashboard file is
  ansible.builtin.set_fact:
    demo_metrics_dashboard: "{{ role_path }}/files/demo-metrics-dashboard.json"

- name: Monitor demo-metrics
  ansible.builtin.include_role:
    name: monitor_app
  vars:
    monitor_app_name: demo-metrics
    monitor_app_targets: ["127.0.0.1:{{ demo_metrics_port }}"]
    monitor_app_dashboards: ["{{ demo_metrics_dashboard }}"]
```

- `monitor_app_name` becomes the `job` and `app` label, the Grafana folder, and
  the file names. Lowercase letters, digits, `-` and `_`, starting with a letter.
- `monitor_app_targets` is `host:port` **on this machine**. Alloy runs on the
  host, so a container must publish the port (`PublishPort=127.0.0.1:...`).
  Loopback is enough and keeps it off the network.
- `monitor_app_dashboards` is optional. Leave it out to get metrics without a
  dashboard.
- The `set_fact` step is not decoration. Variables passed to `include_role`
  are evaluated inside `monitor_app`, where `{{ role_path }}` would point at the
  wrong role, so resolve the path first.

The role only writes two things: `/etc/alloy/targets.d/demo-metrics.yml`
and `~/monitoring-config/app-dashboards/demo-metrics/demo-metrics-dashboard.json`
(under the monitoring user's home). If monitoring is not installed, it says so
and does nothing; run your role again after installing monitoring.

### Step 4: verify (allow about a minute)

```bash
ls /etc/alloy/targets.d/            # demo-metrics.yml is there
sudo journalctl -u alloy -e         # no errors about the file
curl -s http://127.0.0.1:9102/metrics | head   # the app itself serves metrics
```

In Grafana:

1. *Explore*, data source **Prometheus**, query `up{job="demo-metrics"}`.
   `1` means it is being scraped.
2. *Dashboards*: a folder **demo-metrics** with the dashboard **Demo metrics
   app**.
3. The **Containers** dashboard now also lists the `demo-metrics` container,
   with no extra work (it runs under your own user, which is monitored).

### Step 5: remove it again

Set `monitor_app_state: absent` in the `vars:` of the `monitor_app` include
and run the role once. That deletes the target file and the dashboard folder.
Stop the container itself the usual way: `systemctl --user disable --now
demo-metrics`, and delete `~/.config/containers/systemd/demo-metrics.container`.

To adapt this to a real application, change three things: the image and port in
the Quadlet, `monitor_app_name` / `monitor_app_targets`, and the dashboard file
(section 3 shows how to get one).

## 3. Getting a dashboard

You can do this in Grafana first and put it in the repo afterwards.

- **Use a ready-made one.** *Dashboards*, *New*, *Import*. Enter a dashboard ID
  from [grafana.com/grafana/dashboards](https://grafana.com/grafana/dashboards)
  or upload JSON, and pick **Prometheus** as the data source (logs: **Loki**).
- **Build your own.** *Dashboards*, *New*, *New dashboard*, *Add visualization*,
  data source **Prometheus**. Type a query, for example
  `rate(http_requests_total{job="myapp"}[5m])`, choose a visualization, *Save
  dashboard*. For logs use data source **Loki**, for example
  `{source="journal", unit=~"myapp.*"}`. The *Metrics browser* / *Label browser*
  button lists what exists.
- **Make it permanent with Ansible.** Open the dashboard, *Export*, *Export for
  sharing externally*, *Save to file*. Put the file in your role as
  `files/myapp-dashboard.json` and list it in `monitor_app_dashboards`.
  `${DS_PROMETHEUS}` / `${DS_LOKI}` placeholders in the exported file are
  pointed at this stack's data sources automatically
  (`monitor_app_fix_datasources`, on by default).

Dashboards that come from files (the three Homelab ones and everything
registered through `monitor_app`) are read-only in the UI. Edit them with *Save
as* to a copy, or change the JSON file and run the role again. Dashboards you
create or import in the UI are editable, but live only in Grafana's volume and
are lost if that is deleted. Export them (above) if you want to keep them.

## 4. Without Ansible

Create `/etc/alloy/targets.d/myapp.yml` as root:

```yaml
- targets: ["127.0.0.1:9100"]
  labels:
    app: myapp
    # __metrics_path__: /metrics     # only if it is not /metrics
    # __scheme__: https              # only if it is not plain http
```

Alloy picks it up within 30 seconds. Delete the file to stop scraping. Note the
`app` label is what gives the series `job="myapp"`. Ansible will not touch files
it did not create.

## 5. Another service user running Podman

A container under a user other than `git` or your desktop user is not seen by
the container dashboards until that user gets its own Podman exporter. Add it
in `group_vars/all.yml` with a free port (`git` uses 9882, the desktop user 9883):

```yaml
monitoring_podman_exporters_extra:
  - {user: nextcloud, port: 9884}
```

then run `ansible-playbook site.yml --tags monitoring --ask-become-pass`. Users
that do not exist are skipped.

## 6. Reference

`monitor_app` variables (defaults in `roles/monitor_app/defaults/main.yml`):

| Variable | Default | Meaning |
|---|---|---|
| `monitor_app_name` | required | job/app label, folder and file names |
| `monitor_app_state` | `present` | `absent` removes target file and dashboards |
| `monitor_app_targets` | `[]` | list of `host:port` |
| `monitor_app_metrics_path` | `/metrics` | path to scrape |
| `monitor_app_scheme` | `http` | `http` or `https` |
| `monitor_app_labels` | `{}` | extra labels added to every series |
| `monitor_app_dashboards` | `[]` | dashboard JSON files on the Ansible side |
| `monitor_app_fix_datasources` | `true` | rewrite `${DS_...}` placeholders |

Where things live:

| What | Where |
|---|---|
| scrape targets | `/etc/alloy/targets.d/<name>.yml` |
| provisioned dashboards | `/home/monitoring/monitoring-config/app-dashboards/<name>/` |
| Alloy config | `/etc/alloy/config.alloy` |
| Pushgateway (for batch jobs) | `127.0.0.1:9091` |
| data source ids in dashboards | `prometheus`, `loki` |

Timing: Alloy re-reads targets every 30 s and scrapes every 30 s; Grafana
re-reads dashboard files every 30 s. Allow a minute or two.

## 7. Troubleshooting and limits

If nothing shows up:

1. `ls /etc/alloy/targets.d/`: is your file there?
2. Does the app answer on the host? `curl -s http://127.0.0.1:<port>/metrics | head`.
   If not, the container does not publish the port, or the app has metrics switched
   off.
3. `sudo journalctl -u alloy -e` for Alloy's own errors.
4. Alloy's debug page at `http://127.0.0.1:12345` (its default address): the
   *Graph* page shows `prometheus.scrape.apps` and each target's state.
5. In Grafana *Explore*, `up{job="myapp"}`: `0` means the scrape fails, no result
   means Alloy does not know the target.
6. Dashboard missing: the folder only exists if the role ran *after* monitoring
   was installed. Run your role again.

Limits:

- **k3s workloads are not monitored.** Pods are not Podman containers. The next
  step would be `kube-state-metrics` plus scraping the kubelet; not built.
- The services in the monitoring stack have no authentication, so register only
  loopback endpoints unless you know what you are doing (see [networking](networking.md)).
- Applications that need credentials for `/metrics` (bearer token) are not
  supported by `monitor_app`; use a hand-written target file and extend
  `config.alloy.j2`.
- Forgejo can serve metrics (`[metrics]` / `ENABLED = true` in its `app.ini`,
  inside the data volume, which this playbook never edits); registering
  `127.0.0.1:3000` should then work. Untested.
- Everything here was tested in a sandbox without Podman or Grafana: the files
  are rendered and written as described, but I have not seen a dashboard load on
  a real machine.
