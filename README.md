# Automation Service

A comprehensive automation service for collecting, processing, and storing financial data with Supabase integration.

## 🚀 API Endpoints

- `GET /health` - Health check
- `POST /utgl-gary-wealth-data` - Submit data (first project: Gary wealth data)
- `GET /utgl-gary-wealth-data` - Endpoint info
- `GET /` - API information

*More endpoints will be added as we scale to collect different types of data*

## 🔧 Setup

1. **Database Setup**:
   ```bash
   # Run create_table.sql in your Supabase SQL Editor
   ```

2. **Configuration**:
   ```bash
   cp env.yaml.template env.yaml
   # Edit env.yaml with your Supabase URL and API key
   ```

3. **VM Setup** (for background data collection):
   ```bash
   # Run automated setup script
   chmod +x setup-vm-cron.sh
   ./setup-vm-cron.sh
   # Note the VM IP from output for next step
   ```

4. **Deploy**:
   ```bash
   gcloud run deploy automation-service \
     --source . \
     --env-vars-file env.yaml \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080
   ```

## 📝 Usage Example

```bash
# Submit data (Gary wealth - first project)
curl -X POST https://your-url.run.app/utgl-gary-wealth-data \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "GARY001",
    "wealth_data": {
      "assets": 1500000,
      "net_worth": 1300000
    }
  }'

# Check health
curl https://your-url.run.app/health
```
