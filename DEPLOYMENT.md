# 🚀 CanillitaBot Automatic Deployment Setup

This guide shows how to set up automatic deployment to your DigitalOcean server when you push to the main branch.

## 📋 Setup Instructions

### 1. Add SSH Private Key to GitHub Secrets

1. Go to your GitHub repository: `https://github.com/trueshizus/botonar`
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `SSH_PRIVATE_KEY`
5. Value: Copy the entire content of your SSH private key (including `-----BEGIN` and `-----END` lines)

**Your SSH private key is located at:** `~/.ssh/digital_ocean`

To copy it:
```bash
cat ~/.ssh/digital_ocean | pbcopy  # Copies to clipboard on macOS
```

### 2. Workflow Configuration

The GitHub Actions workflow (`.github/workflows/deploy.yml`) is already configured to:

- ✅ Trigger on pushes to `main` branch
- ✅ Connect to your server via SSH
- ✅ Pull latest code changes
- ✅ Rebuild Docker containers
- ✅ Restart the bot
- ✅ Verify deployment health

### 3. Server Prerequisites

Your server is already configured correctly:
- ✅ SSH access with key authentication
- ✅ Git repository cloned at `/root/canillitabot`
- ✅ Docker and Docker Compose installed
- ✅ Bot currently running successfully

## 🔄 Deployment Process

When you push to main, the workflow will:

1. **Pull Changes**: `git reset --hard origin/main`
2. **Rebuild**: `docker compose build --no-cache`
3. **Restart**: `docker compose down && docker compose up -d`
4. **Verify**: Check container health and logs

## 🧪 Testing the Deployment

After setting up the SSH key secret:

1. Make a small change to any file
2. Commit and push to main:
   ```bash
   git add .
   git commit -m "Test automatic deployment"
   git push origin main
   ```
3. Go to **Actions** tab in GitHub to watch the deployment
4. Check your server: `ssh bot 'cd canillitabot && docker compose ps'`

## 📊 Monitoring Deployments

- **GitHub Actions**: Monitor deployment logs in the Actions tab
- **Server Logs**: `ssh bot 'cd canillitabot && docker compose logs -f canillitabot'`
- **Health Check**: `ssh bot 'cd canillitabot && docker compose ps'`

## 🔒 Security Notes

- SSH private key is stored securely in GitHub Secrets
- Deployment only triggers from the main branch
- Server access is limited to your SSH key
- No credentials are exposed in logs

## 🛠️ Manual Deployment (Backup)

If automatic deployment fails, you can still deploy manually:

```bash
ssh bot
cd canillitabot
git pull origin main
docker compose down
docker compose up -d --build
```

## 🚨 Troubleshooting

**Common Issues:**
- **SSH Connection Failed**: Verify SSH_PRIVATE_KEY secret is set correctly
- **Docker Build Failed**: Check Dockerfile and requirements.txt
- **Container Won't Start**: Check logs with `docker compose logs canillitabot`
- **Permission Issues**: Ensure SSH key has proper permissions on server

**Getting Help:**
- Check GitHub Actions logs for detailed error messages
- Monitor server logs: `ssh bot 'cd canillitabot && tail -f logs/canillitabot.log'`
- Verify container health: `ssh bot 'cd canillitabot && docker compose ps'`
