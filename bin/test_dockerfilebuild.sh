#!/bin/bash

# Create a docker ignore to speed up context
cat << EOF > .dockerignore
*
!.devcontainer
EOF

DOCKER_BUILDKIT=0 docker build . -f .devcontainer/Dockerfile \
  -t foo:bar \
  --build-arg VARIANT="3.9" \
  --build-arg INSTALL_NODE="true" \
  --build-arg NODE_VERSION="lts/*" \
  --build-arg SHELLCHECK_VERSION="0.7.2" \
  --build-arg SHELLCHECK_CHECKSUM="70423609f27b504d6c0c47e340f33652aea975e45f312324f2dbf91c95a3b188" \
rm .dockerignore