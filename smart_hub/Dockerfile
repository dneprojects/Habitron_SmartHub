#============================#
#  dneprojects'S DOCKERFILE  #
#=== Home Assistant Addon ===#
#============================#
ARG BUILD_FROM=ghcr.io/hassio-addons/base:14.3.3
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
    apk add --no-cache --virtual .build-dependencies \
    \
    && curl -J -L -o /tmp/python.tar.xz \
        "https://www.python.org/ftp/python/${PYTHON_VERSION#v}/Python-${PYTHON_VERSION#v}.tar.xz" \
    && curl -J -L -o /tmp/python.tar.xz.asc \
        "https://www.python.org/ftp/python/${PYTHON_VERSION#v}/Python-${PYTHON_VERSION#v}.tar.xz.asc" \
    \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg \
        --batch \
        --keyserver hkps://keys.openpgp.org \
        --recv-keys "$GPG_KEY" \
    && gpg \
        --batch \
        --verify /tmp/python.tar.xz.asc /tmp/python.tar.xz \
    && { command -v gpgconf > /dev/null && gpgconf --kill all || :; } \
    \
    && mkdir -p /usr/src/python \
    && tar -xJC /usr/src/python --strip-components=1 -f /tmp/python.tar.xz \
    && cd /usr/src/python \
    \
    && gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)" \
    && ./configure \
        --build="$gnuArch" \
        --enable-loadable-sqlite-extensions \
        --enable-optimizations \
        --enable-option-checking=fatal \
        --enable-shared \
        --with-lto \
        --with-system-expat \
        --without-ensurepip \
    \
    && make -j "$(nproc)" \
        EXTRA_CFLAGS="-DTHREAD_STACK_SIZE=0x100000" \
        LDFLAGS="-Wl,--strip-all" \
    && make install \
    \
    && find /usr/local \
        -type f \
        -executable \
        -not \( -name '*tkinter*' \) \
        -exec scanelf \
        --needed \
        --nobanner \
        --format '%n#p' '{}' ';' \
            | tr ',' '\n' \
            | sort -u \
            | awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 { next } { print "so:" $1 }' \
            | xargs -rt apk add --no-cache --virtual .python-rundeps \
    \
    && cd /usr/local/bin \
    && ln -s idle3 idle \
    && ln -s pydoc3 pydoc \
    && ln -s python3 python \
    && ln -s python3-config python-config \
    \
    && curl -J -L -o /tmp/get-pip.py \
        'https://bootstrap.pypa.io/get-pip.py' \
    \
    && python /tmp/get-pip.py \
        --disable-pip-version-check \
        --no-cache-dir \
        --no-compile \
        "pip==$PYTHON_PIP_VERSION" \
        "setuptools==$PYTHON_SETUPTOOLS_VERSION" \
    \
    && apk del --no-cache --purge .build-dependencies \
    && rm -f -r \
        /usr/src \
        "$GNUPGHOME" \
        /tmp/* \
    \
    && python3 --version \
    && pip3 --version \
    \
    && find /usr -depth \
        \( \
            \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) \
            -o \
            \( -type f -a \( -name '*.pyc' -o -name '*.pyo' -o -name 'libpython*.a' \) \) \
        \) -exec rm -rf '{}' +

COPY /src/requirements.txt /

RUN pip install --no-cache-dir --upgrade pip==24.0 \
    && pip install --no-cache-dir --requirement requirements.txt

# Add src
COPY /src /src

WORKDIR /src
CMD ["python", "smarthub.py"]

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

