# Role: bashrc_loader

Makes sure `~/.bashrc` loads every file in `~/.bashrc.d/`. Tag:
`bashrc_loader`. Source: `roles/bashrc_loader/`.

Other roles ship shell commands as small drop-ins there: [homelab](homelab.md)
(`homelab.sh`) and [k3s](k3s.md) (`k3s.sh`). Both declare this role as a
dependency, so you do not run it yourself.

## What it does

1. Creates `~/.bashrc.d` for `desktop_user`.
2. Checks whether `~/.bashrc` already mentions `bashrc.d`. Fedora's default does.
3. Only if it does not, adds a marked block (`# BEGIN ANSIBLE MANAGED BLOCK:
   bashrc.d loader`) that sources every file in the directory. `~/.bashrc` is
   backed up first; the backup sits in `~`, outside `.bashrc.d`, so it is not
   loaded.

## Rule for roles that write drop-ins

Do **not** use `backup: true` on files inside `~/.bashrc.d`. Every file there is
sourced, so a backup copy would be loaded too and its old definitions would
override the new ones.

## Settings

Uses `desktop_user` only.
