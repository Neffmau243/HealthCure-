import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, Loader2 } from 'lucide-react';
import logoImage from '../assets/logo.png';
import { useAuth } from '../context/useAuth';
import { mensajeError } from '../services/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(email.trim(), password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(mensajeError(err, 'No se pudo iniciar sesión'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-gradient-to-b from-sky-400 via-sky-200 to-sky-100 p-4 font-lexend">
      {/* Contenedor principal con una altura óptima y uniforme */}
      <div className="flex w-full max-w-[460px] lg:max-w-[1150px] lg:h-[580px] bg-[#fcf6f4] rounded-xl shadow-2xl overflow-hidden flex-col lg:flex-row">
        {/* Panel del Formulario Izquierdo con distribución equilibrada */}
        <div className="w-full lg:flex-1 bg-[#fcf6f4] flex flex-col justify-between items-center p-8 lg:p-12">
          <div className="text-center w-full mt-2">
            <img
              src={logoImage}
              alt="Logo"
              className="w-[280px] lg:w-[310px] max-w-full h-auto mb-3 mx-auto object-contain"
            />
            <p className="text-[13px] text-slate-500 font-light">
              Ingresa tus credenciales para iniciar sesión
            </p>
          </div>

          <form
            onSubmit={handleLogin}
            className="w-full max-w-[340px] flex flex-col gap-5 my-6"
          >
            <div className="relative flex items-center">
              <Mail className="absolute left-3.5 text-slate-500 w-[18px] h-[18px]" />
              <input
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="correo@healthcure.com"
                className="w-full py-3.5 pr-4 pl-11 rounded-md border border-slate-300 bg-white text-sm font-lexend outline-none text-slate-900 focus:border-blue-900 transition-colors"
              />
            </div>

            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 text-slate-500 w-[18px] h-[18px]" />
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Ingresa tu contraseña"
                className="w-full py-3.5 pr-4 pl-11 rounded-md border border-slate-300 bg-white text-sm font-lexend outline-none text-slate-900 focus:border-blue-900 transition-colors"
              />
            </div>

            {error && (
              <p className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2.5" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={enviando}
              className="mt-2 py-3.5 bg-[#17324c] text-white rounded-md text-[15px] font-semibold font-lexend cursor-pointer hover:bg-[#0f2235] transition-colors shadow-md disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {enviando && <Loader2 className="w-4 h-4 animate-spin" />}
              {enviando ? 'Ingresando...' : 'Iniciar Sesión'}
            </button>

            <p className="text-[11px] text-slate-400 text-center leading-relaxed">
              Cuentas de prueba: <br />
              admin@healthcure.com / admin123 · dr.garcia@healthcure.com / doctor123
            </p>
          </form>

          <div className="mb-2"></div>
        </div>

        {/* Panel Derecho: Logo derecho para pantallas grandes */}
        <div className="flex-1 bg-[#56ccf2] hidden lg:flex justify-center items-center p-12">
          <img
            src={logoImage}
            alt="Logo Grande"
            className="w-[520px] lg:w-[580px] h-auto object-contain drop-shadow-xl"
          />
        </div>
      </div>
    </div>
  );
}
