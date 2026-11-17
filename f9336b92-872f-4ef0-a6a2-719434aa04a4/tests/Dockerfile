# syntax=docker/dockerfile:1.19@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

# Separate, no-network verifier for the RFC 5545 dateutil repair. Build context: the bundle's tests/.
# The `shipped` stage reconstructs the pristine shipped tree from the pinned upstream archive and the
# private patch series in __grader__/build/patches/ and checks its tree hash; the reference expander
# is at __grader__/ref/rfc5545ref/. Cases, the shipped manifest, the shipped suite baseline, and the
# shipped signatures are produced once at build time from those inputs; no expected answer is
# ever written: the scorer recomputes every expected result with the reference at grading time.

# Clamps the timestamps RUN steps write; the image exporter also needs it as a build argument.
ARG SOURCE_DATE_EPOCH=1792987983

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

# The pristine shipped tree, rebuilt like lib/build.sh's out/shipped: upstream a78cbd81 (codeload
# archive, digest checked, extracted with filter="data") plus 00-strip, R1 R2 R3 R5 R6 R7, P1 P2 P3 P4.
# GNU patch lives in this stage only. SHIPPED_TREE_SHA256 is sha256 over the sorted
# "sha256  ./path" list of every regular file (lib/tools/tree_hash.sh, full digest).
FROM --platform=$BUILDPLATFORM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS shipped
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DATEUTIL_COMMIT=a78cbd81d5d03b5f126eb36edb92bca78972c804
ARG DATEUTIL_ARCHIVE_SHA256=fb25686c99903d306b5d0a0a3b92c481a5843e141f0b486a193d6a9e3a4196ff
ARG SHIPPED_TREE_SHA256=d522a5b7f5f5beddbe803d96d91d2d1efb6cb79adcf617787aefcb740aa6b23b
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie-updates main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261026T041303Z trixie-security main' \
      > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends patch=2.8-2 \
 && rm -rf /var/lib/apt/lists/*
COPY __grader__/build/patches/ /patches/
RUN python3 -I -B - <<'PY'
import hashlib, io, os, shutil, tarfile, urllib.request
commit = os.environ["DATEUTIL_COMMIT"]
data = urllib.request.urlopen(f"https://codeload.github.com/dateutil/dateutil/tar.gz/{commit}", timeout=600).read()
digest = hashlib.sha256(data).hexdigest()
if digest != os.environ["DATEUTIL_ARCHIVE_SHA256"]:
    raise SystemExit(f"dateutil archive digest mismatch: {digest}")
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    archive.extractall("/fetch", filter="data")
shutil.move(f"/fetch/dateutil-{commit}", "/shipped")
PY
RUN cd /shipped \
 && for p in 00-strip R1 R2 R3 R5 R6 R7 P1 P2 P3 P4; do \
      patch -p1 -F0 -N --batch --no-backup-if-mismatch -i "/patches/$p.patch" || { echo "patch $p failed" >&2; exit 1; }; \
    done \
 && test -z "$(find . -name '*.rej' -o -name '*.orig')" \
 && find . -depth -type d -empty -delete \
 && tree=$(find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1) \
 && echo "shipped tree hash $tree" \
 && test "$tree" = "$SHIPPED_TREE_SHA256"

# The verifier's operating system and Python tooling, shared by the bake and runtime stages.
FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS base
ARG SOURCE_DATE_EPOCH
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN groupadd --gid 1000 grader && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash grader \
 && groupadd --gid 1001 sandbox && useradd --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin sandbox
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20261026T041303Z trixie-updates main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20261026T041303Z trixie-security main' \
      > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends tzdata=2026e-0+deb13u1 procps=2:4.0.4-9 \
 && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log /var/log/apt /var/log/alternatives.log /var/cache/ldconfig/aux-cache
RUN --mount=type=bind,from=wheels,source=/wheels,target=/wheels \
    --mount=type=bind,source=requirements.lock,target=/requirements.lock \
    pip install --no-cache-dir --no-index --find-links /wheels --require-hashes -r /requirements.lock
COPY __grader__/runner/ /opt/runner/
# Zone data: Python's TZPATH is the tzdata 2026.5 wheel (IANA 2026e, main form), as in the agent image,
# for the reference, the grader, the child and every suite run; test.sh passes it through env -i.
ENV PYTHONDONTWRITEBYTECODE=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True \
    PYTHONTZPATH=/usr/local/lib/python3.12/site-packages/tzdata/zoneinfo
RUN python3 -I -B -c "import os, pathlib, tzdata, zoneinfo; \
path = str(pathlib.Path(tzdata.__file__).parent / 'zoneinfo'); \
assert path == os.environ['PYTHONTZPATH'], path; assert tzdata.IANA_VERSION == '2026e', tzdata.IANA_VERSION; \
assert zoneinfo.TZPATH == (path,), zoneinfo.TZPATH; \
assert os.path.isfile(os.path.join(path, 'America', 'New_York'))"

