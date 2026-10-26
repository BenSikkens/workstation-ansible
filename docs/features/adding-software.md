# Adding new software and keeping it portable

## Adding a role

1. Create the role: `ansible-galaxy init roles/<name> --offline`, or just write
   `roles/<name>/tasks/main.yml` by hand; that is all that is strictly needed.
2. Write the install tasks. Prefer `ansible.builtin.dnf` for RPM packages and
   `community.general.flatpak` for Flatpak apps.
3. Add it to `site.yml` with its own tag, like the others:
   `- { role: <name>, tags: [<name>] }`.
4. If it needs another role (Flatpak apps need `flatpak_setup`), declare that in
   `roles/<name>/meta/main.yml` under `dependencies:`, so `--tags <name>` works
   on its own.
5. Document it in `docs/roles/<name>.md` and add a row to the index in
   `docs/README.md`.

## Hooking an application into monitoring

A role that runs a service can register it with Grafana / Prometheus / Loki by
including `monitor_app`. See [monitoring other applications](monitoring-apps.md)
and the [monitor_app role](../roles/monitor_app.md).

## Portability across distributions

The repo is Fedora-first (`dnf` is used directly). To make a role portable
later, either:

- guard package-manager tasks with `when: ansible_facts['os_family'] == "RedHat"`
  and add sibling tasks for other families, which is what the existing roles
  already do for the package task, or
- prefer Flatpak for GUI apps, since that layer is distro-agnostic once
  [flatpak_setup](../roles/flatpak_setup.md) has run.

Several roles are Fedora-specific by nature: SELinux labels (`monitor_app`,
`k3s`), firewalld (`k3s`), Quadlet and systemd user services (`forgejo`,
`monitoring`), and the `vim-default-editor` package swap (`vim`).
