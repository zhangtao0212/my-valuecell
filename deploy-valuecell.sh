#!/bin/bash

# ValueCell 服务器部署脚本

HOST="45.32.31.197"
USER="claude"
PASSWORD="Ppnn13%vultr"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" 1>&2; }

# 执行远程命令的函数
exec_remote() {
    local cmd="$1"
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$USER@$HOST" "$cmd"
}

# 检查连接
info "检查服务器连接..."
if exec_remote "echo '连接成功'"; then
    info "服务器连接成功"
else
    error "服务器连接失败"
    exit 1
fi

# 1. 更新系统
info "更新系统包..."
exec_remote "apt update && apt upgrade -y"

# 2. 安装基础工具
info "安装基础工具..."
exec_remote "apt install -y curl wget git build-essential nginx certbot python3-certbot-nginx"

# 3. 安装 Node.js
info "安装 Node.js..."
exec_remote "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs"

# 4. 安装 Python 3.12
info "安装 Python 3.12..."
exec_remote "apt install -y python3.12 python3.12-venv python3.12-dev"

# 5. 安装 uv (Python 包管理器)
info "安装 uv..."
exec_remote "curl -LsSf https://astral.sh/uv/install.sh | sh"

# 6. 安装 bun (前端包管理器)
info "安装 bun..."
exec_remote "curl -fsSL https://bun.sh/install | bash"

# 7. 更新 PATH
info "更新 PATH..."
exec_remote "echo 'export PATH=\"\$HOME/.local/bin:\$HOME/.bun/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"

# 8. 创建项目目录
info "创建项目目录..."
exec_remote "mkdir -p /opt/valuecell"

# 9. 克隆代码
info "克隆项目代码..."
exec_remote "cd /opt/valuecell && git clone https://github.com/zhangtao0212/my-valuecell.git . || true"

# 10. 更新代码
info "更新项目代码..."
exec_remote "cd /opt/valuecell && git pull origin main"

# 11. 配置环境变量
info "创建环境配置文件..."
exec_remote "cd /opt/valuecell && cp .env.example .env"

# 12. 安装前端依赖
info "安装前端依赖..."
exec_remote "cd /opt/valuecell/frontend && ~/.bun/bin/bun install"

# 13. 构建前端
info "构建前端应用..."
exec_remote "cd /opt/valuecell/frontend && ~/.bun/bin/bun run build"

# 14. 安装后端依赖
info "安装后端依赖..."
exec_remote "cd /opt/valuecell/python && ~/.local/bin/uv sync"

# 15. 配置 Nginx
info "配置 Nginx..."
exec_remote "cat > /etc/nginx/sites-available/invest.todd0212.com << 'EOF'
server {
    listen 80;
    server_name invest.todd0212.com;

    # 前端静态文件
    location / {
        root /opt/valuecell/frontend/build/client;
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF"

# 16. 启用 Nginx 站点
info "启用 Nginx 站点..."
exec_remote "ln -sf /etc/nginx/sites-available/invest.todd0212.com /etc/nginx/sites-enabled/ && nginx -t"

# 17. 安装 PM2
info "安装 PM2 进程管理器..."
exec_remote "npm install -g pm2"

# 18. 启动后端服务
info "启动后端服务..."
exec_remote "cd /opt/valuecell/python && export PATH=\"\$HOME/.local/bin:\$PATH\" && pm2 start --name valuecell-backend uv -- run scripts/launch.py"

# 19. 保存 PM2 配置
info "保存 PM2 配置..."
exec_remote "pm2 startup && pm2 save"

# 20. 重启 Nginx
info "重启 Nginx..."
exec_remote "systemctl restart nginx"

# 21. 检查服务状态
info "检查服务状态..."
exec_remote "pm2 status"
exec_remote "systemctl status nginx --no-pager"

info "🎉 ValueCell 部署完成！"
info "🌐 前端地址: http://invest.todd0212.com"
info "📊 服务状态: pm2 status"
info "📝 后端日志: pm2 logs valuecell-backend"
info "🔧 Nginx状态: systemctl status nginx"