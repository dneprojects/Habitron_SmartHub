#============================#
#  dneprojects'S DOCKERFILE  #
#=== Home Assistant Addon ===#
#============================#
ARG BUILD_FROM=ghcr.io/hassio-addons/base:15.0.2
# hadolint ignore=DL3006
ARG BUILD_VERSION
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY /src/requirements.txt ./

RUN \
    apk add --no-cache \
        aiohttp=3.9.1 \
        aioserial=1.3.1 \
        multidict=6.0.4 \
        psutil=5.9.6 \
        py_cpuinfo=9.0.0 \
        pymodbus=3.6.2 \
        pyserial=3.5 \
        pyserial_asyncio=0.6 \
        PyYAML=6.0.1 \
        websockets=12.0
       

# Add src
COPY /src /src

WORKDIR /src
CMD ["python3", "smarthub.py"]

# Labels 

ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="dneprojects (https://github.com/dneprojects)" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Add-ons" \
    org.opencontainers.image.authors="dneprojects (https://github.com/dneprojects)" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://github.com/dneprojects" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

