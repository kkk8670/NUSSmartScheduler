import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import "./agent.css";

const API_BASE = "http://localhost:8000";
const ENDPOINTS = {
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
};

async function http(path, { method = "GET", body, token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `${res.status} ${res.statusText}`;
    throw new Error(msg);
  }
  return data;
}

export default function AuthPage() {
  const [tab, setTab] = useState("login");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [params] = useSearchParams();
  const navigate = useNavigate();

  // 登录表单
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // 注册表单
  const [name, setName] = useState("");
  const [rEmail, setREmail] = useState("");
  const [rPassword, setRPassword] = useState("");
  const [rConfirm, setRConfirm] = useState("");

  const redirectTo = params.get("redirect") || "/agent";

  function saveToken(tok) {
    if (!tok) return;
    localStorage.setItem("auth.token", tok);
  }

  const PREFER_JSON = false; // 如需测试 JSON 登录，改为 true

  async function onLogin(e) {
    e.preventDefault();
    setErr(""); setOk(""); setLoading(true);

    try {
      if (PREFER_JSON) {
        const data = await http(ENDPOINTS.LOGIN, {
          method: "POST",
          body: { email: email.trim(), password },
        });
        const token = data?.access_token || data?.token;
        if (!token) throw new Error("No access token returned by server");
        saveToken(token);
        setOk("Login success");
        navigate(redirectTo, { replace: true }); // ← 这里跳转
        return;
      }

      // 表单版（适配 OAuth2PasswordRequestForm）
      const form = new URLSearchParams();
      form.set("username", email.trim());
      form.set("password", password);

      const res = await fetch(`${API_BASE}${ENDPOINTS.LOGIN}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString(),
      });

      let data = {}; try { data = await res.json(); } catch {}
      if (!res.ok) {
        const msg = data?.detail || data?.message || `${res.status}`;
        if (res.status === 401) throw new Error("Invalid credentials");
        if (res.status === 422) throw new Error("Invalid form fields (username/password)");
        throw new Error(msg);
      }

      const token = data?.access_token || data?.token;
      if (!token) throw new Error("No access token returned by server");
      saveToken(token);
      setOk("Login success");
      navigate(redirectTo, { replace: true }); // ← 这里跳转
    } catch (err) {
      setErr(err?.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onRegister(e) {
    e.preventDefault();
    setErr(""); setOk("");
    if (rPassword !== rConfirm) {
      setErr("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const payload = { name: name || undefined, email: rEmail, password: rPassword };
      const data = await http(ENDPOINTS.REGISTER, { method: "POST", body: payload });

      const token = data?.access_token || data?.token;
      if (token) {
        saveToken(token);
        setOk("Register success · Signed in");
        navigate(redirectTo, { replace: true }); // ← 这里跳转
      } else {
        setOk("Register success · Please login");
        setTab("login");
        setEmail(rEmail);
      }
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
      <div className="am2-root">
        <header className="am2-header">
          <div className="am2-header__inner">
            <div className="am2-brand">
              <div className="am2-brand__icon">🔐</div>
              <div>
                <h1 className="am2-brand__title">Account</h1>
                <div className="am2-brand__subtitle">Login or create your account</div>
              </div>
            </div>
            <button className="am2-btn" onClick={() => window.history.back()}>⬅ Back</button>
          </div>
        </header>

        <main className="am2-main">
          <section className="am2-column">
            <div className="am2-card">
              <div className="am2-card__head">
                <div className="am2-row between center">
                  <h2 className="am2-card__title">{tab === "login" ? "Login" : "Register"}</h2>
                  <div className="am2-row gap-2">
                    <button
                        className={`am2-btn ${tab === "login" ? "am2-btn--primary" : ""}`}
                        onClick={() => setTab("login")}
                    >Login</button>
                    <button
                        className={`am2-btn ${tab === "register" ? "am2-btn--primary" : ""}`}
                        onClick={() => setTab("register")}
                    >Register</button>
                  </div>
                </div>
              </div>

              {err && <div className="am2-alert am2-alert--danger" style={{marginBottom:"0.75rem"}}>{err}</div>}
              {ok &&  <div className="am2-alert am2-alert--success" style={{marginBottom:"0.75rem"}}>{ok}</div>}

              {tab === "login" ? (
                  <form className="am2-form" onSubmit={onLogin}>
                    <label className="am2-label">Email</label>
                    <input
                        className="am2-input"
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                    />

                    <label className="am2-label am2-mt-2">Password</label>
                    <input
                        className="am2-input"
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                    />

                    <div className="am2-row between center am2-mt-2">
                      <div className="am2-hint">Press Enter to sign in</div>
                      <button className="am2-btn am2-btn--primary" disabled={loading}>
                        {loading ? "Signing in..." : "Sign in"}
                      </button>
                    </div>
                  </form>
              ) : (
                  <form className="am2-form" onSubmit={onRegister}>
                    <label className="am2-label">Name (optional)</label>
                    <input
                        className="am2-input"
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your name"
                    />

                    <label className="am2-label am2-mt-2">Email</label>
                    <input
                        className="am2-input"
                        type="email"
                        required
                        value={rEmail}
                        onChange={(e) => setREmail(e.target.value)}
                        placeholder="you@example.com"
                    />

                    <label className="am2-label am2-mt-2">Password</label>
                    <input
                        className="am2-input"
                        type="password"
                        required
                        minLength={6}
                        value={rPassword}
                        onChange={(e) => setRPassword(e.target.value)}
                        placeholder="At least 6 characters"
                    />

                    <label className="am2-label am2-mt-2">Confirm Password</label>
                    <input
                        className="am2-input"
                        type="password"
                        required
                        value={rConfirm}
                        onChange={(e) => setRConfirm(e.target.value)}
                        placeholder="Re-enter password"
                    />

                    <div className="am2-row between center am2-mt-2">
                      <div className="am2-hint">You can login right after registering</div>
                      <button className="am2-btn am2-btn--primary" disabled={loading}>
                        {loading ? "Creating..." : "Create account"}
                      </button>
                    </div>
                  </form>
              )}
            </div>

            {/* 已移除“Token quick check”，避免对 /users/me 的依赖 */}
          </section>
        </main>
      </div>
  );
}
