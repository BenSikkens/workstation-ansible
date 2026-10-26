# Role: vim

Vim, set as the default editor. Tag: `vim`. Source: `roles/vim/`.

## What it does

1. Installs `vim-enhanced` (Fedora Workstation only ships a minimal `vi`).
2. Installs `vim-default-editor` with `allowerasing: true`. That package sets
   `EDITOR` for every login shell (`/etc/profile.d/vim-default-editor.sh`). It
   conflicts with `nano-default-editor`, which Workstation installs by default,
   so dnf swaps the two. Only that small profile package is removed; nano itself
   stays installed.

The change takes effect in **new login shells**. Check with `echo $EDITOR`.

## Settings

None. RedHat family only.
