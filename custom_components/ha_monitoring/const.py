"""Constantes de l'intégration Monitoring."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ha_monitoring"

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_MAIL_PREVIEW: Final = "mail_preview"

DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10
DEFAULT_MAIL_PREVIEW: Final = True

DEFAULT_TIMEOUT: Final = timedelta(seconds=15)

# Statuts renvoyés par le monitoring, plus deux états calculés ici.
STATUS_OK: Final = "ok"
STATUS_WARNING: Final = "warning"
STATUS_ERROR: Final = "error"
STATUS_PENDING: Final = "pending"
STATUS_PAUSED: Final = "paused"
STATUSES: Final = [STATUS_OK, STATUS_WARNING, STATUS_ERROR, STATUS_PENDING, STATUS_PAUSED]

PROBE_TYPES: Final = {
    "imap": "Boîte mail (IMAP)",
    "http": "API / site web (HTTP)",
    "ping": "Ping / port TCP",
    "snmp": "Machine distante (SNMP)",
}
