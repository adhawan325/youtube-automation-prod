# YouTube Automation System - Permanent Deployment Guide

## 🚀 Quick Deployment

### Option 1: One-Click Deployment (Recommended)
```bash
git clone https://github.com/adhawan325/youtube-automation-prod.git
cd youtube-automation-prod
./deploy.sh
```

### Option 2: Manual Docker Deployment
```bash
# 1. Clone the repository
git clone https://github.com/adhawan325/youtube-automation-prod.git
cd youtube-automation-prod

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Deploy with Docker
docker-compose up -d
```

## 🔧 Server Requirements

### Minimum Requirements
- **CPU**: 1 vCPU
- **RAM**: 2GB
- **Storage**: 10GB SSD
- **OS**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **Network**: Stable internet connection

### Recommended for Production
- **CPU**: 2+ vCPUs
- **RAM**: 4GB+
- **Storage**: 50GB+ SSD
- **OS**: Ubuntu 22.04 LTS
- **Network**: High-speed internet (for video uploads)

## 🌐 Cloud Deployment Options

### 1. DigitalOcean Droplet
```bash
# Create $10/month droplet (2GB RAM, 1 vCPU)
# SSH into droplet and run:
curl -fsSL https://raw.githubusercontent.com/adhawan325/youtube-automation-prod/main/deploy.sh | bash
```

### 2. AWS EC2
```bash
# Launch t3.small instance (2GB RAM, 2 vCPUs)
# Use Ubuntu 22.04 AMI
# Configure security group: Port 5000 open
# SSH and run deployment script
```

### 3. Google Cloud Platform
```bash
# Create e2-small instance (2GB RAM, 2 vCPUs)
# Use Ubuntu 22.04 image
# Enable HTTP/HTTPS traffic
# SSH and run deployment script
```

### 4. Linode
```bash
# Create Nanode 2GB plan
# Use Ubuntu 22.04 image
# SSH and run deployment script
```

## 🔐 Environment Configuration

### Required API Keys
Create `.env` file with:
```bash
# News API
NEWSAPI_AI_KEY=your_newsapi_key

# OpenAI API
OPENAI_API_KEY=your_openai_key

# Media APIs
PEXELS_API_KEY=your_pexels_key

# YouTube OAuth
YOUTUBE_CLIENT_ID=your_google_client_id
YOUTUBE_CLIENT_SECRET=your_google_client_secret

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_random_secret_key
```

## 🎯 Post-Deployment Setup

### 1. Access Dashboard
- **URL**: `http://your-server-ip:5000`
- **Status API**: `http://your-server-ip:5000/api/automation/status`

### 2. Start Automation
1. Visit dashboard
2. Click "Generate Video Now" to test
3. Click "Start Scheduler" for 24/7 automation

### 3. Complete YouTube OAuth
1. Visit Google Cloud Console
2. Configure OAuth consent screen
3. Add authorized redirect URIs:
   - `http://your-server-ip:5000/auth/callback`
   - `http://your-server-ip:5000/oauth2callback`

## 🔧 Management Commands

### Docker Management
```bash
# View logs
docker-compose logs -f

# Stop system
docker-compose down

# Restart system
docker-compose restart

# Update system
git pull
docker-compose up -d --build

# View running containers
docker-compose ps

# Access container shell
docker-compose exec youtube-automation bash
```

### System Monitoring
```bash
# Check system status
curl http://localhost:5000/api/automation/status

# Monitor video generation
tail -f logs/app.log

# Check disk usage
df -h

# Monitor system resources
htop
```

## 🛡️ Security Configuration

### 1. Firewall Setup
```bash
# Ubuntu/Debian
sudo ufw allow 22    # SSH
sudo ufw allow 5000  # Application
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 2. SSL/HTTPS Setup (Optional)
```bash
# Install Nginx
sudo apt install nginx

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/youtube-automation

# Add SSL certificate (Let's Encrypt)
sudo certbot --nginx -d yourdomain.com
```

### 3. Domain Configuration
1. Point your domain to server IP
2. Update OAuth redirect URIs to use domain
3. Configure SSL certificate
4. Update environment variables

## 📊 Monitoring & Maintenance

### Health Checks
- **Application**: `http://localhost:5000/api/automation/status`
- **Docker**: `docker-compose ps`
- **Logs**: `docker-compose logs`

### Backup Strategy
```bash
# Backup database and media
tar -czf backup-$(date +%Y%m%d).tar.gz database/ media/

# Automated daily backup
echo "0 2 * * * cd /path/to/youtube-automation-prod && tar -czf backup-\$(date +\%Y\%m\%d).tar.gz database/ media/" | crontab -
```

### Updates
```bash
# Update system
cd youtube-automation-prod
git pull
docker-compose up -d --build
```

## 🚨 Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
docker-compose logs

# Check environment
cat .env

# Rebuild container
docker-compose down
docker-compose up -d --build
```

#### Video Generation Fails
```bash
# Check API keys
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check disk space
df -h

# Check FFmpeg
docker-compose exec youtube-automation ffmpeg -version
```

#### YouTube Upload Issues
1. Verify OAuth configuration
2. Check redirect URIs
3. Ensure proper scopes enabled
4. Test authentication flow

### Performance Optimization
```bash
# Increase video generation frequency
# Edit docker-compose.yml environment:
GENERATION_INTERVAL=30  # minutes

# Scale with multiple containers
docker-compose up -d --scale youtube-automation=3
```

## 💰 Cost Optimization

### Monthly Costs
- **Server**: $10-20/month (DigitalOcean/Linode)
- **APIs**: $160/month (NewsAPI + OpenAI + Pexels)
- **Total**: ~$170-180/month

### Cost Reduction Tips
1. Use smaller server initially ($5/month)
2. Optimize API usage patterns
3. Implement caching for repeated requests
4. Use free tiers where available

## 📈 Scaling Options

### Horizontal Scaling
```bash
# Multiple containers
docker-compose up -d --scale youtube-automation=3

# Load balancer
# Add nginx load balancer configuration
```

### Vertical Scaling
- Upgrade server resources
- Increase generation frequency
- Add more API keys for higher limits

## 🎯 Production Checklist

- [ ] Server provisioned and secured
- [ ] Domain configured (optional)
- [ ] SSL certificate installed (optional)
- [ ] Environment variables configured
- [ ] Application deployed and running
- [ ] Health checks passing
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] YouTube OAuth completed
- [ ] First video generated successfully
- [ ] Scheduler started for automation

## 📞 Support

### Resources
- **GitHub**: https://github.com/adhawan325/youtube-automation-prod
- **Documentation**: This README
- **Logs**: `docker-compose logs -f`

### Emergency Commands
```bash
# Stop everything
docker-compose down

# Emergency restart
docker-compose restart

# Reset database
rm -rf database/* && docker-compose restart
```

---

**🎉 Your YouTube automation system is now ready for 24/7 operation!**

