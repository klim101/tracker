# Minimal image for Streamlit app
FROM python:3.11-slim

# Prevent prompts
ENV PIP_DISABLE_PIP_VERSION_CHECK=on     PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY streamlit_timeline_tracker.py ./

ENV STREAMLIT_SERVER_HEADLESS=true     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_timeline_tracker.py", "--server.port=8501", "--server.address=0.0.0.0"]
