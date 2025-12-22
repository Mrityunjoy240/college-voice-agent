# Railway Deployment Guide

This guide explains how to deploy the College Voice Agent application to Railway with proper security practices.

## Prerequisites

1. Railway account (https://railway.app/)
2. GitHub account
3. Production API keys for:
   - Groq (https://console.groq.com/)
   - Speechmatics (https://speechmatics.com/)
   - MURF.ai (https://murf.ai/)

## Deployment Steps

### 1. Prepare Repository

1. Create a new GitHub repository
2. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Railway deployment"
   git branch -M main
   git remote add origin https://github.com/yourusername/college-voice-agent.git
   git push -u origin main
   ```

### 2. Deploy to Railway

1. Go to https://railway.app/ and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect the Docker configuration

### 3. Configure Environment Variables

In Railway project settings, add these environment variables:

```
GROQ_API_KEY=your_actual_groq_api_key
SPEECHMATICS_API_KEY=your_actual_speechmatics_api_key
MURF_API_KEY=your_actual_murf_api_key
MURF_VOICE_ID=en-US-JennyNeural
```

### 4. Update CORS Configuration (Optional)

If you're deploying the frontend separately, update the CORS configuration in `backend/app/config.py`:

```python
def cors_origins(self) -> List[str]:
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://your-frontend-domain.vercel.app",  # Add your frontend domain
        "https://your-railway-app.up.railway.app"   # Add your Railway domain
    ]
```

### 5. Deploy Frontend (Alternative Approach)

Since Railway doesn't serve static files as efficiently as Vercel/Netlify, you might want to deploy the frontend separately:

1. Build the frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Deploy to Vercel/Netlify with the following environment variable:
   ```
   VITE_API_URL=https://your-backend-service.up.railway.app
   ```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use Railway's environment variables** for all sensitive credentials
3. **Regularly rotate API keys** for enhanced security
4. **Monitor Railway logs** for any suspicious activity

## Troubleshooting

### Common Issues

1. **Build Failures**: Ensure all dependencies are listed in requirements.txt
2. **Runtime Errors**: Check Railway logs for missing environment variables
3. **CORS Issues**: Verify CORS origins include your frontend domain
4. **API Connection Issues**: Confirm API keys are correctly set in Railway environment variables

### Checking Logs

1. Go to your Railway project
2. Select the service (backend)
3. Click on "Logs" tab to view real-time logs

## Scaling

Railway automatically scales your application based on demand. For high-traffic scenarios:

1. Upgrade to a paid Railway plan
2. Consider implementing caching mechanisms
3. Monitor resource usage in Railway dashboard

Your application will be accessible at `https://your-project-name.up.railway.app`