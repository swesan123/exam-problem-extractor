# Deployment Guide

## Overview

This guide covers deploying the Exam Problem Extractor API to production environments.

## Prerequisites

- Python 3.10 or higher
- Docker (optional, for containerized deployment)
- OpenAI API key
- Sufficient disk space for vector database (recommended: 10GB+)

## Environment Variables

### Required Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Optional Variables

- `VECTOR_DB_PATH`: Path to vector database storage (default: `./vector_store/chroma_index`)
- `VECTOR_DB_TYPE`: Vector database type - `chroma` or `faiss` (default: `chroma`)
- `LOG_LEVEL`: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `MAX_FILE_SIZE_MB`: Maximum file upload size in MB (default: `10`)

## Docker Deployment

### Building the Image

```bash
docker build -t exam-problem-extractor:latest .
```

### Running the Container

```bash
docker run -d \
  --name exam-problem-extractor \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/vector_store:/app/vector_store \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  exam-problem-extractor:latest
```

### Docker Compose

Use the provided `docker-compose.yml`:

```bash
# Set environment variables in .env file
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Production Deployment

### Using Gunicorn

For production deployments, use Gunicorn with Uvicorn workers:

```bash
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile /var/log/exam-extractor/access.log \
  --error-logfile /var/log/exam-extractor/error.log \
  --log-level info
```

### Systemd Service

Create `/etc/systemd/system/exam-problem-extractor.service`:

```ini
[Unit]
Description=Exam Problem Extractor API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/exam-problem-extractor
Environment="PATH=/opt/exam-problem-extractor/venv/bin"
Environment="OPENAI_API_KEY=your_key_here"
ExecStart=/opt/exam-problem-extractor/venv/bin/gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable exam-problem-extractor
sudo systemctl start exam-problem-extractor
```

## Health Checks

### Health Endpoint

The service provides a health check endpoint at `/health`:

```bash
curl http://localhost:8000/health
```

Response format:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "exam-problem-extractor",
  "checks": {
    "database": "ok",
    "openai_api": "ok",
    "vector_db": "ok",
    "disk_space": "ok"
  }
}
```

### Monitoring

Set up monitoring to check the health endpoint regularly:

- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Failure Threshold**: 3 consecutive failures

## Security Considerations

### CORS Configuration

Update CORS settings in `app/main.py` for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Rate Limiting

Consider adding rate limiting for production:

```bash
pip install slowapi
```

Configure in `app/main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### SSL/TLS

Use a reverse proxy (nginx, Traefik) for SSL termination:

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Backup Strategy

### Database Backup

The SQLite database is stored in `data/app.db`. Regular backups:

```bash
# Backup script
cp data/app.db backups/app_$(date +%Y%m%d_%H%M%S).db
```

### Vector Store Backup

Backup the vector store directory:

```bash
tar -czf backups/vector_store_$(date +%Y%m%d).tar.gz vector_store/
```

## Scaling

### Horizontal Scaling

For high-traffic deployments:

1. Use a load balancer (nginx, HAProxy)
2. Run multiple instances behind the load balancer
3. Use shared storage for vector database (network filesystem or object storage)
4. Use external database (PostgreSQL) instead of SQLite

### Vertical Scaling

- Increase worker processes: `-w 8` (adjust based on CPU cores)
- Increase timeout for long-running requests
- Allocate more memory for vector database operations

## Troubleshooting

### Common Issues

1. **Database locked**: Ensure only one instance accesses SQLite database
2. **Vector DB errors**: Check disk space and permissions
3. **OpenAI API errors**: Verify API key and check rate limits
4. **Memory issues**: Reduce worker count or increase server memory

### Logs

Check application logs:

```bash
# Docker
docker logs exam-problem-extractor

# Systemd
journalctl -u exam-problem-extractor -f
```

## Performance Tuning

- **Workers**: 2-4x CPU cores
- **Timeout**: 60-120 seconds for generation requests
- **Vector DB**: Use ChromaDB for persistent storage, FAISS for high-performance reads
- **Caching**: Consider Redis for frequently accessed data

