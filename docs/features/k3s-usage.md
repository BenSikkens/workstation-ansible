# Using k3s next to Podman

Installed by the [k3s role](../roles/k3s.md). k3s runs on the host as a normal
system service. Podman cannot be k3s's container runtime (it does not provide
the CRI interface k3s needs), so k3s keeps its own containerd and the two are
tuned to coexist.

```bash
homelab up k3s                       # start (and refresh ~/.kube/k3s.yaml)
kubectl get nodes                    # kubectl is installed by k3s; KUBECONFIG is set for you
podman build -t localhost/myapp:dev .
k3s-load localhost/myapp:dev         # Podman -> k3s, no registry needed
homelab down k3s                     # stop it and all its pods
```

Start and stop through the [homelab command](homelab-command.md): `down` runs
`k3s-killall.sh` so pods really stop.

## Loading your own images

k3s has its own image store (containerd), separate from Podman's. `k3s-load`
(a shell function in `~/.bashrc.d/k3s.sh`) pipes `podman save` into
`k3s ctr images import`. It needs k3s to be running. In your manifests use
`imagePullPolicy: IfNotPresent` (or `Never`) for these images, otherwise k3s
tries to pull `localhost/...` from a registry and fails.

## The kubeconfig

k3s writes a root-only kubeconfig the first time it starts
(`/etc/rancher/k3s/k3s.yaml`). Your user gets a copy at `~/.kube/k3s.yaml`
(`k3s_kubeconfig_path`, mode 0600), refreshed by `homelab up k3s` and by the
Ansible role. `KUBECONFIG` points at it in new shells, and kubectl completion
is loaded. Its sudo rule is discussed in [homelab sudo rules](homelab-sudo.md).

## What the role tunes on the host

| What | Why |
|---|---|
| `k3s-selinux` policy + `selinux: true` in the k3s config | Fedora enforces SELinux; installed by the official installer |
| firewalld: pod (`10.42.0.0/16`) and service (`10.43.0.0/16`) networks in the `trusted` zone | without it pods cannot reach the API server or each other |
| `overlay` and `br_netfilter` modules, loaded at boot | container storage and bridge networking |
| sysctl `ip_forward`, `bridge-nf-call-*`, larger inotify limits (`/etc/sysctl.d/90-k3s.conf`) | the inotify limits also help rootless Podman with many containers |
| cluster/service CIDRs chosen to avoid Podman's `10.88.0.0/16` and the `10.89.x` networks Quadlet creates | no routing overlap with the Forgejo/monitoring networks |
| `k3s-load` shell function | copies images built with Podman into k3s |

## Network exposure

k3s listens on the host directly (API server 6443, kubelet 10250, and Traefik /
service load balancer on 80/443 unless disabled). See [networking](networking.md)
for what is reachable from the LAN and how to keep k3s off it.

## Removing k3s

Not automated, since it deletes the cluster and its data:
`sudo /usr/local/bin/k3s-uninstall.sh`. The firewalld trusted sources and
`/etc/sysctl.d/90-k3s.conf` stay behind; remove them by hand if you want them
gone.

## Monitoring k3s workloads

Only one workload is wired up: [cv-microfrontend](cv-microfrontend.md).
Other pods are not monitored (see [monitoring other applications](monitoring-apps.md)).
