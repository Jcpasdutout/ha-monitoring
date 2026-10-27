#!/bin/sh
# Démarre le monitoring dans l'add-on : base SQLite dans /data (conservée et sauvegardée par Home Assistant).
set -e
OPTIONS=/data/options.json

# Reprise d'une installation existante : un monitoring.db déposé dans /share/monitoring/
# est copié au premier démarrage, tant que l'add-on n'a pas encore de base.
if [ ! -f /data/monitoring.db ] && [ -f /share/monitoring/monitoring.db ]; then
  echo "Reprise de la base /share/monitoring/monitoring.db"
  cp /share/monitoring/monitoring.db /data/monitoring.db
fi

ARGS=""
if [ -f "$OPTIONS" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('$OPTIONS')).get('reset_admin') else 1)"; then
  echo "Option reset_admin activée : pensez à la désactiver après avoir recréé le compte."
  ARGS="--reset-admin"
fi

export MONITORING_DATA=/data MONITORING_HOST=0.0.0.0 MONITORING_PORT=8080
cd /opt/monitoring
exec python3 server.py $ARGS
