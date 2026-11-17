# Separate verifier for the Raft safety task; only the LLM judge uses the network.
ARG SOURCE_DATE_EPOCH=1793606400

# Hash-locked pytest, installed into a directory the runtime reads through PYTHONPATH.
FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS pydeps
COPY requirements.lock /requirements.lock
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: --target /pydeps -r /requirements.lock

# Reward Kit 0.2.1 needs Python 3.12. It runs from its own relocatable interpreter and virtual
# environment under /opt, so the grader's Python (bookworm's 3.11 with /opt/pydeps) is unchanged.
FROM golang:1.26.10-bookworm@sha256:23ce71337b726608afb1bc00986e630a05034a87a87ea1fc2cd1ae5cf33387eb AS rewardkit
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /usr/local/bin/uv
COPY rewardkit.lock /rewardkit.lock
ENV UV_NO_CACHE=1 UV_COMPILE_BYTECODE=0 UV_PYTHON_INSTALL_DIR=/opt/rewardkit-python UV_PYTHON_PREFERENCE=only-managed
RUN uv python install 3.12.16 \
 && uv venv --python 3.12.16 /opt/rewardkit \
 && uv pip install --python /opt/rewardkit/bin/python --require-hashes -r /rewardkit.lock \
 && /opt/rewardkit/bin/python -c "import rewardkit, litellm" \
 && find /opt/rewardkit /opt/rewardkit-python -name __pycache__ -prune -exec rm -rf {} +

FROM golang:1.26.10-bookworm@sha256:23ce71337b726608afb1bc00986e630a05034a87a87ea1fc2cd1ae5cf33387eb
ARG SOURCE_DATE_EPOCH
LABEL org.opencontainers.image.source="https://github.com/etcd-io/raft" \
      org.opencontainers.image.revision="c51f010c851edd0dada5af41bafbf68e54617767" \
      org.opencontainers.image.licenses="Apache-2.0"
ENV GOTOOLCHAIN=local CGO_ENABLED=0 GOSUMDB=off GOFLAGS=-mod=mod
# The module's dependencies, fetched at build time and read-only at grading time; no copy of
# the raft module itself enters the module cache.
COPY shipped/go.mod shipped/go.sum /opt/deps/
RUN cd /opt/deps && GOPROXY=https://proxy.golang.org go mod download all \
 && rm -rf /opt/deps && test ! -d /go/pkg/mod/go.etcd.io/raft \
 && chmod -R a+rX /go/pkg/mod
RUN groupadd --gid 1000 grader && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash grader
COPY --from=pydeps /pydeps /opt/pydeps
COPY --from=rewardkit /opt/rewardkit-python /opt/rewardkit-python
COPY --from=rewardkit /opt/rewardkit /opt/rewardkit
COPY __grader__/ /opt/grader/
COPY harness/ /opt/grader/harness/
COPY pristine/ /opt/grader/pristine/
COPY shipped/ /opt/grader/shipped/
# A build cache of the standard library, the dependencies, and the harness against the library as
# shipped, copied into each run's sandbox cache so builds compile only what the submission changed.
RUN cp -R /opt/grader/harness /tmp/h && cd /tmp/h && go mod edit -replace go.etcd.io/raft/v3=/opt/grader/shipped \
 && GOCACHE=/opt/gocache GOPROXY=off GOMAXPROCS=1 go test -p 1 -c -o /tmp/h.test . \
 && cd /opt/grader/shipped && GOCACHE=/opt/gocache GOPROXY=off GOMAXPROCS=1 go test -p 1 -count=1 -run '^$' ./... \
 && rm -rf /tmp/h /tmp/h.test
COPY test_output.py /opt/grader/fallback/test_output.py
COPY test_output.py /opt/grader/nojudge/test_output.py
COPY test.sh judge.toml reward.toml test_output.py /tests/
COPY judge/prompt.md /tests/judge/prompt.md
RUN chown -R 0:0 /opt/grader /opt/pydeps /opt/gocache /opt/rewardkit /opt/rewardkit-python /tests \
 && chmod -R a+rX,go-w /opt/grader /opt/pydeps /opt/gocache /opt/rewardkit /opt/rewardkit-python /tests \
 && chmod 0555 /tests/test.sh \
 && install -d -o 1000 -g 1000 /workspace /logs/verifier
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
CMD ["/bin/bash"]
