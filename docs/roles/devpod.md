# Role: devpod

The [DevPod](https://devpod.sh) CLI. Tag: `devpod`. Source: `roles/devpod/`.

## What it does

1. Detects the CPU architecture (`amd64` or `arm64`).
2. Downloads `https://github.com/loft-sh/devpod/releases/latest/download/devpod-linux-<arch>`
   to `/usr/local/bin/devpod`, mode 0755. The URL always serves the current
   release, so there is no version to resolve (unlike [todotxt](todotxt.md)).

## What it leaves out

- **The Desktop GUI app.** Upstream dropped deb/rpm packaging for it; it ships
  only as an AppImage with extra runtime dependencies (fuse2, libfribidi, mesa
  GL libs). Not installed by default.
- **A provider.** Choosing one (Docker, Kubernetes, SSH, ...) is a one-time
  interactive choice, e.g. `devpod provider add docker`. The rootless Podman on
  this machine can serve the Docker provider through its docker-compatible
  socket (the `podman.socket` unit is enabled for the `git` user by the
  [forgejo](forgejo.md) role; for your own user use
  `systemctl --user enable --now podman.socket`).

## Settings

| Variable | Default |
|---|---|
| `devpod_install_path` | `/usr/local/bin/devpod` |
