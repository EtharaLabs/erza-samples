# syntax=docker/dockerfile:1.19@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

# Clamps the timestamps RUN steps write (useradd, pip, cargo); the image exporter still needs it as a build argument.
ARG SOURCE_DATE_EPOCH=1791720447

FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS source
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG REGRESS_COMMIT=0328ab6828471b6a8ed3b9acb8b256e285b65abc
ARG REGRESS_ARCHIVE_SHA256=176f6140b43f9410787acc50c26f930def646b21031a93101ddc6d0bd22d565b
# The gh-pages commit that published ES2025; its 2025/index.html is the page tc39.es/ecma262/2025/ serves, byte for byte.
ARG SPEC_URL=https://raw.githubusercontent.com/tc39/ecma262/d2183a3577d44747c11823d8880b85f07ab92dea/2025/index.html
ARG SPEC_SHA256=c1f9a15946c7dd94b13f56564fa6549cc6f212fd35101f8f5e38a32a0efbefe1
COPY sanitize.py Cargo.lock /stage/
RUN python - <<'PY'
import hashlib, io, os, re, shutil, subprocess, tarfile, urllib.request
commit = os.environ["REGRESS_COMMIT"]
data = urllib.request.urlopen(f"https://codeload.github.com/ridiculousfish/regress/tar.gz/{commit}", timeout=600).read()
if hashlib.sha256(data).hexdigest() != os.environ["REGRESS_ARCHIVE_SHA256"]:
    raise SystemExit("regress archive digest mismatch")
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    archive.extractall("/fetch", filter="data")
shutil.move(f"/fetch/regress-{commit}", "/regress")
subprocess.run(["python", "/stage/sanitize.py", "/regress"], check=True)
shutil.copy("/stage/Cargo.lock", "/regress/Cargo.lock")
spec = urllib.request.urlopen(os.environ["SPEC_URL"], timeout=600).read()
if hashlib.sha256(spec).hexdigest() != os.environ["SPEC_SHA256"]:
    raise SystemExit("specification digest mismatch")
text = spec.decode("utf-8")
# The page needs no script or external stylesheet to be read; drop them so the file stands alone.
text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S)
text = re.sub(r"<link\b[^>]*>", "", text)
os.makedirs("/spec", exist_ok=True)
open("/spec/ecma262-2025.html", "w").write(text)
open("/spec/NOTICE.md", "w").write(
    "ECMAScript 2025 Language Specification (ECMA-262, 16th edition), rendered from tc39/ecma262 tag es2025\n"
    "(commit 84b38ad852ff426795fa29cebc06949027336c64) as published at https://tc39.es/ecma262/2025/.\n\n"
    "Copyright Ecma International. The natural language text is used under the Alternative copyright notice of\n"
    "the Ecma text copyright policy: https://ecma-international.org/policies/by-ipr/ecma-text-copyright-policy/\n"
    "Scripts and external stylesheets of the published page are removed.\n")
PY

FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS toolchain
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG TARGETARCH
ARG RUST_VERSION=1.98.1
ARG RUST_SHA256_AMD64=5326b36c53de11d148c8f8dab6553a3d1006c2cfd32123683073fad3c302605b
ARG RUST_SHA256_ARM64=0b514a8cc1cbcd939bff0f151661fe58b6ea5c7a7f645a5098c69e32e8c1e0a2
RUN python - <<'PY'
import hashlib, os, subprocess, tarfile, urllib.request
arch = {"amd64": "x86_64", "arm64": "aarch64"}[os.environ["TARGETARCH"]]
want = os.environ["RUST_SHA256_AMD64" if arch == "x86_64" else "RUST_SHA256_ARM64"]
name = f"rust-{os.environ['RUST_VERSION']}-{arch}-unknown-linux-gnu"
data = urllib.request.urlopen(f"https://static.rust-lang.org/dist/{name}.tar.xz", timeout=1800).read()
if hashlib.sha256(data).hexdigest() != want:
    raise SystemExit("rust archive digest mismatch")
open("/rust.tar.xz", "wb").write(data)
with tarfile.open("/rust.tar.xz") as archive:
    archive.extractall("/", filter="data")
