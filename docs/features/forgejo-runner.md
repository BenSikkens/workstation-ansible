# Forgejo Actions runner

A second, separate **rootless** container (`forgejo-runner`, image
`code.forgejo.org/forgejo/runner`) runs CI/CD jobs for Forgejo Actions under
the same `git` user as [Forgejo](../roles/forgejo.md). It is managed the same
way, as a Quadlet unit at `~git/.config/containers/systemd/forgejo-runner.container`.
Tasks: `roles/forgejo/tasks/runner.yml`.

## How it connects

- It talks to Forgejo over a shared Podman network (`forgejo.network`, also
  deployed by the role) instead of the host's published port, so it works
  whichever host port Forgejo is mapped to.
- Job containers join the `forgejo` network (`container.network` in the runner
  config), so the instance URL `http://forgejo:3000` resolves inside a job.
  Without that, `actions/checkout` could not reach the server.
- Jobs using `docker://...` labels run through the `git` user's own rootless
  Podman socket, bind-mounted into the runner container as
  `/var/run/docker.sock`. Job containers are themselves rootless, one level
  down.
- The runner container needs to reach that socket, so it runs with SELinux label
  confinement disabled by default (`forgejo_runner_selinux_type: ""`, same as
  `spc_t`). Try `container_runtime_t` for a narrower domain; if the runner then
  fails with `permission denied ... docker.sock`, check `ausearch -m avc`.

## Registration is automatic

Forgejo has an "offline registration" CLI mode built for scripted setups:

1. The role generates a random secret.
2. It hands it to Forgejo via `podman exec ... forgejo-cli actions register --secret ...`.
3. Forgejo returns a UUID; the role stores both in the runner's data dir as
   `.runner-uuid` and `.runner-secret` (mode 0600).

Registration happens exactly once. `config.yml` is re-rendered from the
template on every run (the previous version is kept as a backup) and the runner
is restarted when it changes. A runner registered by an earlier version of the
role, whose UUID and secret only lived inside `config.yml`, is migrated on the
next run without re-registering. See also [overwrite policy](overwrite-policy.md).

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_runner_image` | `code.forgejo.org/forgejo/runner:13` | pinned to major 13; bump deliberately after checking the registry |
| `forgejo_runner_name` | the host's hostname | name shown in Forgejo's runner list |
| `forgejo_runner_labels` | `docker:docker://node:22-bookworm`, `ubuntu-latest:docker://node:22-bookworm` | labels workflows target with `runs-on:`. `ubuntu-latest` exists because workflows from the earlier hand-made runner used it; here it runs in a throwaway node container. Use `ubuntu-latest:host` if a workflow needs the runner container itself |
| `forgejo_runner_scope` | `""` (instance-wide) | an org/user/repo name scopes the runner narrower |
| `forgejo_runner_data_dir` | `/home/git/forgejo-runner-data` | holds `config.yml`, `.runner-uuid`, `.runner-secret` |
| `forgejo_runner_selinux_type` | `""` | SELinux domain for the runner container |

The `scan` label is added automatically when the [CI scanner image](ci-scanners.md)
is enabled.

## Checking it

```bash
sudo machinectl shell git@
systemctl --user status forgejo-runner.service
podman logs forgejo-runner
```

It also appears under Forgejo's **Site Administration → Actions → Runners**.
`homelab down forgejo` stops the runner together with Forgejo
([homelab command](homelab-command.md)).
