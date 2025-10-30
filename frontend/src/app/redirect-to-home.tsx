import { Navigate } from "react-router";

export default function RedirectToHome() {
  // 检测当前域名，如果是 admin 子域名则重定向到 /admin
  if (window.location.hostname === 'admin.invest.todd0212.com') {
    return <Navigate to="/admin" replace />;
  }

  // 其他情况重定向到 /home
  return <Navigate to="/home" replace />;
}
