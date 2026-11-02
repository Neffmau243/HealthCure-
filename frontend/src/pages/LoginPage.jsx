import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, Loader2, HeartPulse, ClipboardList, Stethoscope, FileText } from 'lucide-react';
import { useAuth } from '../context/useAuth';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (enviando) return;
    setError(null);
    setEnviando(true);
    try {
      await login(email.trim(), password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err.response?.status === 401) {
        setError('El correo o la contraseña no coinciden. Revisa tus datos y vuelve a intentarlo.');
      } else if (!err.response) {
        setError('No pudimos conectar con el servidor. Comprueba tu conexión y vuelve a intentarlo.');
      } else {
        setError('No pudimos iniciar sesión en este momento. Vuelve a intentarlo en unos instantes.');
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="login-screen">
      {/* Contenedor principal con una altura óptima y uniforme */}
      <div className="login-layout">
        {/* Panel del Formulario Izquierdo con distribución equilibrada */}
        <div className="login-form-panel">
          <div className="login-brand"><HeartPulse className="w-8 h-8" aria-hidden="true" /><span>HealthCure</span></div>
          <div className="w-full mt-10">
            <h1 className="text-3xl font-semibold tracking-tight text-[#17324c]">Bienvenido a tu espacio de atención</h1>
            <p className="text-sm text-slate-600 leading-relaxed mt-3">Ingresa con tu cuenta para continuar con la atención de tus pacientes.</p>
          </div>

          <form
            onSubmit={handleLogin}
            className="w-full flex flex-col gap-5 mt-8"
          >
            {/* Etiquetas reales (ocultas visualmente): el placeholder solo no
                da nombre accesible al campo, así que un lector de pantalla
                anunciaba "cuadro de edición, en blanco". */}
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 mb-2">
                Correo electrónico
              </label>
              <div className="relative flex items-center"><Mail className="absolute left-3.5 text-slate-500 w-[18px] h-[18px]" aria-hidden="true" /><input
                id="login-email"
                type="email"
                required
                autoComplete="username"
                aria-describedby={error ? 'login-error' : undefined}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="correo@healthcure.com"
                className="w-full py-3.5 pr-4 pl-11 rounded-md border border-slate-300 bg-white text-sm font-lexend outline-none text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#17324c] focus:border-blue-900 transition-colors"
              /></div>
            </div>

            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-2">
                Contraseña
              </label>
              <div className="relative flex items-center"><Lock className="absolute left-3.5 text-slate-500 w-[18px] h-[18px]" aria-hidden="true" /><input
                id="login-password"
                type="password"
                required
                autoComplete="current-password"
                aria-describedby={error ? 'login-error' : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Ingresa tu contraseña"
                className="w-full py-3.5 pr-4 pl-11 rounded-md border border-slate-300 bg-white text-sm font-lexend outline-none text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#17324c] focus:border-blue-900 transition-colors"
              /></div>
            </div>

            {error && (
              <p id="login-error" className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2.5" role="alert">
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

            {/* text-slate-500 en vez de slate-400: el gris anterior daba
                2.63:1 de contraste (WCAG AA exige 4.5:1 para texto normal). */}
            <details className="text-xs text-slate-600 leading-relaxed"><summary className="cursor-pointer py-2">Acceso para demostración</summary><p className="mt-2">admin@healthcure.com / admin123<br />dr.garcia@healthcure.com / doctor123</p></details>
          </form>

          <p className="text-xs text-slate-500 mt-8 leading-relaxed">Herramientas para el personal de salud, al servicio de cada paciente.</p>
        </div>

        {/* Panel Derecho: Logo derecho para pantallas grandes */}
        <section className="login-care-panel" aria-labelledby="atencion-conectada">
          <HeartPulse className="w-12 h-12" aria-hidden="true" />
          <h2 id="atencion-conectada">Una atención conectada.<br />Una historia que continúa.</h2>
          <p>Información clínica para acompañar cada etapa del cuidado.</p>
          <div className="login-care-steps">
            <div><ClipboardList aria-hidden="true" /><span>Conoce al paciente<small>Identificación, antecedentes y datos de la visita.</small></span></div>
            <div><Stethoscope aria-hidden="true" /><span>Acompaña la valoración<small>Mediciones, señales de alarma y evaluación cardiovascular.</small></span></div>
            <div><FileText aria-hidden="true" /><span>Da continuidad al cuidado<small>Atenciones, historia clínica y FUA.</small></span></div>
          </div>
        </section>
      </div>
    </div>
  );
}