subprocess.run([f"/{name}/install.sh", "--prefix=/opt/rust", "--disable-ldconfig",
                f"--components=rustc,cargo,rust-std-{arch}-unknown-linux-gnu"], check=True)
PY

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS vendor
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=toolchain /opt/rust /opt/rust
COPY --from=source /regress /regress
ENV PATH=/opt/rust/bin:$PATH
RUN cargo vendor --locked --manifest-path /regress/Cargo.toml /vendor > /vendor-config.toml \
 && rm -rf /root/.cargo

# Agent CLIs, preinstalled so Harbor finds them and skips its run-time install: the task image then needs no
# network at setup ([environment] network_mode = "no-network"). Same versions Harbor installs: @openai/codex
# 0.166.0 and Claude Code 2.1.311 (stable channel), linked into /usr/local/bin. Only the packages are copied, not
# Node 22: Node's V8 is a complete ECMAScript RegExp reference, so codex is linked to its native binary instead
# of the codex.js launcher, and claude is native.
FROM node:22.23.4-bookworm-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS agent-cli
RUN npm install -g --no-fund --no-audit @openai/codex@0.166.0 @anthropic-ai/claude-code@2.1.311 \
    && npm cache clean --force

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS runtime
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
LABEL org.opencontainers.image.source="https://github.com/ridiculousfish/regress" \
      org.opencontainers.image.revision="0328ab6828471b6a8ed3b9acb8b256e285b65abc" \
      org.opencontainers.image.licenses="MIT OR Apache-2.0" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159"
RUN groupadd --gid 1000 agent && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash agent
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261026T041303Z trixie-security main' \
      > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gcc=4:14.2.0-1 libc6-dev=2.41-12+deb13u4 patch=2.8-2 \
      libssl3t64=3.5.7-1~deb13u3 openssl=3.5.7-1~deb13u3 \
 && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log /var/log/apt /var/log/alternatives.log /var/cache/ldconfig/aux-cache \
 && printf '%s\n' "export PATH=/opt/rust/bin:\$PATH" > /etc/profile.d/rust.sh
# The snapshot pin is for the build only; anything installed at run time uses the base image's default mirror.
COPY --from=python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 \
     /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources
RUN rm -f /etc/apt/sources.list
COPY --from=toolchain /opt/rust /opt/rust
COPY --from=vendor /vendor /opt/cargo-vendor
COPY --from=vendor /vendor-config.toml /opt/cargo-home/config.toml
RUN sed -i 's#directory = "/vendor"#directory = "/opt/cargo-vendor"#' /opt/cargo-home/config.toml \
 && printf '\n[net]\noffline = true\n' >> /opt/cargo-home/config.toml \
 && chmod -R a+rX /opt/rust /opt/cargo-vendor /opt/cargo-home
COPY --from=source --chown=1000:1000 /regress /workspace/regress
COPY --from=source --chown=1000:1000 /spec /workspace/spec
RUN install -d -o 1000 -g 1000 /workspace/output /home/agent/.cargo && chown 1000:1000 /workspace
ENV PATH=/opt/rust/bin:$PATH \
    CARGO_HOME=/home/agent/.cargo \
    CARGO_NET_OFFLINE=true \
    PYTHONDONTWRITEBYTECODE=1
RUN cp /opt/cargo-home/config.toml /home/agent/.cargo/config.toml && chown -R 1000:1000 /home/agent/.cargo
WORKDIR /workspace
USER 1000:1000
CMD ["/bin/bash"]
# Harbor runs agent setup as the image user; the agent itself runs as [agent].user (1000:1000).
USER root
COPY --from=agent-cli /usr/local/lib/node_modules/@openai/codex /usr/local/lib/node_modules/@openai/codex
COPY --from=agent-cli /usr/local/lib/node_modules/@anthropic-ai/claude-code /usr/local/lib/node_modules/@anthropic-ai/claude-code
RUN rg_bin="$(find /usr/local/lib/node_modules/@openai/codex -type f -path '*/codex-path/rg' | head -n 1)" \
    && codex_bin="$(find /usr/local/lib/node_modules/@openai/codex -type f -path '*/vendor/*/bin/codex' | head -n 1)" \
    && test -x "$rg_bin" && test -x "$codex_bin" \
    && ln -sf "$codex_bin" /usr/local/bin/codex \
    && ln -sf /usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe /usr/local/bin/claude \
    && ln -sf "$rg_bin" /usr/local/bin/rg \
    && mkdir -p /tmp/cli-check \
    && HOME=/tmp/cli-check CODEX_HOME=/tmp/cli-check sh -c 'codex --version && claude --version && rg --version' \
    && rm -rf /tmp/cli-check \
    && ! command -v node
