# TNG Shield Risk API

FastAPI backend for transaction risk scoring with Qwen AI integration.

## Features

- 🤖 AI-powered risk scoring using Qwen VL model
- 🔍 SC Malaysia InvestorAlert integration for merchant verification
- 📋 Rule-based policy engine
- 🚀 FastAPI with automatic API docs
- ☁️ Deploys to AWS App Runner in 3 minutes

## Quick Deploy to AWS

### Cost: ~$12-20/month | Time: 3 minutes

```cmd
deploy.bat
```

That's it! The script will:
1. Ask for your Qwen API key
2. Deploy from GitHub to AWS App Runner
3. Give you a public HTTPS endpoint with `/docs`

**Your API will be live at**: `https://[random-id].ap-southeast-1.awsapprunner.com/docs`

### What You Get

- ✅ Automatic HTTPS endpoint
- ✅ Swagger UI at `/docs`
- ✅ Auto-deploys on `git push`
- ✅ Auto-scales with traffic
- ✅ Health monitoring

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /run-risk-score` | Score transaction risk |
| `GET /docs` | Swagger UI (interactive API docs) |
| `GET /redoc` | ReDoc (alternative docs) |

## Example Request

```bash
curl -X POST "https://your-app.awsapprunner.com/run-risk-score" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn-001",
    "transaction": {
      "amount": 5000,
      "merchant_name": "ABC Trading",
      "channel": "online"
    },
    "customer_profile": {
      "account_age_days": 30
    },
    "context": {}
  }'
```

## Response Example

```json
{
  "transaction_id": "txn-001",
  "risk_score": 65,
  "risk_level": "MEDIUM",
  "decision_band": "LIKELY_SAFE",
  "action": "ALLOW_WITH_WARNING",
  "reasons": [
    "New merchant detected",
    "Transaction amount within normal range"
  ],
  "recommendation": "Proceed with user confirmation"
}
```

## Local Development

```cmd
# Install dependencies
pip install -r requirements.txt

# Copy environment variables
copy .env.example .env
# Edit .env and add your QWEN_API_KEY

# Run locally
python main.py

# Open http://localhost:8000/docs
```

## Delete Deployment

```cmd
delete.bat
```

## Files

```
tng-shield-be/
├── main.py              # FastAPI application
├── rules.txt            # Risk scoring policy rules
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (local dev)
├── deploy.bat           # Deploy to AWS (3 minutes)
├── delete.bat           # Delete AWS deployment
├── apprunner.yaml       # App Runner config (reference)
└── README.md            # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QWEN_API_KEY` | Qwen API key (required) | - |
| `QWEN_BASE_URL` | Qwen API endpoint | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| `QWEN_MODEL` | Model name | `qwen3-vl-plus-2025-12-19` |

## Risk Scoring Logic

The API uses a multi-signal approach:

1. **Blacklist Check** (-100 points): Blocks known bad actors
2. **Merchant Verification** (+40 points): Verified TNG merchants
3. **Business Registration** (+25 points): SSM-registered businesses
4. **Account Age** (+5 to +20 points): Older accounts are trusted more
5. **Transaction History** (+5 to +20 points): Volume and consistency
6. **Prior Relationship** (+30 points): Previous successful transactions
7. **Network Reputation** (+10 to +20 points): Community feedback

**Decision Bands**:
- 80-100: TRUSTED → Allow
- 50-79: LIKELY_SAFE → Allow with warning
- 30-49: UNCERTAIN → Additional verification
- 10-29: SUSPICIOUS → Cooling-off period
- 0-9: HIGH_RISK → Block

## SC Malaysia Integration

The API automatically checks merchant names against the SC Malaysia InvestorAlert database to detect potentially fraudulent entities.

## Tech Stack

- **Framework**: FastAPI 0.115+
- **Runtime**: Python 3.11+
- **AI Model**: Qwen VL Plus (Alibaba Cloud)
- **Deployment**: AWS App Runner
- **Cost**: ~$12-20/month

## Support

- GitHub: https://github.com/yujie0124/tng-shield-be
- FastAPI Docs: https://fastapi.tiangolo.com
- Qwen AI: https://dashscope.aliyun.com

---

**Ready to deploy?** Just run `deploy.bat` and enter your Qwen API key! 🚀
