"""Annonce le monitoring à Home Assistant pour que l'intégration le propose toute seule."""
import json
import os
import socket
import time
import urllib.error
import urllib.request

TOKEN_FILE = "/data/ha_token"
SUPERVISOR = "http://supervisor"


def supervisor_token():
    """Jeton donné par le Supervisor. L'image de base (s6-overlay) le retire de l'environnement
    du script de démarrage, mais le garde dans /run/s6/container_environment."""
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    for path in ("/run/s6/container_environment/SUPERVISOR_TOKEN",
                 "/var/run/s6/container_environment/SUPERVISOR_TOKEN"):
        if token:
            break
        try:
            with open(path, encoding="utf-8") as f:
                token = f.read().strip()
        except OSError:
            pass
    if not token:
        print("Découverte : jeton SUPERVISOR_TOKEN introuvable, le Supervisor refusera l'annonce.")
    return token


HEADERS = {"Authorization": f"Bearer {supervisor_token()}"}


def supervisor(method, path, body=None):
    req = urllib.request.Request(
        SUPERVISOR + path,
        method=method,
        headers={**HEADERS, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)["data"]
    except urllib.error.HTTPError as err:
        # Le Supervisor explique le refus dans sa réponse : on l'affiche dans le journal.
        detail = err.read().decode(errors="replace").strip()
        raise RuntimeError(f"{method} {path} : HTTP {err.code} {detail}") from None


def main():
    # On attend que le serveur réponde : l'intégration le teste dès l'annonce.
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:8080/api/auth", timeout=2).close()
            break
        except OSError:
            time.sleep(1)
    else:
        print("Découverte : le monitoring ne répond pas, annonce abandonnée.")
        return
    with open(TOKEN_FILE, encoding="utf-8") as f:
        token = f.read().strip()
    try:
        host = supervisor("GET", "/addons/self/info")["hostname"]
    except (OSError, RuntimeError) as err:
        # Le conteneur porte déjà le nom d'hôte de l'add-on sur le réseau interne de HA.
        host = socket.gethostname()
        print(f"Découverte : infos de l'add-on illisibles ({err}), nom d'hôte {host} utilisé.")
    supervisor("POST", "/discovery", {
        "service": "ha_monitoring",
        "config": {"host": host, "port": 8080, "token": token},
    })
    print(f"Découverte : monitoring annoncé à Home Assistant ({host}:8080).")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:  # l'add-on doit continuer à tourner même sans découverte
        print(f"Découverte : échec de l'annonce à Home Assistant ({err}).")