# Build-time grading inputs: cases (inputs only), the shipped manifest outside src/dateutil and
# tests, the shipped suite run against the shipped library, and the shipped public signatures.
FROM base AS bake
ARG SOURCE_DATE_EPOCH
# The default generation: the families in gen/contested.py ALWAYS_EXCLUDED are left out always,
# every other family is included (CONTESTED.md). There is no build-time switch.
COPY __grader__/ /opt/grader/
COPY --from=shipped /shipped/ /opt/grader/shipped/
RUN test -f /opt/grader/ref/rfc5545ref/__init__.py && test -f /opt/grader/shipped/src/dateutil/rrule.py \
 && rm -rf /opt/grader/selftest /opt/grader/build \
 && python3 -I -B /opt/grader/grade.py gen --ref /opt/grader/ref --out /bake/cases \
 && python3 -I -B /opt/grader/grade.py manifest --tree /opt/grader/shipped --out /bake/shipped_manifest.json \
 && mkdir -p /bake/lib /bake/suite /bake/run /bake/junit \
 && cp -R /opt/grader/shipped/src/dateutil /bake/lib/dateutil \
 && mkdir /bake/lib/python_dateutil-4.0.0.dist-info \
 && printf 'Metadata-Version: 2.1\nName: python-dateutil\nVersion: 4.0.0\n' > /bake/lib/python_dateutil-4.0.0.dist-info/METADATA \
 && cp -R /opt/grader/shipped/tests /bake/suite/tests \
 && cp /opt/grader/shipped/pyproject.toml /bake/suite/pyproject.toml \
 && chmod -R a+rX,go-w /bake && chown 1001:1001 /bake/run /bake/junit
# The shipped suite on the shipped library, through the same launcher, collection pass, and junit
# file as test.sh, as uid 1001: the baseline of shipped node ids and the ones that pass.
RUN cd /bake/run \
 && as_sandbox() { setpriv --reuid=1001 --regid=1001 --clear-groups --no-new-privs \
      env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/bake/run TMPDIR=/bake/run TZ="${SANDBOX_TZ:-UTC}" LANG=C.UTF-8 \
      PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONTZPATH="$PYTHONTZPATH" "$@"; } \
 && args=(-c /bake/suite/pyproject.toml --rootdir /bake/suite -p no:cacheprovider -o addopts= -o junit_family=xunit1 \
      -W ignore::pytest.PytestUnknownMarkWarning --hypothesis-profile=ci --continue-on-collection-errors -q /bake/suite/tests) \
 && SANDBOX_TZ=America/New_York as_sandbox env PYTHONPATH=/bake/lib python3 -I -B /opt/runner/pytest_launch.py /bake/lib "${args[@]}" --collect-only > /bake/collect.txt \
 && code=0 \
 && { SANDBOX_TZ=America/New_York as_sandbox env PYTHONPATH=/bake/lib python3 -I -B /opt/runner/pytest_launch.py /bake/lib "${args[@]}" --junitxml=/bake/junit/report.xml \
      > /bake/baseline.log 2>&1 || code=$?; } \
 && echo '{"cpu": 0, "exit": 0, "status": "ok"}' > /bake/collect.status.json \
 && echo "{\"cpu\": 0, \"exit\": $code, \"status\": \"ok\"}" > /bake/run.status.json \
 && python3 -I -B /opt/grader/grade.py suite-report --junit /bake/junit/report.xml --collect /bake/collect.txt \
      --collect-status /bake/collect.status.json --status /bake/run.status.json --out /bake/shipped_baseline.json \
 && as_sandbox python3 -I -B /opt/runner/sigs.py /bake/lib 3> /bake/shipped_sigs.json \
 && python3 -I -B -c "import collections,json,sys; r=json.load(open('/bake/shipped_baseline.json')); c=collections.Counter(r.get('outcomes', {}).values()); print('shipped baseline', r.get('exit'), r.get('collect_errors'), dict(sorted(c.items()))); sys.exit(0 if r.get('exit') == 0 and c['failed'] == 0 and c['passed'] > 1000 else 1)"

FROM base AS runtime
ARG SOURCE_DATE_EPOCH
LABEL org.opencontainers.image.title="rfc5545-dateutil verifier" \
      org.opencontainers.image.description="Separate no-network verifier grading a repaired python-dateutil against RFC 5545" \
      org.opencontainers.image.source="https://github.com/dateutil/dateutil" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159"
COPY __grader__/canonical.py __grader__/cli.py __grader__/grade.py __grader__/refload.py __grader__/supervise.py /opt/grader/
COPY __grader__/gen/ /opt/grader/gen/
COPY __grader__/score/ /opt/grader/score/
COPY __grader__/checks/ /opt/grader/checks/
COPY __grader__/reference/REFERENCE.md /opt/grader/reference/REFERENCE.md
COPY __grader__/fallback/ /opt/grader/fallback/
COPY test_output.py /opt/grader/fallback/test_output.py
COPY __grader__/nojudge/ /opt/grader/nojudge/
COPY test_output.py /opt/grader/nojudge/test_output.py
COPY __grader__/ref/rfc5545ref/ /opt/grader/ref/rfc5545ref/
COPY --from=bake /opt/grader/shipped/ /opt/grader/shipped/
COPY --from=bake /bake/cases/ /opt/grader/cases/
COPY --from=bake /bake/shipped_manifest.json /bake/shipped_baseline.json /bake/shipped_sigs.json /opt/grader/
COPY test.sh reward.toml test_output.py judge.toml /tests/
COPY judge/prompt.md /tests/judge/
RUN find /opt/grader /opt/runner /tests -name __pycache__ -prune -exec rm -rf {} + \
 && chown -R 0:0 /opt/runner /tests && chmod -R a+rX,go-w /opt/runner /tests \
 && chmod 0755 /tests/test.sh \
 && chown -R 1000:1000 /opt/grader && chmod -R u+rwX,go-rwx /opt/grader \
 && install -d -o 1000 -g 1000 -m 0755 /workspace /logs/verifier
WORKDIR /workspace
USER root
CMD ["/bin/bash"]
