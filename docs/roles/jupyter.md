# Role: jupyter

JupyterLab for your user (`desktop_user`) only, not system-wide. Tag: `jupyter`.
Source: `roles/jupyter/`.

## Why per user, with pipx

- Fedora marks the system Python as externally managed (PEP 668): a global `pip install` is refused, and forcing it can break the Python tools `dnf` itself uses. Fedora's own Jupyter RPMs lag upstream and miss most extensions.
- Nothing about Jupyter needs to be shared with other accounts, and it needs no root.
- JupyterLab gets its own isolated environment, so it can be upgraded or rolled back independently of Fedora and of your projects.

## What it does

1. Installs `pipx` with `dnf`.
2. As your user: `pipx install jupyterlab`. Apps go to `~/.local/bin`, the environment to `~/.local/share/pipx/venvs/jupyterlab`.
3. Injects `jupyter-core` with its apps exposed. pipx only exposes the main package's commands (`jupyter-lab`, ...), not the plain `jupyter` command that `jupyter lab`, `jupyter kernelspec` and `jupyter --version` need.
4. Injects the packages from `jupyter_extra_packages`, if any.

It is idempotent (a second run changes nothing) and never upgrades by itself.
`~/.local/bin` is on your `PATH` in Fedora's default `~/.bashrc`; in an open
terminal start a new shell once.

## Using it

```bash
jupyter lab                    # opens http://localhost:8888 in your browser
jupyter lab --no-browser       # only print the URL (with its token)
pipx upgrade jupyterlab        # upgrade, when you want to
pipx list                      # what pipx manages
```

JupyterLab listens on localhost only and requires the token it prints, so it is
not reachable from the network. It is deliberately not a service that stays
running; start it when you need it.

## Giving a project its own libraries (kernels)

Do not install project libraries (pandas, numpy, ...) into JupyterLab's
environment. Give the project its own virtual environment and register that as a
kernel, so the notebook runs with the project's packages:

```bash
cd ~/Repositories/myproject
python3 -m venv .venv
.venv/bin/pip install ipykernel pandas        # plus whatever the project needs
.venv/bin/python -m ipykernel install --user --name myproject --display-name "myproject"
```

`myproject` then shows up in JupyterLab's kernel list. Remove it with
`jupyter kernelspec remove myproject`.

## Extensions and language servers

Things that must live inside JupyterLab's own environment go in
`jupyter_extra_packages`, for example in `group_vars/all.yml`:

```yaml
jupyter_extra_packages: [jupyterlab-lsp, python-lsp-server]
```

then run `ansible-playbook site.yml --tags jupyter --ask-become-pass`. A package
that is already injected is skipped. Removing one from the list does not
uninstall it; use `pipx uninject jupyterlab <package>`.

## Settings (`roles/jupyter/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `jupyter_package` | `jupyterlab` | the pipx package providing `jupyter lab` |
| `jupyter_extra_packages` | `[]` | extra packages injected into JupyterLab's environment |

## Running it somewhere else

If you would rather have it next to the rest of the homelab (for example on a
dedicated machine, shared with others), run it as a rootless Podman container
instead. That is a different role; this one stays a local tool.
