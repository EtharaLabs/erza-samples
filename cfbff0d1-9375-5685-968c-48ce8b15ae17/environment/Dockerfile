# syntax=docker/dockerfile:1.19@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

FROM --platform=$BUILDPLATFORM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS source
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG REGRESS_COMMIT=0328ab6828471b6a8ed3b9acb8b256e285b65abc
ARG REGRESS_ARCHIVE_SHA256=176f6140b43f9410787acc50c26f930def646b21031a93101ddc6d0bd22d565b
ARG SPEC_URL=https://tc39.es/ecma262/2025/
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

FROM --platform=$BUILDPLATFORM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS toolchain
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

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS vendor
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=toolchain /opt/rust /opt/rust
COPY --from=source /regress /regress
ENV PATH=/opt/rust/bin:$PATH
RUN cargo vendor --locked --manifest-path /regress/Cargo.toml /vendor > /vendor-config.toml \
 && rm -rf /root/.cargo

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS runtime
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
LABEL org.opencontainers.image.source="https://github.com/ridiculousfish/regress" \
      org.opencontainers.image.revision="0328ab6828471b6a8ed3b9acb8b256e285b65abc" \
      org.opencontainers.image.licenses="MIT OR Apache-2.0" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337"
RUN groupadd --gid 1000 agent && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash agent
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261020T000000Z bookworm main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261026T041303Z bookworm-security main' \
      > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gcc=4:12.2.0-3 libc6-dev=2.36-9+deb12u14 patch=2.7.6-7 \
      libssl3=3.0.22-1~deb12u2 openssl=3.0.22-1~deb12u2 \
 && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log /var/log/apt /var/log/alternatives.log /var/cache/ldconfig/aux-cache \
 && printf '%s\n' 'export PATH=/opt/rust/bin:$PATH' > /etc/profile.d/rust.sh
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
