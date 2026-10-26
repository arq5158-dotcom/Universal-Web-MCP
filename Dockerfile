# Ashzo MCP: dashboard, MCP server and the Ashzo Browser in one image.
#   docker compose up -d --build      (then open http://localhost:8000)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DISPLAY=:99 \
    ASHZO_HOST=0.0.0.0 \
    ASHZO_PORT=8000

# ffmpeg: study_video. Xvfb + x11vnc + noVNC: a screen the Ashzo Browser runs on,
# which you can watch and sign in to from your own web browser (port 6080).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg xvfb x11vnc novnc websockify fonts-liberation ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt \
 && python -m playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

COPY . .
COPY docker/entrypoint.sh /usr/local/bin/ashzo-entrypoint
RUN chmod +x /usr/local/bin/ashzo-entrypoint

EXPOSE 8000 6080
VOLUME ["/data"]

ENTRYPOINT ["ashzo-entrypoint"]
CMD ["python", "app.py"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if b'ashzo-mcp' in urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).read() else 1)"
