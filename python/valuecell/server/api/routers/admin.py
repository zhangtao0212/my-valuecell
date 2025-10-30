"""Admin configuration router for ValueCell."""

import os
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Ppnn13%invest"

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials."""
    if credentials.username != ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    if credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def create_admin_router():
    router = APIRouter(prefix="/admin", tags=["Admin"])

    CONFIG_DESCRIPTIONS = {
        # 应用基础配置
        "APP_NAME": "应用名称 | 用于标识应用在系统中的显示名称 | 可选 | 默认: ValueCell",
        "APP_VERSION": "应用版本 | 标识当前应用的版本号 | 可选 | 默认: 0.1.0",
        "APP_ENVIRONMENT": "运行环境 | 指定应用运行的环境，development为开发环境，production为生产环境 | 可选 | 可选值: development/production | 默认: production",
        "API_DEBUG": "API调试模式 | 启用API调试模式，会输出详细的调试信息 | 可选 | true/false | 默认: false",

        # API配置
        "API_ENABLED": "启用API | 控制是否启用API服务 | 必填 | true/false | 默认: true",
        "API_I18N_ENABLED": "启用国际化 | 控制是否启用多语言支持 | 可选 | true/false | 默认: true",
        "API_HOST": "API主机地址 | API服务绑定的主机地址，0.0.0.0表示监听所有网络接口 | 必填 | 默认: 0.0.0.0",
        "API_PORT": "API端口 | API服务监听的端口号 | 必填 | 默认: 8000",

        # 系统配置
        "LANG": "默认语言 | 系统默认显示语言，影响界面和消息的语言 | 可选 | 可选值: en-US/zh-CN/zh-TW/ja-JP/ko-KR | 默认: en-US",
        "TIMEZONE": "默认时区 | 系统默认时区设置，影响时间显示和计算 | 可选 | 可选值: America/New_York/America/Los_Angeles/Asia/Shanghai/Asia/Tokyo/Europe/London/Europe/Paris | 默认: America/New_York",
        "PYTHONIOENCODING": "Python编码 | Python输入输出编码设置 | 可选 | 默认: utf-8",

        # 代理配置
        "AGENT_DEBUG_MODE": "代理调试模式 | 启用代理调试模式，会输出代理的详细执行信息 | 可选 | true/false | 默认: false",

        # AI模型提供商API密钥
        "OPENROUTER_API_KEY": "OpenRouter API密钥 | 用于访问OpenRouter平台的AI模型服务，支持多种开源模型 | 可选 | 从 https://openrouter.ai/ 获取",
        "AZURE_OPENAI_API_KEY": "Azure OpenAI API密钥 | 用于访问微软Azure平台的OpenAI服务 | 可选 | 从 https://ai.azure.com/ 获取",
        "GOOGLE_API_KEY": "Google API密钥 | 用于访问Google的Gemini模型服务 | 可选 | 从 https://aistudio.google.com/ 获取",
        "SILICONFLOW_API_KEY": "硅基流动API密钥 | 用于访问硅基流动平台的AI模型服务 | 可选 | 从 https://siliconflow.cn 获取",
        "OPENAI_API_KEY": "OpenAI API密钥 | 用于直接访问OpenAI官方API服务 | 可选 | 从 https://platform.openai.com/api-keys 获取",

        # 研究代理配置
        "SEC_EMAIL": "SEC API请求邮箱 | 用于向美国证券交易委员会(SEC)API发送请求时的标识邮箱 | 可选 | 可设置为任何有效邮箱地址",

        # 第三方代理配置
        "FINNHUB_API_KEY": "Finnhub API密钥 | 用于获取金融数据，包括股票价格、新闻等，交易代理必需 | 必填 | 从 https://finnhub.io/register 获取免费API密钥",
        "XUEQIU_TOKEN": "雪球Token | 用于获取中国股市数据，当YFinance数据获取不稳定时使用 | 可选 | 从 https://xueqiu.com/ 获取",
    }

    def read_env_file():
        env_file = "/opt/valuecell/.env"
        config = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        return config

    def write_env_file(config):
        env_file = "/opt/valuecell/.env"
        lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
        updated_lines = []
        found_keys = set()
        for line in lines:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('#') and '=' in stripped_line:
                key = stripped_line.split('=', 1)[0].strip()
                if key in config:
                    updated_lines.append(f"{key}={config[key]}\n")
                    found_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        for key, value in config.items():
            if key not in found_keys:
                updated_lines.append(f"{key}={value}\n")
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)

    @router.get("/config")
    async def get_config(username: str = Depends(verify_admin)):
        config = read_env_file()
        config_with_descriptions = {}
        for key, value in config.items():
            config_with_descriptions[key] = {
                "value": value,
                "description": CONFIG_DESCRIPTIONS.get(key, "No description")
            }
        return {"config": config_with_descriptions, "descriptions": CONFIG_DESCRIPTIONS}

    @router.post("/config")
    async def update_config(updates: Dict[str, str], username: str = Depends(verify_admin)):
        current_config = read_env_file()
        for key in updates:
            if key not in CONFIG_DESCRIPTIONS:
                raise HTTPException(status_code=400, detail=f"Invalid key: {key}")
        current_config.update(updates)
        write_env_file(current_config)
        return {"message": "Updated", "updated_keys": list(updates.keys())}

    @router.get("/health")
    async def admin_health(username: str = Depends(verify_admin)):
        return {"status": "healthy", "service": "Admin API", "user": username}

    return router