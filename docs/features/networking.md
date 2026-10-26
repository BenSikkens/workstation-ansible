# Networking: what is reachable from where

See also: [forgejo](../roles/forgejo.md), [monitoring](../roles/monitoring.md), [k3s](../roles/k3s.md), [docs index](../README.md).

Every service in this setup publishes its ports through a `PublishPort=` line
in a Quadlet unit. The address in front of the port decides who can connect:

- `PublishPort=3000:3000` has no address, so it listens on **all network
  interfaces** and is reachable from your LAN.
- `PublishPort=127.0.0.1:3001:3000` is **this machine only**.

## What is exposed today

| Service                             | Host port   | Reachable from                              | Defined in                                                                                  |
| ----------------------------------- | ----------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Forgejo web                         | 3000        | LAN                                         | `roles/forgejo/templates/forgejo.container.j2` (`PublishPort={{ forgejo_http_port }}:3000`) |
| Forgejo SSH                         | 2222        | LAN                                         | same file (`PublishPort={{ forgejo_ssh_port }}:22`)                                         |
| Grafana                             | 3001        | this machine only                           | `roles/monitoring/templates/grafana.container.j2` (`PublishPort=127.0.0.1:...`)             |
| Prometheus                          | 9094        | this machine only                           | `roles/monitoring/templates/prometheus.container.j2`                                        |
| Loki                                | 3100        | this machine only                           | `roles/monitoring/templates/loki.container.j2`                                              |
| Pushgateway                         | 9091        | this machine only                           | `roles/monitoring/templates/pushgateway.container.j2`                                       |
| Podman exporters                    | 9882, 9883  | this machine only                           | `roles/monitoring/templates/prometheus-podman-exporter.service.j2`                          |
| k3s API server                      | 6443        | **LAN** (needs a client certificate)        | k3s itself, `/etc/rancher/k3s/config.yaml`                                                  |
| k3s kubelet                         | 10250       | **LAN** (needs authentication)              | k3s itself                                                                                  |
| k3s Traefik / service load balancer | 80, 443     | **LAN** while k3s runs                      | k3s add-ons; `k3s_disable: [traefik, servicelb]` removes them                               |
| k3s NodePort services               | 30000-32767 | **LAN** for any service you expose that way | Kubernetes                                                                                  |

k3s is different from the container services above: it is not started through
`PublishPort`, it listens on the host directly, so the table lists where it
listens rather than a template line. Fedora Workstation's default firewall zone
typically allows incoming ports 1025-65535, which covers 6443, 10250 and the
NodePort range; 80/443 additionally need the `http`/`https` services. Check
yours with `sudo firewall-cmd --list-all`. All of it only exists while k3s is
running (`homelab down k3s` closes everything).

The monitoring stack is local-only on purpose. Forgejo was already published
without an address from the earlier hand-made setup and was left as it was.

Prometheus, Loki and the Pushgateway have **no authentication**. Do not expose
them. Grafana is plain HTTP with an admin login, so only expose it on a
network you trust.

## Changing it without Ansible

The units are Quadlet files owned by the service user. **Ansible rewrites them
on its next run**, so a manual change is lost then. To make a change
permanent, change the template instead (see the end of this file).

### Make Grafana reachable from the network

```bash
sudo -u monitoring nano /home/monitoring/.config/containers/systemd/grafana.container
```

Change

```
PublishPort=127.0.0.1:3001:3000
```

to

```
PublishPort=3001:3000
```

Then reload and restart:

```bash
sudo -u monitoring bash -c 'cd /; export XDG_RUNTIME_DIR=/run/user/$(id -u monitoring);
  systemctl --user daemon-reload && systemctl --user restart grafana.service'
```

### Make Forgejo local-only

```bash
sudo -u git nano /home/git/.config/containers/systemd/forgejo.container
```

Change the two lines to

```
PublishPort=127.0.0.1:3000:3000
PublishPort=127.0.0.1:2222:22
```

Then reload and restart:

```bash
sudo -u git bash -c 'cd /; export XDG_RUNTIME_DIR=/run/user/$(id -u git);
  systemctl --user daemon-reload && systemctl --user restart forgejo.service'
```

To shut off only the SSH exposure, change just the 2222 line.

## Things to know

- **Firewall.** Fedora's firewalld can still block a published port from
  other machines. Open one with:
  `sudo firewall-cmd --add-port=3001/tcp --permanent && sudo firewall-cmd --reload`
  (`--zone=<name>` if you use a non-default zone.) Check what is open with
  `sudo firewall-cmd --list-all`.
- **Keeping k3s off the LAN.** k3s cannot simply bind to `127.0.0.1` (pods
  reach the API server through the node address). Instead block the ports in
  firewalld; the pod and service networks are trusted by *source*, which takes
  precedence over the interface's zone, so the cluster keeps working. This is
  the recommended approach but I have not been able to test it on a real k3s
  node.
- **Check what is listening.** `sudo ss -ltnp | grep -E ':(3000|2222|3001|9094|3100|9091)\b'`
  shows the address each port is bound to: `127.0.0.1` is local only,
  `0.0.0.0` or `*` is every interface.
- **Public URLs.** If you reach a service by hostname or LAN IP instead of
  `localhost`, tell it so, or links and redirects will point at the wrong
  address:
  - Forgejo: `ROOT_URL` (and `DOMAIN`) in `app.ini` inside the data volume,
    `/home/git/forgejo-data/data/gitea/conf/app.ini`. Clone URLs use it.
  - Grafana: add `Environment=GF_SERVER_ROOT_URL=http://<your-host>:3001/` to
    `grafana.container` (the unit currently sets `http://localhost:3001/`).
- **CI jobs** reach Forgejo and the Pushgateway over the internal Podman
  network (`forgejo`) by name, not through these published ports, so changing
  a host binding does not affect pipelines.
- **No TLS.** All of these speak plain HTTP. If you expose one beyond a
  trusted network, put a reverse proxy with TLS in front of it.

## Making a change permanent in the Ansible code

Edit the `PublishPort=` line in the template named in the table above and
re-run `ansible-playbook site.yml --ask-become-pass`. The unit is re-rendered
and the service restarted. If you want this as a setting rather than an edited
template, a variable such as `monitoring_grafana_bind` (default `127.0.0.1`)
used as `PublishPort={{ monitoring_grafana_bind }}:{{ monitoring_grafana_port }}:3000`
would let one line in `group_vars/all.yml` control it.
