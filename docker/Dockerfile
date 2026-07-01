# Stubborn E2E toolchain image
#
# Includes: JDK 21, Maven, scip-java, Python 3, stubborn CLI
#
# Build (from repo root):
#   docker compose build
#
# Run demo-spring E2E:
#   docker compose run --rm e2e
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

COPY docker/run-e2e.sh /usr/local/bin/run-demo-e2e
RUN sed -i 's/\r$//' /usr/local/bin/run-demo-e2e && chmod +x /usr/local/bin/run-demo-e2e

COPY docker/run-petclinic-e2e.sh /usr/local/bin/run-petclinic-e2e
RUN sed -i 's/\r$//' /usr/local/bin/run-petclinic-e2e && chmod +x /usr/local/bin/run-petclinic-e2e

COPY docker/run-dukesbank-e2e.sh /usr/local/bin/run-dukesbank-e2e
RUN sed -i 's/\r$//' /usr/local/bin/run-dukesbank-e2e && chmod +x /usr/local/bin/run-dukesbank-e2e

COPY examples/spring-petclinic/upstream.pin /opt/stubborn/examples/spring-petclinic/upstream.pin
COPY scripts/resolve_symbol.py scripts/verify_petclinic_context.py \
    scripts/verify_demo_context.py scripts/verify_controller_context.py \
    scripts/verify_pay_flow_context.py scripts/verify_dukesbank_context.py \
    /opt/stubborn/scripts/

# Default CLI; compose services override entrypoint/command as needed
ENTRYPOINT ["stubborn"]
CMD ["--help"]
