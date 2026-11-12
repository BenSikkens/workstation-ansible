#!/usr/bin/python3 -I
"""homelab-gui: a small local web dashboard for the `homelab` command.

Runs as you (a systemd user service), listens on 127.0.0.1 only, uses nothing
but the Python standard library. It does exactly what `homelab` does, by
calling it: `homelab status --porcelain`, `homelab up|down SCOPE`, and
`journalctl` for the logs. No new privileges: the sudo rules of the homelab
group apply as they do in a terminal.

Safeguards, because anything on this machine can reach a loopback port:
  * every request needs the secret cookie (set once by /login?t=TOKEN; the
    `homelab-gui` command opens that URL for you);
  * the Host header must be the loopback address (blocks DNS rebinding);
  * POSTs also need a custom header and a matching Origin (blocks CSRF);
  * log and action targets are checked against what `homelab status` reported,
    never passed through from the request.

Managed by Ansible (roles/homelab_gui). Local edits are overwritten.
"""

import hmac
import http.server
import json
import os
import pwd
import grp
import subprocess
import sys
import threading
import time
import urllib.parse

CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.config/homelab-gui/config.json")
with open(CONFIG_PATH, encoding="utf-8") as fh:
    CFG = json.load(fh)

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(CFG["port"])
HOMELAB_SH = CFG["homelab_sh"]
IDENTITY_SH = CFG.get("identity_sh", "")
GROUP_NAME = CFG.get("homelab_group", "homelab")
LOG_LINES = int(CFG.get("log_lines", 300))
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
SCOPES = {"all", "identity", "forgejo", "monitoring", "k3s"}
COOKIE = "homelab_gui"
JOB_TIMEOUT = 900

with open(CFG["token_file"], encoding="utf-8") as fh:
    TOKEN = fh.read().strip()
if len(TOKEN) < 32:
    sys.exit("homelab-gui: the token file is missing or too short")


