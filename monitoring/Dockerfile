ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.21
FROM $BUILD_FROM

# Commit (ou tag) de https://github.com/Jcpasdutout/monitoring à installer, fixé dans build.yaml.
ARG MONITORING_REF

# Python (bibliothèque standard uniquement) et la commande ping pour les sondes ICMP.
RUN apk add --no-cache python3 iputils \
    && mkdir -p /opt/monitoring \
    && curl -fsSL "https://github.com/Jcpasdutout/monitoring/archive/${MONITORING_REF}.tar.gz" \
       | tar xz -C /opt/monitoring --strip-components=1 \
    && rm -rf /opt/monitoring/web /opt/monitoring/deploy \
    && test -f /opt/monitoring/static/index.html

COPY run.sh discovery.py /
RUN chmod a+x /run.sh

CMD ["/run.sh"]
