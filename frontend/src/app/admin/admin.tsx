import React, { useState } from 'react';
import { useNavigate } from 'react-router';

interface ConfigParam {
  name: string;
  value: string;
  description: string;
  isRequired: boolean;
  originalValue: string;
  isEditing: boolean;
}

// 支持的语言选项
const LANGUAGES = [
  { value: 'en-US', label: 'English (US)' },
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'ja-JP', label: '日本語' },
  { value: 'ko-KR', label: '한국어' },
];

// 支持的时区选项
const TIMEZONES = [
  { value: 'America/New_York', label: '美国东部时间 (EST)' },
  { value: 'America/Los_Angeles', label: '美国太平洋时间 (PST)' },
  { value: 'Asia/Shanghai', label: '中国标准时间 (CST)' },
  { value: 'Asia/Tokyo', label: '日本标准时间 (JST)' },
  { value: 'Europe/London', label: '格林威治标准时间 (GMT)' },
  { value: 'Europe/Paris', label: '中欧时间 (CET)' },
];

// 布尔值选项
const BOOLEAN_OPTIONS = [
  { value: 'true', label: '是 (true)' },
  { value: 'false', label: '否 (false)' },
];

// 环境选项
const ENVIRONMENT_OPTIONS = [
  { value: 'development', label: '开发环境 (development)' },
  { value: 'production', label: '生产环境 (production)' },
];

