# Define function directory
ARG FUNCTION_DIR="/function"

FROM python:3.13-slim@sha256:914bf5c12ea40a97a78b2bff97fbdb766cc36ec903bfb4358faf2b74d73b555b

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends ca-certificates curl git gstreamer1.0-libav libnss3-tools libatk-bridge2.0-0 libcups2-dev libxkbcommon-x11-0 libxcomposite-dev libxrandr2 libgbm-dev libgtk-3-0 libxshmfence-dev gnupg2 postgresql-client openssh-client python3-pip vim wget xz-utils zsh entr \
    && apt-get autoremove -y && apt-get clean -y

ARG FUNCTION_DIR
WORKDIR ${FUNCTION_DIR}

RUN mkdir -p /pymodules
ENV PYTHONPATH=/pymodules

COPY ./requirements.txt ${FUNCTION_DIR}


RUN python3.13 -m pip install -r ${FUNCTION_DIR}/requirements.txt --target /pymodules

# Install the runtime interface client
RUN pip install \
    --target /pymodules \
    awslambdaric

# Copy function code
COPY . ${FUNCTION_DIR}

# Set build variables
ARG git_sha 
ENV GIT_SHA=$git_sha

# Install lambda runtime interactive environment
ARG RIE_VERSION=1.1
RUN wget -O aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/download/${RIE_VERSION}/aws-lambda-rie \
    && mv aws-lambda-rie /usr/bin/aws-lambda-rie
COPY bin/entry.sh /
RUN chmod 755 /usr/bin/aws-lambda-rie /entry.sh

ENTRYPOINT [ "/entry.sh" ]
CMD [ "main.handler" ]
