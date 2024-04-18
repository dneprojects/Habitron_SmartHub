#============================#
#  dneprojects'S DOCKERFILE  #
#=== Home Assistant Addon ===#
#============================#
ARG BUILD_FROM
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

# Environment variables
ENV \
    PATH="/usr/local/bin:$PATH" \
    GPG_KEY="7169605F62C751356D054A26A821E680E5FA6305"

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install base system
ARG PYTHON_VERSION="v3.12.2"
ARG PYTHON_PIP_VERSION="24.0"
ARG PYTHON_SETUPTOOLS_VERSION="69.0.3"
# hadolint ignore=DL3003,DL4006,SC2155
RUN \
    set -x \
    && apk add --no-cache \
        py3-pip \
        python3

COPY /src/requirements.txt /

RUN pip install --no-cache-dir --break-system-packages --requirement requirements.txt

# Add src
COPY /src /src
COPY start.sh /start.sh
RUN chmod +x /start.sh
WORKDIR /src
CMD ["/start.sh"]

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