export default function AdminPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [config, setConfig] = useState<ConfigParam[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('/api/v1/admin/config', {
        headers: {
          'Authorization': 'Basic ' + btoa(username + ':' + password)
        }
      });

      if (response.ok) {
        const data = await response.json();
        const configArray: ConfigParam[] = Object.entries(data.config).map(([name, info]: [string, any]) => {
          const isRequired = info.description.includes('必填');
          const isEmptyValue = !info.value || info.value === '' || info.value === 'not_set';
          const shouldShowEmpty = !isRequired && isEmptyValue;

          return {
            name,
            value: shouldShowEmpty ? '' : info.value,
            description: info.description,
            isRequired,
            originalValue: info.value,
            isEditing: false
          };
        });
        setConfig(configArray);
        setIsAuthenticated(true);
        setMessage('');
      } else {
        setMessage('登录失败，请检查用户名和密码');
      }
    } catch (error) {
      setMessage('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);

    try {
      // 准备发送的数据，过滤掉空值的可选参数
      const dataToSend = config.reduce((acc, param) => {
        // 对于可选参数，如果值为空则不发送
        if (!param.isRequired && (!param.value || param.value.trim() === '')) {
          return acc;
        }
        acc[param.name] = param.value;
        return acc;
      }, {} as Record<string, string>);

      const response = await fetch('/api/v1/admin/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Basic ' + btoa(username + ':' + password)
        },
        body: JSON.stringify(dataToSend)
      });

      if (response.ok) {
        setMessage('配置保存成功');
        // 更新原始值
        const newConfig = [...config];
        newConfig.forEach(param => {
          param.originalValue = param.value;
          param.isEditing = false;
        });
        setConfig(newConfig);

        // 显示弹框提示
        setTimeout(() => {
          alert('保存成功！配置已更新。');
        }, 100);
      } else {
        setMessage('保存失败');
      }
    } catch (error) {
      setMessage('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setUsername('');
    setPassword('');
    setConfig([]);
    setMessage('');
  };

  const handleStartEditing = (index: number) => {
    const newConfig = [...config];
    newConfig[index].isEditing = true;
    setConfig(newConfig);
  };

  const handleInputChange = (index: number, value: string) => {
    const newConfig = [...config];
    newConfig[index].value = value;
    setConfig(newConfig);
  };

  const handleCancelEditing = (index: number) => {
    const newConfig = [...config];
    newConfig[index].value = newConfig[index].originalValue;
    newConfig[index].isEditing = false;
    setConfig(newConfig);
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-4">
        <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-md">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 text-center">
              管理员登录
            </h2>
            <p className="mt-2 text-sm text-gray-600 text-center">
              请输入管理员账号和密码
            </p>
          </div>
          <form className="mt-8 space-y-6" onSubmit={handleLogin}>
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                用户名
              </label>
              <input
                id="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 placeholder-gray-400"
                placeholder="输入用户名"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                密码
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 placeholder-gray-400"
                placeholder="输入密码"
              />
            </div>
            {message && (
              <div className="text-red-600 text-sm">{message}</div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 overflow-auto">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h1 className="text-2xl font-bold text-gray-900">系统配置管理</h1>
              <button
                onClick={handleLogout}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                退出登录
              </button>
            </div>
          </div>

          <div className="p-6">
            {message && (
              <div className={`mb-4 p-3 rounded-md ${
                message.includes('成功')
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-red-50 text-red-700 border border-red-200'
              }`}>
                {message}
              </div>
            )}

            <div className="space-y-6">
              {config.map((param, index) => {
                const isLanguage = param.name === 'LANG';
                const isTimezone = param.name === 'TIMEZONE';
                const isBoolean = param.name === 'API_DEBUG' || param.name === 'API_ENABLED' || param.name === 'API_I18N_ENABLED' || param.name === 'AGENT_DEBUG_MODE';
                const isEnvironment = param.name === 'APP_ENVIRONMENT';
                const isReadOnly = !param.isEditing && param.value !== '' && param.value === param.originalValue;

                return (
                  <div key={param.name} className="border border-gray-200 rounded-lg p-4">
                    <div className="mb-2">
                      <div className="flex justify-between items-start mb-2">
                        <label className="block text-sm font-medium text-gray-700">
                          {param.name}
                          {param.isRequired && (
                            <span className="ml-1 text-red-500">*</span>
                          )}
                        </label>
                        {param.isRequired && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            必填
                          </span>
                        )}
                      </div>

                      <p className="text-sm text-gray-600 mb-3 leading-relaxed">
                        {param.description}
                      </p>

                      {/* 语言选择器 */}
                      {isLanguage && (
                        <select
                          value={param.value}
                          onChange={(e) => handleInputChange(index, e.target.value)}
                          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">请选择语言</option>
                          {LANGUAGES.map((lang) => (
                            <option key={lang.value} value={lang.value}>
                              {lang.label}
                            </option>
                          ))}
                        </select>
                      )}

                      {/* 时区选择器 */}
                      {isTimezone && (
                        <select
                          value={param.value}
                          onChange={(e) => handleInputChange(index, e.target.value)}
                          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">请选择时区</option>
                          {TIMEZONES.map((tz) => (
                            <option key={tz.value} value={tz.value}>
                              {tz.label}
                            </option>
                          ))}
                        </select>
                      )}

                      {/* 布尔值选择器 */}
                      {isBoolean && (
                        <select
                          value={param.value}
                          onChange={(e) => handleInputChange(index, e.target.value)}
                          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">请选择</option>
                          {BOOLEAN_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      )}

                      {/* 环境选择器 */}
                      {isEnvironment && (
                        <select
                          value={param.value}
                          onChange={(e) => handleInputChange(index, e.target.value)}
                          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">请选择环境</option>
                          {ENVIRONMENT_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      )}

                      {/* 普通文本输入框 */}
                      {!isLanguage && !isTimezone && !isBoolean && !isEnvironment && (
                        <div className="flex space-x-2">
                          <input
                            type="text"
                            value={param.value}
                            onChange={(e) => handleInputChange(index, e.target.value)}
                            onFocus={() => handleStartEditing(index)}
                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
                              isReadOnly ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : 'border-gray-300'
                            }`}
                            placeholder={param.isRequired ? '请输入值' : '可选，可为空'}
                            readOnly={isReadOnly}
                          />
                          {isReadOnly && (
                            <button
                              type="button"
                              onClick={() => handleStartEditing(index)}
                              className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            >
                              编辑
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => navigate('/')}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                返回首页
              </button>
              <button
                onClick={handleSave}
                disabled={loading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? '保存中...' : '保存配置'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}