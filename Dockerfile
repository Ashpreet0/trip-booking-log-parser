# 3.11+ so datetime.fromisoformat accepts the "Z" suffix
FROM python:3.13-slim
WORKDIR /app
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
# code and tests only; the log is mounted at run time, never copied in
COPY parse_log.py summarize.py test_parse_log.py test_summarize.py ./
ENTRYPOINT ["python3", "summarize.py"]
