"""Annonce le monitoring à Home Assistant pour que l'intégration le propose toute seule."""
import json
import os
import time
import urllib.request

TOKEN_FILE = "/data/ha_token"
SUPERVISOR = "http://supervisor"
HEADERS = {"Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}"}


def supervisor(method, path, body=None):
    req = urllib.request.Request(
        SUPERVISOR + path,
        method=method,
        headers={**HEADERS, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)["data"]


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
    host = supervisor("GET", "/addons/self/info")["hostname"]
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
