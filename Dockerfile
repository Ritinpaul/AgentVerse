# AgentVerse All-in-One Multi-Service Production Container
FROM python:3.11-slim

# Install Node.js 18 & Supervisord
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    supervisor \
    libpq-dev \
    gcc \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy entire repository
COPY . /workspace

# Install Python dependencies for all backend services
RUN pip install --no-cache-dir hatchling \
    && pip install --no-cache-dir -r /workspace/AgentStore/backend/requirements.txt \
    && pip install --no-cache-dir -r /workspace/AgentGovernOS/services/governance-api/requirements.txt \
    && pip install --no-cache-dir -e /workspace/AgentOS/services/control-plane \
    && pip install --no-cache-dir -e /workspace/AgentOS/services/execution-plane \
    && pip install --no-cache-dir -e /workspace/AgentOS/services/state-plane

# Install Node dependencies for frontends
RUN cd /workspace/AgentStore/frontend && npm ci \
    && cd /workspace/console && npm ci

# Configure Supervisord for process management
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose all ecosystem ports
EXPOSE 3000 8005 8010 8012 8014 8025 8050

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
