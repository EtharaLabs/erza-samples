# syntax=docker/dockerfile:1.19@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

# Clamps the timestamps RUN steps write (useradd, apt); the image exporter still needs it as a build argument.
ARG SOURCE_DATE_EPOCH=1793606400

# Stages the shipped library copy and the specification texts, and refuses version-control residue.
FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS source
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY fast_float /stage/fast_float
COPY spec /stage/spec
RUN python - <<'PY'
import pathlib
root = pathlib.Path("/stage")
bad = [str(p) for p in root.rglob("*") if p.name in {".git", ".gitmodules", ".github"} or p.suffix in {".orig", ".rej", ".patch", ".diff"}]
if bad:
    raise SystemExit(f"version-control or patch residue: {bad}")
headers = sorted(p.name for p in (root / "fast_float/include/fast_float").iterdir())
if len(headers) != 9:
    raise SystemExit(f"unexpected header set: {headers}")
print("staged", sum(1 for p in root.rglob("*") if p.is_file()), "files")
PY

# Agent CLIs, preinstalled so Harbor finds them and skips its run-time install: the task image then needs no
# network at setup ([environment] network_mode = "no-network"). Same versions Harbor installs: Node 22,
# @openai/codex 0.166.0 and Claude Code 2.1.311 (stable channel), linked into /usr/local/bin as Harbor does.
FROM node:22.23.4-bookworm-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS agent-cli
RUN npm install -g --no-fund --no-audit @openai/codex@0.166.0 @anthropic-ai/claude-code@2.1.311 \
    && npm cache clean --force

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS runtime
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
LABEL org.opencontainers.image.source="https://github.com/fastfloat/fast_float" \
      org.opencontainers.image.revision="dbeabeeb3e6791cb96994c2a7a084c36e62ccfb2" \
      org.opencontainers.image.licenses="Apache-2.0 OR BSL-1.0 OR MIT" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159"
RUN groupadd --gid 1000 agent && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash agent
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261026T041303Z trixie-security main' \
      > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends g++=4:14.2.0-1 gcc=4:14.2.0-1 libc6-dev=2.41-12+deb13u4 \
      libssl3t64=3.5.7-1~deb13u3 openssl=3.5.7-1~deb13u3 \
 && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log /var/log/apt /var/log/alternatives.log /var/cache/ldconfig/aux-cache
# The snapshot pin is for the build only; anything installed at run time uses the base image's default mirror.
COPY --from=python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 \
     /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources
RUN rm -f /etc/apt/sources.list
COPY --from=source --chown=1000:1000 /stage/fast_float /workspace/fast_float
COPY --from=source --chown=1000:1000 /stage/spec /workspace/spec
RUN install -d -o 1000 -g 1000 /workspace/output && chown 1000:1000 /workspace
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
USER 1000:1000
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
