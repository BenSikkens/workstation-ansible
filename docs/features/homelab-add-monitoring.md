# `homelab add monitoring`: dashboards from a project

Tool: `roles/homelab/files/homelab-monitoring` (installed to
`/usr/local/libexec/homelab-monitoring`). Part of the
[homelab role](../roles/homelab.md); the command line is described in the
[homelab command](homelab-command.md) docs.

A project can bring its own Grafana dashboards, and data source files, without
editing the playbook:

```bash
homelab add monitoring ~/Repositories/myproject/monitoring     # a folder, or one or more files
homelab add monitoring --name myproject dash1.json dash2.json  # choose the Grafana folder name
homelab remove monitoring myproject
```

Requires [monitoring](../roles/monitoring.md) to be installed.

## What is picked up

The command looks through the given files and folders (hidden folders and
`node_modules` are skipped) for:

- Grafana dashboards: `.json` with a title and panels;
- data source files: `.yaml` / `.yml` with a `datasources:` list.

Anything else is reported as skipped. They end up in a Grafana folder named
after the project: the folder name, or `--name`. A generic folder such as
`monitoring` or `docs` uses its parent's name.

Dashboards appear within about 30 seconds. Data sources are only read when
Grafana starts, so `homelab` restarts Grafana if the files you added contain
one.

## Rules

- Adding under a name again **replaces** what was added under it before, so a
  dashboard you delete from the project also disappears from Grafana. Give all
  the files each time, or point at the folder.
- `${DS_PROMETHEUS}` / `${DS_LOKI}` placeholders in exported dashboards are
  pointed at this stack's data sources, as with `monitor_app`.
- A data source file can add new data sources, but may not redefine the stack's
  own Prometheus/Loki or set `isDefault`. Do not put passwords in a data source
  file: the copy Grafana reads is readable by every user on this machine.
- Dashboard `uid`s must be unique across projects; you are told if one clashes.
- A name that Ansible's [monitor_app](../roles/monitor_app.md) already uses for
  a folder is refused (use `--name`).
- Dashboards placed this way are read-only in the Grafana UI; use *Save as* for
  a copy.

## What it does not do

It only places dashboards and data sources. Getting the application's *metrics*
into Prometheus is separate: see
[monitoring other applications](monitoring-apps.md).

## How it works

Why this takes one fixed sudo command (see [homelab sudo rules](homelab-sudo.md)):

1. As you, the tool validates the files and **stages** them in
   `/var/lib/homelab/monitoring` (the drop folder, writable by the `homelab`
   group).
2. It runs `sudo homelab-monitoring apply` (no arguments). The root-side step
   reads only that folder, never your path. It opens files without following
   symlinks, ignores odd names and oversized files, reads FIFOs non-blocking,
   re-writes each file from its **parsed content** (`safe_load` and re-dump),
   sets ownership and mode, and renames atomically into the monitoring user's
   config directory.
3. Files get the SELinux type `container_file_t`, so the Grafana container can
   read files added after it started.
4. Dashboards live in `~monitoring/monitoring-config/app-dashboards/<name>/` and
   are loaded by Grafana's `apps` provider (every 30 s); data sources go to a
   provisioning directory and cause a Grafana restart.

## Settings

| Variable | Default |
|---|---|
| `homelab_libexec_dir` | `/usr/local/libexec` |
| `homelab_dropbox_dir` | `/var/lib/homelab/monitoring` |
| `homelab_monitoring_config_dir` | the monitoring role's `monitoring_config_dir` |
