#!/bin/sh
# Démarre le monitoring dans l'add-on : base SQLite dans /data (conservée et sauvegardée par Home Assistant).
set -e
OPTIONS=/data/options.json

# Reprise d'une installation existante : un monitoring.db déposé dans /share/monitoring/
# est copié au premier démarrage, tant que l'add-on n'a pas encore de base.
if [ ! -f /data/monitoring.db ] && [ -f /share/monitoring/monitoring.db ]; then
  echo "Reprise de la base /share/monitoring/monitoring.db"
  cp /share/monitoring/monitoring.db /data/monitoring.db
  # Clé de chiffrement des mots de passe de cette base (monitoring 2.11 et plus).
  if [ ! -f /data/secret.key ] && [ -f /share/monitoring/secret.key ]; then
    cp /share/monitoring/secret.key /data/secret.key
    chmod 600 /data/secret.key
  fi
fi

ARGS=""
if [ -f "$OPTIONS" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('$OPTIONS')).get('reset_admin') else 1)"; then
  echo "Option reset_admin activée : pensez à la désactiver après avoir recréé le compte."
  ARGS="--reset-admin"
fi

# Clé qui chiffre les mots de passe des sondes, créée au premier démarrage.
export MONITORING_KEY_FILE=/data/secret.key
export MONITORING_DATA=/data MONITORING_HOST=0.0.0.0 MONITORING_PORT=8080
# Jeton réservé à l'intégration Home Assistant, transmis par la découverte (discovery.py).
export MONITORING_TOKEN_FILE=/data/ha_token MONITORING_TOKEN_NAME="Home Assistant (add-on)"
python3 /discovery.py &
cd /opt/monitoring
exec python3 server.py $ARGS
