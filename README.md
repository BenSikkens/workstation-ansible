# Workstation Setup

Ansible playbook to reproduce my software setup on a fresh Fedora install
(or, since it's Ansible, in principle any Linux distro — see notes below).

## Layout

```
.
├── ansible.cfg          # local defaults (inventory path, callback plugin)
├── inventory.ini         # targets localhost by default
├── requirements.yml       # external collections (community.general for flatpak)
├── site.yml              # main playbook — the list of roles = the list of software
└── roles/
    ├── flatpak_setup/     # base dependency: installs flatpak, adds Flathub remote
    └── podman_desktop/    # installs Podman Desktop via Flathub
```

## Usage

One-time setup on a fresh machine:

```bash
sudo dnf install ansible -y
ansible-galaxy collection install -r requirements.yml
```

Run the playbook:

```bash
ansible-playbook site.yml
```

If your user doesn't have passwordless sudo configured, add `--ask-become-pass`.

## Before running: review what will change

Always preview a run before applying it, especially after editing a role or
pulling in someone else's change:

```bash
ansible-playbook site.yml --ask-become-pass --check --diff
```

`--check` runs without making changes; `--diff` shows the exact before/after
of any file this would write. Nothing here will run the risk of silently
clobbering something you can't see coming back.

### Where this playbook can overwrite something, and what's done about it

Most tasks here (`dnf`, `community.general.flatpak`) only install packages —
they never touch your existing configuration or data, so there's nothing to
protect there. The places that *do* write a file outright are:

- Existing Forgejo data is archived before any change (see "Backup, restore and cleanup" under Forgejo).
- The Forgejo/Forgejo-runner Quadlet units (`roles/forgejo/templates/*.j2`,
  deployed via `ansible.builtin.template`) — these are re-rendered and
  reapplied on every run by design, so that changing a default (say, a port
  or image tag) propagates on the next `ansible-playbook` run. They all use
  `backup: true`, so if content changes, Ansible saves a timestamped copy of
  the previous version right next to it before overwriting — nothing is
  ever lost, even if the file does change.
- The Forgejo runner's `config.yml` is re-rendered on every run too (so that
  label and scanner-toggle changes take effect), also with `backup: true`.
  The runner's identity does *not* live in that file any more: its UUID and
  secret are kept in `.runner-uuid` / `.runner-secret` (mode 0600) next to
  it, created exactly once at registration and never overwritten
  (`force: false`), so re-rendering the config can't re-register the runner.
  Because `config.yml` holds the secret, tasks touching it use `diff: false`
  and it never appears in `--check --diff` output.
- The CI image's `Containerfile` is rendered with `backup: true` as well; it
  is only rebuilt when it actually changed (or the image is missing).