# Codex runs gpt-6.x tool calls as JavaScript in codex-code-mode-host (catalog tool_mode "code_mode_only"), a V8
# whose RegExp implements ECMAScript 2025 section 22.2 in full, duplicate named groups and the v flag included
# (measured in this image). Disabling code mode alone makes Codex refuse every tool call, so the managed config
# instead points Codex at its own catalog with tool_mode cleared for every model (plain shell tools, as Codex
# already uses for models without code mode), and the host is removed. The catalog is generated from this build.
RUN mkdir -p /etc/codex /tmp/cli-check \
    && chmod 0755 /etc/codex \
    && HOME=/tmp/cli-check CODEX_HOME=/tmp/cli-check codex debug models > /tmp/cli-check/models.json \
    && python3 -c "import json,sys; c=json.load(open(sys.argv[1])); [m.update(tool_mode=None, node_repl_disabled=True) for m in c['models']]; json.dump(c, open(sys.argv[2], 'w'))" /tmp/cli-check/models.json /etc/codex/model-catalog.json \
    && printf 'model_catalog_json = "/etc/codex/model-catalog.json"\n' > /etc/codex/managed_config.toml \
    && chmod 0444 /etc/codex/model-catalog.json /etc/codex/managed_config.toml \
    && find /usr/local/lib/node_modules/@openai/codex -type f -name codex-code-mode-host -delete \
    && ! find / -xdev -name codex-code-mode-host | grep -q . \
    && rm -rf /tmp/cli-check && mkdir -p /tmp/cli-check \
    && HOME=/tmp/cli-check CODEX_HOME=/tmp/cli-check codex debug models \
       | python3 -c "import json,sys; m=json.load(sys.stdin)['models']; sys.exit(0 if m and all(x.get('tool_mode') is None for x in m) else 1)" \
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
# Claude Code is a Bun runtime: BUN_OPTIONS=--preload=<file> runs any script in it, and its RegExp
# implements ECMAScript 2025 section 22.2 in full (316 of the 317 hidden expected results). Of the ways to
# run a script in that binary (BUN_OPTIONS, BUN_BE_BUN, a bun or node argv0, NODE_OPTIONS, bunfig.toml,
# a script argument), only BUN_OPTIONS works; Bun's lookup of it is disabled in every copy of the binary,
# and the build checks that a preload no longer runs while Claude Code still starts.
COPY claude_no_preload.py /tmp/claude_no_preload.py
RUN find / -xdev -type f \( -name claude.exe -o -name claude \) -path '*claude-code*' > /tmp/claude-bins \
    && test -s /tmp/claude-bins && cat /tmp/claude-bins \
    && mkdir -p /tmp/preload-check && printf 'console.log("PRELOAD-RAN")\n' > /tmp/preload-check/x.js \
    && chmod -R a+rX /tmp/preload-check \
    && while read -r f; do \
         python3 /tmp/claude_no_preload.py "$f" || exit 1; \
         for opt in "--preload=/tmp/preload-check/x.js" "--preload /tmp/preload-check/x.js"; do \
           out="$(cd /tmp/preload-check && setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/preload-check BUN_OPTIONS="$opt" "$f" --version 2>&1)"; \
           echo "$f [$opt]: $out"; \
           echo "$out" | grep -q PRELOAD-RAN && exit 1; \
           echo "$out" | grep -q '(Claude Code)' || exit 1; \
         done; \
       done < /tmp/claude-bins \
    && rm -rf /tmp/claude_no_preload.py /tmp/claude-bins /tmp/preload-check
