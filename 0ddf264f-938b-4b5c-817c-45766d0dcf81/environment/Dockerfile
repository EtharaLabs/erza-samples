# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
# Agent sandbox for the Pagecraft chain-repair task; build context is environment/.
# Ships Python 3.12, the Pagecraft runtime deps and pytest at hash-locked releases,
# and the defective Pagecraft checkout at /app/repo (importable via a .pth, no
# second copy in site-packages). No VCS history, no credentials, no run-time fetch.

FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS build
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
 && pip install --require-hashes --no-deps --only-binary=:all: \
      --implementation=cp --python-version=3.12 --abi=cp312 \
      --platform="manylinux_2_28_${arch}" --platform="manylinux_2_17_${arch}" --platform="manylinux2014_${arch}" \
      --target=/opt/site -r /tmp/requirements.lock \
 && printf '/app/repo/src\n' > /opt/site/pagecraft-editable.pth \
 && mkdir -p /opt/bin \
 && printf '#!/usr/local/bin/python3\nimport sys\nfrom pagecraft.cli import main\nsys.exit(main())\n' > /opt/bin/pagecraft \
 && printf '#!/usr/local/bin/python3\nimport sys\nimport pytest\nsys.exit(pytest.console_main())\n' > /opt/bin/pytest \
 && chmod 0755 /opt/bin/pagecraft /opt/bin/pytest \
 && rm -rf /opt/site/bin

# Agent CLIs, preinstalled so Harbor finds them and skips its run-time install: the task image then needs no
# network at setup ([environment] network_mode = "no-network"). Same versions Harbor installs: Node 22,
# @openai/codex 0.166.0 and Claude Code 2.1.311 (stable channel), linked into /usr/local/bin as Harbor does.
FROM node:22.23.4-bookworm-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS agent-cli
RUN npm install -g --no-fund --no-audit @openai/codex@0.166.0 @anthropic-ai/claude-code@2.1.311 \
    && npm cache clean --force

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS runtime
LABEL org.opencontainers.image.source="https://github.com/vincenzo-afk/Pagecraft" \
      org.opencontainers.image.revision="3fc71e1dd010768bfc059959725dab95991da32f" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim" \
      org.opencontainers.image.base.digest="sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159" \
      org.opencontainers.image.title="pagecraft-chain-repair agent sandbox"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INDEX=1 PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/agent
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=build /opt/site/ /usr/local/lib/python3.12/site-packages/
COPY --from=build /opt/bin/ /usr/local/bin/
RUN set -o pipefail \
 && groupadd --gid 1000 agent \
 && useradd --uid 1000 --gid 1000 --home-dir /home/agent --create-home --shell /bin/bash agent \
 && find / -xdev -type f -perm /6000 -exec chmod a-s {} + \
 && mkdir -p /app/output \
 && chown 1000:1000 /app/output
COPY --chown=1000:1000 repo/ /app/repo/
USER 1000:1000
WORKDIR /app/repo
CMD ["/bin/bash"]
# Harbor runs agent setup as the image user; the agent itself runs as [agent].user (1000:1000).
USER root
COPY --from=agent-cli /usr/local/bin/node /usr/local/bin/node
COPY --from=agent-cli /usr/local/lib/node_modules/@openai/codex /usr/local/lib/node_modules/@openai/codex
COPY --from=agent-cli /usr/local/lib/node_modules/@anthropic-ai/claude-code /usr/local/lib/node_modules/@anthropic-ai/claude-code
RUN rg_bin="$(find /usr/local/lib/node_modules/@openai/codex -type f -path '*/codex-path/rg' | head -n 1)" \
    && test -x "$rg_bin" \
    && ln -sf /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex \
    && ln -sf /usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe /usr/local/bin/claude \
    && ln -sf "$rg_bin" /usr/local/bin/rg \
    && mkdir -p /tmp/cli-check \
    && HOME=/tmp/cli-check CODEX_HOME=/tmp/cli-check sh -c 'node --version && codex --version && claude --version && rg --version' \
    && rm -rf /tmp/cli-check
# Agent web tools off. Under a plain `harbor run`, Codex offers a web tool that searches through
# api.openai.com/v1/alpha/search and Claude Code offers WebSearch (run by Anthropic's servers) and WebFetch;
# both hosts are on the agent allowlist, so either agent could read the open web despite the no-network
# environment. The system-level (managed) configs below remove the tools and override user config and flags.
RUN mkdir -p /etc/codex /etc/claude-code \
    && chmod 0755 /etc/codex /etc/claude-code \
    && touch /etc/codex/managed_config.toml \
    && chmod 0644 /etc/codex/managed_config.toml \
    && printf 'web_search = "disabled"\n' >> /etc/codex/managed_config.toml \
    && printf '{"permissions": {"deny": ["WebSearch", "WebFetch"]}}\n' > /etc/claude-code/managed-settings.json \
    && chmod 0444 /etc/codex/managed_config.toml /etc/claude-code/managed-settings.json \
    && grep -qx 'web_search = "disabled"' /etc/codex/managed_config.toml \
    && python3 -c "import json; d=set(json.load(open('/etc/claude-code/managed-settings.json'))['permissions']['deny']); raise SystemExit(0 if {'WebSearch','WebFetch'} <= d else 1)"
