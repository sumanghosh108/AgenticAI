import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Brain, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { useAuth } from '@/context/AuthContext';
import { authApi } from '@/api/client';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    if (code) {
      setLoading(true);
      authApi.googleAuth(code)
        .then(res => {
          if (res.success) {
            login(res.username || '');
            navigate('/dashboard');
          } else {
            setError(res.message || 'Google Auth failed');
          }
        })
        .catch(() => setError('Unable to reach server'))
        .finally(() => {
          setLoading(false);
          setSearchParams({});
        });
    }
  }, [searchParams, login, navigate, setSearchParams]);

  const handleGoogleLogin = async () => {
    setError('');
    try {
      const res = await authApi.getGoogleAuthUrl();
      if (res.success && res.url) {
        window.location.href = res.url;
      } else {
        setError(res.message || 'Google login unavailable');
      }
    } catch {
      setError('Unable to reach server');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await authApi.login(username, password);
      if (res.success) {
        login(res.username || username);
        navigate('/dashboard');
      } else {
        setError(res.message || 'Login failed');
      }
    } catch (err) {
      setError('Unable to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#201E25] px-4 font-['Montserrat',sans-serif]">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center justify-center gap-2 mb-10">
          <div className="w-14 h-14 bg-[#6C48C3] rounded-2xl flex items-center justify-center shadow-lg shadow-[#6C48C3]/30 mb-2">
            <Brain className="w-8 h-8 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-[#C530EA] to-[#11D5F7] text-transparent bg-clip-text mb-1">AgenticAI</h1>
            <p className="text-[11px] text-gray-400 uppercase tracking-[0.2em] font-medium">Decision Platform</p>
          </div>
        </div>

        {/* Form */}
        <div className="bg-[#071217] rounded-[10px] shadow-2xl border border-white/10 p-8 sm:p-10 relative overflow-hidden">
          {/* Subtle top glare effect */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
          
          <h2 className="text-2xl font-semibold mb-8 text-center text-white">Welcome back</h2>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-300">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 rounded text-sm border border-white/10 bg-white/5 text-white focus:ring-1 focus:ring-[#11D5F7] focus:border-[#11D5F7] outline-none transition-all placeholder-gray-500"
                placeholder="Enter your username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-gray-300">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 rounded text-sm border border-white/10 bg-white/5 text-white focus:ring-1 focus:ring-[#11D5F7] focus:border-[#11D5F7] outline-none transition-all pr-10 placeholder-gray-500"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button 
              type="submit" 
              loading={loading} 
              className="w-full py-3 mt-2 !bg-[#6C48C3] hover:!bg-[#8D65F0] !text-white !border-0 text-base font-medium rounded transition-all transform hover:scale-[1.02] active:scale-[0.98]"
              size="lg"
            >
              Sign In
            </Button>
            
            <div className="relative mt-8 mb-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-[#071217] text-gray-500">Or continue with</span>
              </div>
            </div>

            <Button
              type="button"
              variant="secondary"
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full py-3 flex items-center justify-center gap-3 !border-white/20 !text-white !bg-transparent hover:!bg-white/5 transition-all rounded text-base font-medium"
              size="lg"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-gray-400">
            Don't have an account?{' '}
            <Link to="/signup" className="text-[#11D5F7] hover:text-white transition-colors font-medium ml-1">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
