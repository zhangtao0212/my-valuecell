#!/usr/bin/expect -f

# ValueCell 服务器自动部署脚本

set timeout 60
set host "45.32.31.197"
set username "root"
set password "H6!dc7B,M}2om%a]"

# 连接服务器
spawn ssh $username@$host

expect {
    "*yes/no*" {
        send "yes\r"
        exp_continue
    }
    "*password:*" {
        send "$password\r"
        exp_continue
    }
    "*# " {
        # 成功登录，开始部署
        send "echo '🚀 开始部署 ValueCell 服务...'\r"

        # 1. 更新系统
        send "echo '📦 更新系统包...'\r"
        send "apt update && apt upgrade -y\r"

        # 等待更新完成
        expect "*# "

        # 2. 安装基础工具
        send "echo '🔧 安装基础工具...'\r"
        send "apt install -y curl wget git build-essential nginx certbot python3-certbot-nginx\r"

        expect "*# "

        # 3. 安装 Node.js
        send "echo '📥 安装 Node.js...'\r"
        send "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -\r"

        expect "*# "

        send "apt-get install -y nodejs\r"

        expect "*# "

        # 4. 检查 Node.js 安装
        send "echo '✅ Node.js 版本:'\r"
        send "node --version\r"
        send "npm --version\r"

        expect "*# "

        # 5. 安装 Python 3.12
        send "echo '🐍 安装 Python 3.12...'\r"
        send "apt install -y python3.12 python3.12-venv python3.12-dev\r"

        expect "*# "

        # 6. 安装 uv (Python 包管理器)
        send "echo '📦 安装 uv...'\r"
        send "curl -LsSf https://astral.sh/uv/install.sh | sh\r"

        expect "*# "

        # 7. 安装 bun (前端包管理器)
        send "echo '🍞 安装 bun...'\r"
        send "curl -fsSL https://bun.sh/install | bash\r"

        expect "*# "

        # 8. 更新 PATH
        send "echo '🔄 更新 PATH...'\r"
        send "export PATH=\"\$HOME/.local/bin:\$HOME/.bun/bin:\$PATH\"\r"

        expect "*# "

        # 9. 创建项目目录
        send "echo '📁 创建项目目录...'\r"
        send "mkdir -p /opt/valuecell\r"
        send "cd /opt/valuecell\r"

        expect "*# "

        # 10. 克隆代码
        send "echo '📥 克隆项目代码...'\r"
        send "git clone https://github.com/zhangtao0212/my-valuecell.git .\r"

        expect "*# "

        # 11. 配置环境变量
        send "echo '⚙️ 创建环境配置文件...'\r"
        send "cp .env.example .env\r"

        expect "*# "

        # 12. 安装前端依赖
        send "echo '📦 安装前端依赖...'\r"
        send "cd frontend && ~/.bun/bin/bun install\r"

        # 等待bun安装完成
        set timeout 300
        expect "*# "
        set timeout 60

        # 13. 构建前端
        send "echo '🔨 构建前端应用...'\r"
        send "~/.bun/bin/bun run build\r"

        expect "*# "

        # 14. 安装后端依赖
        send "echo '📦 安装后端依赖...'\r"
        send "cd /opt/valuecell/python && ~/.local/bin/uv sync\r"

        # 等待uv安装完成
        set timeout 300
        expect "*# "
        set timeout 60

        # 15. 配置 Nginx
        send "echo '🌐 配置 Nginx...'\r"
        send "cat > /etc/nginx/sites-available/invest.todd0212.com << 'EOF'\r"
        send "server {\r"
        send "    listen 80;\r"
        send "    server_name invest.todd0212.com;\r"
        send "\r"
        send "    # 前端静态文件\r"
        send "    location / {\r"
        send "        root /opt/valuecell/frontend/build/client;\r"
        send "        try_files \\$uri \\$uri/ /index.html;\r"
        send "    }\r"
        send "\r"
        send "    # 后端 API 代理\r"
        send "    location /api/ {\r"
        send "        proxy_pass http://localhost:8000;\r"
        send "        proxy_set_header Host \\$host;\r"
        send "        proxy_set_header X-Real-IP \\$remote_addr;\r"
        send "        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;\r"
        send "        proxy_set_header X-Forwarded-Proto \\$scheme;\r"
        send "    }\r"
        send "}\r"
        send "EOF\r"

        expect "*# "

        # 16. 启用 Nginx 站点
        send "ln -sf /etc/nginx/sites-available/invest.todd0212.com /etc/nginx/sites-enabled/\r"
        send "nginx -t\r"

        expect "*# "

        # 17. 安装 PM2
        send "echo '📊 安装 PM2 进程管理器...'\r"
        send "npm install -g pm2\r"

        expect "*# "

        # 18. 创建启动脚本
        send "echo '🚀 创建启动脚本...'\r"
        send "cat > /opt/valuecell/start-backend.sh << 'EOF'\r"
        send "#!/bin/bash\r"
        send "cd /opt/valuecell/python\r"
        send "export PATH=\"\$HOME/.local/bin:\$PATH\"\r"
        send "uv run scripts/launch.py\r"
        send "EOF\r"

        expect "*# "

        send "chmod +x /opt/valuecell/start-backend.sh\r"

        expect "*# "

        # 19. 启动后端服务
        send "echo '🚀 启动后端服务...'\r"
        send "cd /opt/valuecell/python\r"
        send "export PATH=\"\$HOME/.local/bin:\$PATH\"\r"
        send "pm2 start --name valuecell-backend uv -- run scripts/launch.py\r"

        expect "*# "

        # 20. 保存 PM2 配置
        send "pm2 startup\r"

        expect "*# "

        send "pm2 save\r"

        expect "*# "

        # 21. 重启 Nginx
        send "echo '🔄 重启 Nginx...'\r"
        send "systemctl restart nginx\r"

        expect "*# "

        # 22. 检查服务状态
        send "echo '✅ 部署完成！检查服务状态...'\r"
        send "pm2 status\r"

        expect "*# "

        send "systemctl status nginx --no-pager\r"

        expect "*# "

        # 23. 显示部署总结
        send "echo ''\r"
        send "echo '🎉 ValueCell 部署完成！'\r"
        send "echo '🌐 前端地址: http://invest.todd0212.com'\r"
        send "echo '📊 服务状态: pm2 status'\r"
        send "echo '📝 后端日志: pm2 logs valuecell-backend'\r"
        send "echo '🔧 Nginx状态: systemctl status nginx'\r"

        # 保持连接以便查看输出
        interact
    }
    timeout {
        send_user "连接超时\n"
        exit 1
    }
    eof {
        send_user "连接断开\n"
        exit 1
    }
}