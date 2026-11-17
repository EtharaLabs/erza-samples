# syntax=docker/dockerfile:1.19@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

# Clamps the timestamps RUN steps write (useradd, apt, pip); the image exporter still needs it as a build argument.
ARG SOURCE_DATE_EPOCH=1793606400

# The upstream tree at the base, the shipped tree rebuilt from it, its manifest, and pristine
# copies of the kept upstream tests. The verifier never reads a byte the agent could have changed.
FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS source
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG FASTFLOAT_COMMIT=dbeabeeb3e6791cb96994c2a7a084c36e62ccfb2
ARG FASTFLOAT_ARCHIVE_SHA256=973e2e62805ae713e42b1df9bbcbb2ead610fb0525325dc6c00e0be0d30a5e0a
COPY __grader__/build_shipped.py __grader__/restructure.py __grader__/kept_tests.json /stage/
RUN python - <<'PY'
import hashlib, io, json, os, shutil, subprocess, tarfile, urllib.request
commit = os.environ["FASTFLOAT_COMMIT"]
data = urllib.request.urlopen(f"https://codeload.github.com/fastfloat/fast_float/tar.gz/{commit}", timeout=600).read()
if hashlib.sha256(data).hexdigest() != os.environ["FASTFLOAT_ARCHIVE_SHA256"]:
    raise SystemExit("fast_float archive digest mismatch")
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    archive.extractall("/fetch", filter="data")
upstream = f"/fetch/fast_float-{commit}"
subprocess.run(["python", "/stage/build_shipped.py", upstream, "/shipped"], check=True)
# fast_float 8.3.3 as released: the reference the conversion-cost categories count against.
shutil.copytree(f"{upstream}/include", "/reference/include")
manifest = {}
for dirpath, _, files in os.walk("/shipped"):
    for name in files:
        path = os.path.join(dirpath, name)
        manifest[os.path.relpath(path, "/shipped")] = hashlib.sha256(open(path, "rb").read()).hexdigest()
json.dump(manifest, open("/shipped_manifest.json", "w"), sort_keys=True)
os.makedirs("/upstream_tests")
for name in json.load(open("/stage/kept_tests.json")):
    shutil.copyfile(f"{upstream}/tests/{name}.cpp", f"/upstream_tests/{name}.cpp")
print("shipped files:", len(manifest))
PY

FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS wheels
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG TARGETOS
ARG TARGETARCH
COPY requirements.lock /requirements.lock
RUN case "${TARGETARCH}" in \
      amd64) arch=x86_64 ;; \
      arm64) arch=aarch64 ;; \
      *) echo "unsupported ${TARGETOS}/${TARGETARCH}" >&2; exit 1 ;; \
    esac \
 && pip download --no-cache-dir --require-hashes --only-binary=:all: \
      --platform "manylinux_2_28_${arch}" --platform "manylinux_2_17_${arch}" --platform "manylinux2014_${arch}" --platform any \
      --python-version 3.12 --implementation cp --abi cp312 --abi abi3 --abi none \
      -r /requirements.lock -d /wheels

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS runtime
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
LABEL org.opencontainers.image.source="https://github.com/fastfloat/fast_float" \
      org.opencontainers.image.revision="dbeabeeb3e6791cb96994c2a7a084c36e62ccfb2" \
      org.opencontainers.image.licenses="Apache-2.0 OR BSL-1.0 OR MIT" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159"
RUN groupadd --gid 1000 grader && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash grader
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261026T041303Z trixie-security main' \
      > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends g++=4:14.2.0-1 gcc=4:14.2.0-1 libc6-dev=2.41-12+deb13u4 procps=2:4.0.4-9 valgrind=1:3.24.0-3 \
      libssl3t64=3.5.7-1~deb13u3 openssl=3.5.7-1~deb13u3 \
 && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log /var/log/apt /var/log/alternatives.log /var/cache/ldconfig/aux-cache
RUN --mount=type=bind,from=wheels,source=/wheels,target=/wheels \
    --mount=type=bind,source=requirements.lock,target=/requirements.lock \
    pip install --no-cache-dir --no-index --find-links /wheels --require-hashes -r /requirements.lock
COPY --from=source /shipped_manifest.json /opt/grader/shipped_manifest.json
COPY --from=source /upstream_tests /opt/grader/upstream_tests
COPY --from=source /shipped/include /opt/grader/shipped/include
COPY --from=source /reference/include /opt/grader/reference/include
COPY __grader__/probe.cpp __grader__/oracle.py __grader__/cases.py __grader__/test_categories.py \
     __grader__/inspect_submission.py __grader__/cpu_guard.py __grader__/report_items.py \
     __grader__/kept_tests.json __grader__/spec_manifest.json __grader__/meter.cpp __grader__/cost_cases.py /opt/grader/
COPY __grader__/reference/REFERENCE.md /opt/grader/reference/REFERENCE.md
COPY __grader__/fallback/reward.toml __grader__/fallback/judge.py /opt/grader/fallback/
COPY test_output.py /opt/grader/fallback/test_output.py
COPY __grader__/nojudge/reward.toml /opt/grader/nojudge/
COPY test_output.py /opt/grader/nojudge/test_output.py
COPY test.sh test_output.py reward.toml judge.toml /tests/
COPY judge/prompt.md /tests/judge/prompt.md
# The probe built against the headers as shipped, for checking each Reproduction line (K10), and
# the cost meter built against fast_float 8.3.3 as released, for the conversion-cost categories.
RUN install -d /opt/grader/bin \
 && g++ -std=c++17 -O2 -I /opt/grader/shipped/include /opt/grader/probe.cpp -o /opt/grader/bin/shipped_probe \
 && g++ -std=c++17 -O2 -I /opt/grader/reference/include /opt/grader/meter.cpp -o /opt/grader/bin/reference_meter
RUN chown -R 0:0 /opt/grader /tests \
 && chmod -R a+rX,go-w /opt/grader /tests \
 && chmod 0555 /tests/test.sh \
 && install -d -o 1000 -g 1000 /workspace /logs/verifier
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
CMD ["/bin/bash"]
