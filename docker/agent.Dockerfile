FROM python:3.12-slim
RUN pip install --no-cache-dir pytest && apt-get update -qq && apt-get install -y -qq curl >/dev/null && rm -rf /var/lib/apt/lists/*
RUN useradd -m agent && mkdir /work && chown agent /work
USER agent
WORKDIR /work
CMD ["sleep", "infinity"]