- `~/.bashrc` is only touched if it doesn't already load `~/.bashrc.d/`
  (Fedora's default does), and then via a marked block with a backup. The
  `homelab` command itself lives in its own drop-in, `~/.bashrc.d/homelab.sh`.
- Forgejo's own application config (`app.ini`, inside the data volume) and
  any vault/repo data are never templated or written by this playbook at
  all — Forgejo manages those itself, so there's nothing here that could
  clobber them.

If you ever hand-edit a Quadlet unit directly on the box, know that the next
playbook run will overwrite it back to the template's version (with a backup
kept) — that's standard Ansible/infrastructure-as-code behavior: the repo is
the source of truth. If you want a hand-edit to stick, make the equivalent
change in the `.j2` template (or the role's `defaults/main.yml`) instead of
editing the deployed file, so the change survives the next run too.

## Adding new software

1. Create a new role: `ansible-galaxy init roles/<name> --offline` (or just make
   `roles/<name>/tasks/main.yml` by hand — that's all that's strictly needed).
2. Write the install task(s) — prefer `ansible.builtin.dnf` for RPM packages,
   `community.general.flatpak` for Flatpak apps.
3. Add the role name to the `roles:` list in `site.yml`.

## Notes on portability across distros

This is currently Fedora-first (uses `dnf` directly in `flatpak_setup`).
To make a role portable to Debian/Arch/etc. later, either:
- Guard package-manager tasks with `when: ansible_facts['os_family'] == "RedHat"`
  and add sibling tasks for other families, or
- Prefer Flatpak for GUI apps where possible, since that layer is already
  distro-agnostic once `flatpak_setup` has run.

## Software installed so far

| Role | Software | Install method |
|---|---|---|
| `podman_desktop` | Podman Desktop | Flatpak (Flathub) |
| `vim` | Vim (vim-enhanced) | dnf |
| `vscodium` | VSCodium | dnf (official VSCodium RPM repo) |
| `keepassxc` | KeePassXC | dnf |
| `mkcert` | mkcert | dnf |
| `forgejo` | Forgejo (self-hosted git) + Actions runner + scanner CI image (semgrep, gitleaks, trivy) | two rootless Podman containers via Quadlet, under a dedicated `git` user |
| `monitoring` | Grafana + Prometheus + Loki, fed by Grafana Alloy, Podman exporters and a Pushgateway | rootless Podman containers (Quadlet) under a dedicated `monitoring` user; Alloy and the exporter from RPMs. Skipped with `monitoring_enabled: false` |
| `obsidian` | Obsidian | Flatpak (Flathub) |
| `todotxt` | todo.txt-cli + GNOME Shell "Todo.txt" extension | upstream GitHub tarball + extensions.gnome.org, for `desktop_user` |
| `devpod` | DevPod CLI | binary from GitHub releases (`loft-sh/devpod`) |
| `homelab` | the `homelab up\|down\|status` command | bash function in `~/.bashrc.d/` for `desktop_user` |

### Forgejo (self-hosted git server)

Runs as a **rootless** Podman container under a dedicated `git` system user,
managed as a systemd **user** service via a [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
unit at `~git/.config/containers/systemd/forgejo.container`. Systemd lingering
is enabled for `git` so the service survives reboots without anyone logging
in as that user.

Defaults (override in `roles/forgejo/defaults/main.yml` or via
`group_vars/all.yml`):

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_user` | `git` | system user the container runs as |
| `forgejo_image` | `codeberg.org/forgejo/forgejo:16` | pinned to a major version, not `latest`. Never lower it on an existing install: Forgejo refuses a database written by a newer release |
| `forgejo_data_dir` | `/home/git/forgejo-data` | persistent data on the host |
| `forgejo_http_port` | `3000` | web UI |
| `forgejo_ssh_port` | `2222` | git-over-ssh (not 22 — that's the host's own sshd, and rootless containers can't bind ports <1024 on the host side) |

After running the playbook:

- Web UI / first-run setup wizard: `http://localhost:3000`
- Clone over SSH: `git clone ssh://git@localhost:2222/<owner>/<repo>.git`
  (you'll want an entry in your `~/.ssh/config` for the non-standard port)
- Check the service directly:
  ```bash
  sudo machinectl shell git@ 
  systemctl --user status forgejo.service
  podman logs forgejo
  ```

**Note:** this scaffold gets the container running and persistent — it
doesn't configure Forgejo itself (admin account, `APP_URL`, etc.). That's
done once through the first-run web wizard, or later by editing
`{{ forgejo_data_dir }}/data/gitea/conf/app.ini` inside the data volume.

#### Forgejo Actions runner

A second, separate **rootless** container (`forgejo-runner`, image
`code.forgejo.org/forgejo/runner`) runs CI/CD jobs for Forgejo Actions,
under the same `git` user. It's managed the same way — a Quadlet unit at
`~git/.config/containers/systemd/forgejo-runner.container` — and it talks
to Forgejo over a shared Podman network (`forgejo.network`, also deployed
by this role) rather than over the host's published port, so it works
regardless of which host port you've mapped Forgejo to.

**Registration is fully automatic**, no web UI click-through needed:
Forgejo has an "offline registration" CLI mode built for scripted setups
like this one. The role generates a random secret, hands it to Forgejo via
`podman exec ... forgejo-cli actions register --secret ...`, gets back a
UUID, and stores both (`.runner-uuid`, `.runner-secret`) in the runner's
data dir; the pair in `config.yml` is the registration, so there's no
separate token step. Registration happens exactly once. `config.yml` itself
is re-rendered from the template on every run (previous version kept as a
backup), and the runner is restarted when it changes. A runner registered by
an earlier version of this role, whose UUID/secret only lived inside
`config.yml`, is migrated automatically on the next run without
re-registering.

Job containers join the `forgejo` Podman network (`container.network` in the
runner config) so that the instance URL `http://forgejo:3000` resolves inside
a job; without that, `actions/checkout` could not reach the server.

Jobs that use `docker://...` container labels run via the `git` user's own
rootless Podman socket, bind-mounted into the runner container as
`/var/run/docker.sock` — so job containers are themselves rootless, one
level down.

Defaults:

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_runner_image` | `code.forgejo.org/forgejo/runner:13` | pinned to major version 13; bump deliberately after checking the registry |
| `forgejo_runner_name` | the host's hostname | name shown in Forgejo's runner list |
| `forgejo_runner_labels` | `["docker:docker://node:22-bookworm"]` | execution labels workflows can target; add more (e.g. `ubuntu-latest:docker://...`) as needed |
| `forgejo_runner_scope` | `""` (instance-wide) | set to an org/user/repo name to scope the runner narrower |
| `forgejo_runner_data_dir` | `/home/git/forgejo-runner-data` | holds `config.yml`, `.runner-uuid` and `.runner-secret` |

Check it directly:
```bash
sudo machinectl shell git@
systemctl --user status forgejo-runner.service
podman logs forgejo-runner
```
It should also show up under Forgejo's **Site Administration → Actions →
Runners**.

#### Security scanners in CI: semgrep, gitleaks, trivy

Jobs run in throwaway containers, so tools installed on the host would be
invisible to them. Instead the role builds one local image,
`localhost/forgejo-ci:latest` (a `node:22-bookworm` base, so `actions/checkout`
works, plus the scanners), in `git`'s Podman storage and offers it to
workflows as the runner label `scan`:

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

Which tools get installed is controlled in `group_vars/all.yml` (default:
all `true`):

```yaml
forgejo_runner_install_semgrep: true
forgejo_runner_install_gitleaks: true
forgejo_runner_install_trivy: true
```

Set one to `false`, re-run the playbook, and the image is rebuilt without
that tool. If all three are `false`, nothing is built and the `scan` label is
dropped from the runner. (A previously built image stays in Podman storage;
remove it with `sudo -u git podman rmi localhost/forgejo-ci:latest`.)

How each tool gets in: gitleaks and trivy are static Go binaries copied out
of their official images (`zricethezav/gitleaks`, `aquasec/trivy`); semgrep
has no standalone binary, so it is pip-installed into a venv. The image is
built once and then reused, so scanner versions don't move on their own — to
pick up newer ones, remove the image as above and re-run the playbook. The
first build takes a few minutes. Two behaviours to know: trivy downloads its
vulnerability database at scan time (every job starts from a clean
container), and semgrep's `--config auto` talks to semgrep.dev, while a
pinned ruleset like `p/default` or your own rules file does not need to.

#### `homelab`: switch the whole stack on and off

(Installed by the separate `homelab` role, which runs last so it knows
whether monitoring is present.)

The stack holds resources even when idle, so a `homelab` command is
installed for your desktop user (`desktop_user`) as a drop-in at
`~/.bashrc.d/homelab.sh`, which Fedora's `~/.bashrc` already sources:

```bash
homelab up                  # start everything: Forgejo, runner, monitoring
homelab down                # stop it all, plus any CI containers left behind
homelab status              # running / degraded / stopped, per unit
homelab down forgejo        # only Forgejo + runner (monitoring keeps running)
homelab status monitoring   # only Grafana, Prometheus, Loki, Alloy, ...
```

The optional scope is `forgejo`, `monitoring` or `all` (default). With
`monitoring_enabled: false` only `forgejo` exists. `homelab down forgejo`
deliberately leaves the Pushgateway and the Podman socket alone, so
monitoring keeps working.

`status` exits 0 when everything in scope is running, 1 when degraded and 3
when stopped, so it is usable in scripts. A group counts as running when its
core units are up (Forgejo + runner; Prometheus, Loki, Grafana, Alloy and the
Pushgateway); the Podman exporters are listed but do not make a group
"degraded" on their own. Tab completion is included. It uses `sudo` to reach
the service users' systemd instances, so expect a password prompt. The
command only appears in **new** shells; in an open terminal run
`source ~/.bashrc.d/homelab.sh`.

`homelab down` is a runtime switch only: the services are enabled and the
service users have lingering on, so the stack comes back up at the next boot
(and `ansible-playbook` starts it if it's down). Say if you'd rather have it
stay off until you run `homelab up`.

#### Backup, restore and cleanup (`forgejo-backup.yml`)

If Forgejo data already exists, `site.yml` takes a backup **before the forgejo
role changes anything**: it stops Forgejo and the runner (so the SQLite
database and git repos are copied quietly), archives the data dir, the runner
data dir and the Quadlet units (with numeric ownership, plus a SHA-256) into
`/var/backups/forgejo/<timestamp>/` (root-only), and records it in
`/var/backups/forgejo/manifest.yml` with `status: pending`. Once the role has
verified that Forgejo answers on `/api/healthz` and both services are active,
it flips the manifest to `status: success`. On a fresh machine there is
nothing to back up and no manifest is written.

Afterwards, run the separate playbook; what it does depends on that status:

```bash
ansible-playbook forgejo-backup.yml --ask-become-pass
```

| Recorded status | Meaning | `auto` does |
|---|---|---|
| `success` | install finished, Forgejo + runner healthy | **removes** the backup(s) |
| `pending` | install died before it was verified | **restores** the backup (asks you to type `yes`) |
| `restored` | a rollback already happened | removes the backup(s) |

Force a decision with `-e backup_action=restore` or `-e backup_action=remove`,
and skip the prompt (needed without a terminal) with `-e backup_confirmed=true`.
Notes:

- Restoring **never deletes** what it replaces: the broken directories are
  renamed to `<path>.failed-<timestamp>` next to the originals. Delete them
  yourself when you're done. The archive is checked against its recorded
  checksum before anything is moved, and a mismatch aborts untouched.
- If a run fails and you simply re-run `site.yml` instead of restoring, the
  original backup is kept as the restore point (no new backup of the
  half-installed state), until a run finishes successfully.
- "Outcome" means the forgejo role: a later failure in another role (for
  example devpod) doesn't trigger a Forgejo rollback, because Forgejo itself
  was fine.
- The backup stops Forgejo for as long as the copy takes (seconds to a few
  minutes, depending on repository size) and needs free space for a copy of
  the data; there is a check up front that aborts before changing anything.
- Not in the backup: container images, the CI image, firewall rules, the
  `homelab` command, anything outside the three paths. They are recreated by
  re-running the playbook.
- Turn it off with `forgejo_backup_enabled: false` in `group_vars/all.yml`;
  `forgejo_backup_dir` moves the location.

### Monitoring (Grafana, Prometheus, Loki)

A dashboard for the scanner results, plus the health, traffic and logs of the
containers and the machine. Everything listens on `127.0.0.1` only.

| Piece | Runs as | Job |
|---|---|---|
| Grafana | container, user `monitoring` | the dashboards, `http://localhost:3001` |
| Prometheus | container, user `monitoring` | metrics database (30 days) |
| Loki | container, user `monitoring` | log database (14 days) |
| Pushgateway | container, user `git` | holds the latest scan results CI jobs push |
| Grafana Alloy | system service (Grafana RPM repo) | collects host metrics, scrapes the exporters and the Pushgateway, ships the systemd journal to Loki |
| `prometheus-podman-exporter` | systemd user service, one per Podman user (`git` and your desktop user) | per-container CPU, memory, network, disk |

Open `http://localhost:3001` and log in as `admin`. The password is generated
on the first run and kept in a file only `monitoring` and root can read:

```bash
sudo cat /home/monitoring/.grafana-admin-password
```

Three dashboards are provisioned into the *Homelab* folder (edit them in the
UI, but changes are overwritten by the playbook; "Save as" to keep your own):

- **Security scans**: current findings per severity, per repository and tool,
  a history graph, and a table of the individual findings (rule, file, line,
  package, fixed version) with filters.
- **Containers**: state, CPU, memory, network in/out, disk I/O per container,
  for every Podman user.
- **Host and logs**: CPU, memory, disk, load, host network traffic, then log
  volume by level and a searchable log view with container and unit filters
  (includes an "errors and failures" panel).

##### Sending scan results to the dashboard

The CI image (label `scan`) ships a helper, `scan-report`, and knows where
the Pushgateway is. Have the scanner write JSON, then report it:

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

Notes:

- Each push **replaces** the previous result for that repository and tool, so
  fixed findings disappear on the next scan. The history graph shows how the
  counts moved over time.
- Only rule, file, line and package are sent. **Never the matched text**, so a
  secret found by gitleaks does not end up in Grafana or Loki.
- It never fails your pipeline: if the Pushgateway is down it prints a warning
  and exits 0 (`SCAN_REPORT_STRICT=1` changes that). A scan that finds issues
  still fails or passes exactly as the scanner's own exit code decides; run the
  scanner with `|| true` as above if you only want reporting.
- At most 200 findings per scan are listed individually
  (`SCAN_REPORT_MAX_FINDINGS`); the per-severity counts always cover all.
- `SCAN_REPORT_DRY_RUN=1 scan-report trivy trivy.json` prints what would be
  sent.

##### Settings

Defaults live in `roles/monitoring/defaults/main.yml`: image versions,
ports, retention (`monitoring_prometheus_retention`,
`monitoring_loki_retention`), and `monitoring_podman_exporters` (which Podman
users are watched). To skip all of it set `monitoring_enabled: false` in
`group_vars/all.yml`; nothing already installed is removed.

##### Not covered

- Monitoring data is **not** part of the Forgejo backup (`forgejo-backup.yml`).
  It lives in the `monitoring` user's Podman volumes (`prometheus-data`,
  `loki-data`, `grafana-data`); losing it loses history only.
- Container logs are read from the systemd journal, where Quadlet services
  already write. Containers started by hand (`podman run`) are in the journal
  only if they use the journald log driver.
- Grafana is not exposed beyond localhost and has no TLS; put a reverse proxy
  in front if you ever want remote access.

### Obsidian

Installed via Flathub (`md.obsidian.Obsidian`), same pattern as
`podman_desktop` — runs natively as a normal desktop window, with vaults
living wherever you choose in your own home directory rather than inside
a container's data volume.

### todo.txt-cli + GNOME Shell extension

Installs the [Todo.txt](https://extensions.gnome.org/extension/570/todotxt/)
GNOME Shell extension and its dependency, `todo.txt-cli`.

This is the first role that acts on **your own desktop login** rather than
a dedicated service user — GNOME Shell extensions are per-user, so there's
no "git" or "obsidian"-style service account to hide behind. It uses a new
shared variable, `desktop_user` (set in `group_vars/all.yml`), which
defaults to whoever actually runs `ansible-playbook`. Override it there if
you ever run this playbook as someone other than your own login.

**`todo.txt-cli`** has no Fedora package, so it's built from upstream's
GitHub releases: `todotxt_cli_version` defaults to `"latest"`, resolved via
the GitHub API at run time, and installed to `/opt/todo.txt-cli` with
`todo.sh` (and a bare `todo` alias) symlinked onto `/usr/local/bin`. Pin a
specific tag (e.g. `"v2.12.0"`) instead if you want it to stop moving.

**The extension** is resolved dynamically through extensions.gnome.org's
`extension-info` API, keyed by its numeric id (`570`, from the URL above) —
this hands back the right build for whatever GNOME Shell version is
actually installed, so there's no UUID or version hardcoded here to go
stale. It's downloaded straight into
`~{{ desktop_user }}/.local/share/gnome-shell/extensions/<uuid>/` and only
installed once (same "write once, leave alone" pattern as the Forgejo
runner's `config.yml` — if GNOME's own update mechanism later replaces it,
this role won't overwrite that).

**Important:** enabling the extension (`gnome-extensions enable`) writes to
your dconf database over your session's D-Bus — that only exists while
you're logged into GNOME. **Run this playbook from a terminal inside your
active GNOME session**, not from a plain TTY or a headless SSH session with
nobody logged in graphically, or that last step will fail.

After running the playbook, you likely need to either log out and back in,
or restart GNOME Shell (<kbd>Alt</kbd>+<kbd>F2</kbd>, type `r`, Enter — X11
only; Wayland needs a full log out/in) before the extension shows up.

### DevPod

Installs just the [DevPod](https://devpod.sh) **CLI** — upstream dropped
deb/rpm packaging for the separate Desktop GUI app, which now ships only
as an AppImage with extra runtime dependencies (fuse2, libfribidi, mesa GL
libs). That's enough extra machinery that it's left out of this role by
default; say so if you want it added too.

The binary comes straight from GitHub's stable
`releases/latest/download/devpod-linux-<arch>` URL — no version-resolving
step needed (unlike `todotxt`), since that path always serves whatever is
current. Architecture (`amd64`/`arm64`) is detected automatically.
Installed to `/usr/local/bin/devpod` (override via `devpod_install_path`
in `roles/devpod/defaults/main.yml`).

**One thing this role deliberately doesn't do:** configure a DevPod
*provider* (Docker, Kubernetes, SSH, etc.) — that's a one-time interactive
choice (`devpod provider add docker`, for instance) better made by you
than decided on your behalf. This box already has rootless Podman set up
via the `forgejo` role, which DevPod's Docker provider can target through
Podman's docker-compatible socket if you'd rather not run Docker itself.
