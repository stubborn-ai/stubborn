# Stubborn E2E toolchain image
#
# Includes: JDK 21, Maven, scip-java, Python 3, stubborn CLI
#
# Build (from repo root):
#   docker compose build
#
# Interactive shell:
#   docker compose run --rm shell

FROM eclipse-temurin:21-jdk-noble

ARG SCIP_JAVA_VERSION=0.12.3

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        gzip \
        maven \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Coursier launcher → scip-java on PATH
RUN curl -fL "https://github.com/coursier/launchers/raw/master/cs-x86_64-pc-linux.gz" \
        | gzip -d > /usr/local/bin/cs \
    && chmod +x /usr/local/bin/cs \
    && printf '#!/bin/sh\nexec cs launch com.sourcegraph:scip-java_2.13:%s -- "$@"\n' \
        "${SCIP_JAVA_VERSION}" > /usr/local/bin/scip-java \
    && chmod +x /usr/local/bin/scip-java

WORKDIR /opt/stubborn

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY proto ./proto

RUN pip3 install --no-cache-dir --break-system-packages -e ".[dev]"

COPY scripts/resolve_symbol.py /opt/stubborn/scripts/

# Default CLI; compose services override entrypoint/command as needed
ENTRYPOINT ["stubborn"]
CMD ["--help"]
