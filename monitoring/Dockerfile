ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.21
FROM $BUILD_FROM

# Python (bibliothèque standard uniquement) et la commande ping pour les sondes ICMP.
RUN apk add --no-cache python3 iputils

COPY app /opt/monitoring
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
