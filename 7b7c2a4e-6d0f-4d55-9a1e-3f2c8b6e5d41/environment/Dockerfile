# Agent CLIs, preinstalled so Harbor finds them and skips its run-time install: the task image then needs no
# network at setup ([environment] network_mode = "no-network"). Same versions Harbor installs: Node 22,
# @openai/codex 0.166.0 and Claude Code 2.1.311 (stable channel), linked into /usr/local/bin as Harbor does.
FROM node:22.23.4-bookworm-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS agent-cli
RUN npm install -g --no-fund --no-audit @openai/codex@0.166.0 @anthropic-ai/claude-code@2.1.311 \
    && npm cache clean --force

FROM golang:1.26.10-bookworm@sha256:23ce71337b726608afb1bc00986e630a05034a87a87ea1fc2cd1ae5cf33387eb
ENV GOTOOLCHAIN=local GOFLAGS=-mod=mod GOPROXY=off GOSUMDB=off CGO_ENABLED=0
COPY raft/go.mod raft/go.sum /opt/deps/
RUN cd /opt/deps && GOPROXY=https://proxy.golang.org go mod download all \
 && rm -rf /opt/deps && test ! -d /go/pkg/mod/go.etcd.io/raft \
 && chmod -R a+rX /go/pkg/mod
COPY raft /workspace/raft
RUN mkdir -p /workspace/output && chown -R 1000:1000 /workspace /go \
 && mkdir -p /home/agent && chown 1000:1000 /home/agent
ENV HOME=/home/agent GOCACHE=/home/agent/.cache/go-build
WORKDIR /workspace
USER 1000:1000
RUN cd /workspace/raft && go build ./... && go vet ./... >/dev/null && go test -count=1 ./... >/dev/null
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