def run(args, timeout=60):
    """Run a command, return (rc, combined output). Never raises."""
    try:
        proc = subprocess.run(
            args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=timeout, cwd="/",
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as exc:
        return 127, str(exc)


def homelab(*words, timeout=60):
    """Run the `homelab` shell function (it lives in ~/.bashrc.d, not on PATH)."""
    return run(["/bin/bash", "-c", 'source "$1" && shift && homelab "$@"', "homelab", HOMELAB_SH, *words], timeout)


# --------------------------------------------------------------------- status
_status_lock = threading.Lock()
_status_cache = {"at": 0.0, "data": None}


def parse_porcelain(text):
    groups, order, missing = {}, [], []
    for line in text.splitlines():
        f = line.split("\t")
        if f[0] == "G" and len(f) == 4:
            groups[f[1]] = {"id": f[1], "state": f[2], "title": f[3], "units": []}
            order.append(f[1])
        elif f[0] == "U" and len(f) == 5 and f[1] in groups:
            groups[f[1]]["units"].append({"name": f[2], "state": f[3], "owner": f[4]})
        elif f[0] == "M" and len(f) == 2:
            missing.append(f[1])
    return [groups[g] for g in order], missing


def in_homelab_group():
    try:
        return grp.getgrnam(GROUP_NAME).gr_gid in os.getgroups()
    except KeyError:
        return False


def get_status(max_age=2.0):
    with _status_lock:
        if _status_cache["data"] is not None and time.time() - _status_cache["at"] < max_age:
            return _status_cache["data"]
        rc, out = homelab("status", "all", "--porcelain")
        groups, missing = parse_porcelain(out)
        notes = []
        if not groups:
            notes.append(out.strip() or "Nothing from `homelab status`.")
        if not in_homelab_group():
            notes.append(
                f"This service is not in the '{GROUP_NAME}' group yet, so sudo may ask for a password "
                "and the dashboard cannot answer it. Log out and in again, then restart the dashboard."
            )
        data = {"groups": groups, "missing": missing, "notes": notes, "busy": job_running(),
                "at": int(time.time())}
        _status_cache.update(at=time.time(), data=data)
        return data


def known_units():
    data = get_status(max_age=30)
    return {(u["owner"], u["name"]) for g in data["groups"] for u in g["units"]
            if u["state"] != "not installed"}


# ----------------------------------------------------------------------- jobs
_job_lock = threading.Lock()
_job = {"id": 0, "running": False, "verb": "", "scope": "", "output": "", "rc": None, "started": 0.0}


def job_snapshot(offset):
    with _job_lock:
        return {k: (_job[k] if k != "output" else _job["output"][offset:]) for k in _job} | {"offset": len(_job["output"])}


def job_running():
    with _job_lock:
        return _job["running"]


def _run_job(verb, scope):
    proc = None
    try:
        proc = subprocess.Popen(
            ["/bin/bash", "-c", 'source "$1" && homelab "$2" "$3"', "homelab", HOMELAB_SH, verb, scope],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", cwd="/",
        )
        killer = threading.Timer(JOB_TIMEOUT, proc.kill)
        killer.start()
        for line in proc.stdout:
            with _job_lock:
                _job["output"] += line
        proc.wait()
        killer.cancel()
        rc = proc.returncode
    except OSError as exc:
        rc = 127
        with _job_lock:
            _job["output"] += f"{exc}\n"
    with _job_lock:
        _job["rc"] = rc
        _job["running"] = False
    _status_cache["at"] = 0.0


def start_job(verb, scope):
    with _job_lock:
        if _job["running"]:
            return None
        _job.update(id=_job["id"] + 1, running=True, verb=verb, scope=scope, output="", rc=None,
                    started=time.time())
        job_id = _job["id"]
    threading.Thread(target=_run_job, args=(verb, scope), daemon=True).start()
    return job_id


# ----------------------------------------------------------------------- logs
def get_logs(owner, unit, lines):
    if (owner, unit) not in known_units():
        return 404, "Unknown unit."
    cmd = ["journalctl", "--no-pager", "-o", "short-iso", "-n", str(lines)]
    if owner == "system":
        cmd += ["-u", unit]
    else:
        try:
            uid = pwd.getpwnam(owner).pw_uid
        except KeyError:
            return 404, "Unknown user."
        cmd += [f"--user-unit={unit}", f"_UID={uid}"]
    rc, out = run(cmd, timeout=20)
    if "insufficient permissions" in out or "not seeing messages from other users" in out:
        out += ("\nYour account may not read this journal. Members of the 'wheel' or 'systemd-journal' group can; "
                "or run it in a terminal: sudo " + " ".join(cmd) + "\n")
    return 200, out[-300_000:]


def get_info():
    if not IDENTITY_SH or not os.path.exists(IDENTITY_SH):
        return ""
    rc, out = run(["/bin/bash", "-c", 'source "$1" && identity-info', "identity", IDENTITY_SH], timeout=10)
    return out if rc == 0 else ""


# ----------------------------------------------------------------------- HTTP
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "homelab-gui"
    sys_version = ""

    def log_message(self, fmt, *args):  # quiet: the journal is for errors
        pass

    # -- helpers
    def _send(self, code, body, ctype="application/json", extra=None):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                         "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _host_ok(self):
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    def _authed(self):
        for part in self.headers.get("Cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE and hmac.compare_digest(value, TOKEN):
                return True
        return False

    # -- verbs
    def do_GET(self):
        if not self._host_ok():
            return self._send(421, "Misdirected request", "text/plain")
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)

        if url.path == "/login":
            given = (query.get("t") or [""])[0]
            if hmac.compare_digest(given, TOKEN):
                return self._send(303, "", "text/plain", {
                    "Location": "/",
                    "Set-Cookie": f"{COOKIE}={TOKEN}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000",
                })
            return self._send(403, "Wrong token. Run `homelab gui` to open the dashboard.", "text/plain")

        if not self._authed():
            return self._send(401, "Not signed in. Run `homelab gui` (or the Homelab launcher) in your session.",
                              "text/plain")

        if url.path == "/":
            return self._static("index.html", "text/html; charset=utf-8")
        if url.path in ("/app.js", "/app.css"):
            ctype = "text/javascript; charset=utf-8" if url.path.endswith(".js") else "text/css; charset=utf-8"
            return self._static(url.path[1:], ctype)
        if url.path == "/api/status":
            return self._json(200, get_status())
        if url.path == "/api/config":
            return self._json(200, {"links": CFG.get("links", []), "info": get_info(), "log_lines": LOG_LINES})
        if url.path == "/api/job":
            try:
                offset = int((query.get("offset") or ["0"])[0])
            except ValueError:
                offset = 0
            return self._json(200, job_snapshot(max(offset, 0)))
        if url.path == "/api/logs":
            owner = (query.get("owner") or [""])[0]
            unit = (query.get("unit") or [""])[0]
            try:
                lines = min(max(int((query.get("lines") or [str(LOG_LINES)])[0]), 10), 2000)
            except ValueError:
                lines = LOG_LINES
            code, text = get_logs(owner, unit, lines)
            return self._send(code, text, "text/plain; charset=utf-8")
        return self._send(404, "Not found", "text/plain")

    def do_POST(self):
        if not self._host_ok():
            return self._send(421, "Misdirected request", "text/plain")
        if not self._authed():
            return self._send(401, "Not signed in", "text/plain")
        origin = self.headers.get("Origin")
        if origin is not None and urllib.parse.urlsplit(origin).netloc not in ALLOWED_HOSTS:
            return self._send(403, "Bad origin", "text/plain")
        if self.headers.get("X-Homelab-GUI") != "1":
            return self._send(403, "Missing header", "text/plain")
        if self.path != "/api/action":
            return self._send(404, "Not found", "text/plain")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(min(length, 4096)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "bad request"})
        verb, scope = body.get("verb"), body.get("scope")
        if verb not in ("up", "down") or scope not in SCOPES:
            return self._json(400, {"error": "verb must be up|down and scope one of " + ", ".join(sorted(SCOPES))})
        job_id = start_job(verb, scope)
        if job_id is None:
            return self._json(409, {"error": "another action is still running"})
        return self._json(202, {"id": job_id})

    def _static(self, name, ctype):
        try:
            with open(os.path.join(HERE, name), "rb") as fh:
                return self._send(200, fh.read(), ctype)
        except OSError:
            return self._send(404, "Not found", "text/plain")


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    Server(("127.0.0.1", PORT), Handler).serve_forever()
