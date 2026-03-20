import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Brain } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { authApi } from '@/api/client';

export function SignupPage() {
  const [form, setForm] = useState({ username: '', email: '', password: '', confirmPwd: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPwd) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.signup({
        username: form.username,
        email: form.email,
        password: form.password,
      });
      if (res.success) {
        navigate('/login');
      } else {
        setError(res.message || 'Signup failed');
      }
    } catch {
      setError('Unable to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const update = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 via-white to-indigo-50 dark:from-gray-950 dark:via-gray-900 dark:to-brand-950 px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 bg-brand-600 rounded-2xl flex items-center justify-center shadow-lg shadow-brand-500/25">
            <Brain className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold">AgenticAI</h1>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 p-8">
          <h2 className="text-xl font-semibold mb-6 text-center">Create your account</h2>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {(['username', 'email', 'password', 'confirmPwd'] as const).map((field) => (
              <div key={field}>
                <label className="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300 capitalize">
                  {field === 'confirmPwd' ? 'Confirm Password' : field}
                </label>
                <input
                  type={field.includes('assword') ? 'password' : field === 'email' ? 'email' : 'text'}
                  value={form[field]}
                  onChange={update(field)}
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition"
                  required
                />
              </div>
            ))}

            <Button type="submit" loading={loading} className="w-full" size="lg">
              Create Account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-600 hover:text-brand-700 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
