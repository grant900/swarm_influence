FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi uvicorn pydantic httpx
WORKDIR /srv
COPY commons /srv/commons
ENV SITE_DB=/srv/data/site.db CONTENT_PACK=/srv/pack.json
CMD ["uvicorn", "commons.main:app", "--host", "0.0.0.0", "--port", "80"]
