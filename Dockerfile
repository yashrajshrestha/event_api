## base image
FROM python:3.10-slim AS base

## install dependencies
RUN apt update && apt upgrade -y

## virtualenv
ENV VIRTUAL_ENV=/opt/venv 
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

## build-image
FROM base AS builder
RUN pip install --upgrade pip && \
    pip install pip-tools
WORKDIR /app
COPY requirements.txt . 
RUN pip install -r requirements.txt
COPY init_db.py /app/init_db.py
RUN python init_db.py  # Execute database initialization script

FROM base
# copy Python dependencies from build image
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY . /app
WORKDIR /app

EXPOSE 4449

ENTRYPOINT ["gunicorn", "-w", "4", "-b 0.0.0.0:4449", "app:app", "--timeout", "3600"]
