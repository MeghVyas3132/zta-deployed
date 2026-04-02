FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY streamlit_app.py .

# Create .streamlit directory for config
RUN mkdir -p ~/.streamlit

# Streamlit configuration
RUN echo '\
[server]\n\
headless = true\n\
port = 8501\n\
address = "0.0.0.0"\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
' > ~/.streamlit/config.toml

# Create secrets file with API base URL
RUN echo '\
api_base_url = "http://api:8000"\n\
' > ~/.streamlit/secrets.toml

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]
