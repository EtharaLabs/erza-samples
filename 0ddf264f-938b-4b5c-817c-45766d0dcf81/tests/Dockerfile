# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
# Verifier image for the Pagecraft chain-repair task; build context is tests/.
# Holds Reward Kit, LiteLLM, pytest and the Pagecraft runtime deps; no agent CLI.

FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS deps
ARG TARGETOS
ARG TARGETARCH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY requirements.lock /tmp/requirements.lock
# Cross-install target-platform wheels (binary only, hash-checked) into a staging prefix.
RUN set -o pipefail \
 && case "${TARGETOS}/${TARGETARCH}" in \
      linux/amd64) arch=x86_64 ;; \
      linux/arm64) arch=aarch64 ;; \
      *) echo "unsupported platform ${TARGETOS}/${TARGETARCH}" >&2; exit 1 ;; \
    esac \
 && python -m venv /opt/verifier \
 && site=/opt/verifier/lib/python3.12/site-packages \
 && /opt/verifier/bin/pip install --require-hashes --no-deps --only-binary=:all: \
      --implementation=cp --python-version=3.12 --abi=cp312 \
      --platform="manylinux_2_34_${arch}" --platform="manylinux_2_28_${arch}" \
      --platform="manylinux_2_17_${arch}" --platform="manylinux2014_${arch}" \
      --upgrade --target="${site}" -r /tmp/requirements.lock \
 && cp -a "${site}/bin/." /opt/verifier/bin/ \
 && rm -rf "${site}/bin"

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS verifier
LABEL org.opencontainers.image.source="https://github.com/vincenzo-afk/Pagecraft" \
      org.opencontainers.image.revision="3fc71e1dd010768bfc059959725dab95991da32f" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim" \
      org.opencontainers.image.base.digest="sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159" \
      org.opencontainers.image.title="pagecraft-chain-repair verifier"
ENV PATH=/opt/verifier/bin:$PATH \
    PIP_NO_INDEX=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=deps /opt/verifier /opt/verifier
COPY --chmod=0755 . /tests
# The judge-unavailable fallback lives outside /tests; its test_output.py is a symlink so the
# compiled criteria resolve their held-out data from /tests exactly as in the main run.
RUN set -o pipefail \
 && mkdir -p /logs/verifier /app /opt/grader \
 && cp -R /tests/__grader__/fallback /opt/grader/fallback \
 && chmod 0644 /opt/grader/fallback/reward.toml /opt/grader/fallback/judge.py \
 && ln -s /tests/test_output.py /opt/grader/fallback/test_output.py \
 && cp -R /tests/__grader__/nojudge /opt/grader/nojudge \
 && chmod 0644 /opt/grader/nojudge/reward.toml \
 && ln -s /tests/test_output.py /opt/grader/nojudge/test_output.py \
 && chown -R 10001:10001 /logs /app
USER root
WORKDIR /tests
CMD ["/bin/bash", "/tests/test.sh"]
