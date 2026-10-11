import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AlignLeft, Bell, ChevronDown, LogOut, Clock } from 'lucide-react';
import { useAuth } from '../../context/useAuth';
import { etiquetaRol } from '../../constants/roles';

export default function Topbar({ toggleSidebar }) {
  // Un solo estado: 'notificaciones' | 'usuario' | null. Abrir uno cierra el otro.
  const [menuAbierto, setMenuAbierto] = useState(null);
  const [currentTime, setCurrentTime] = useState('');
  const refNotificaciones = useRef(null);
  const refUsuario = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Reloj en tiempo real para un toque profesional
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    };
    updateClock();
    const timer = setInterval(updateClock, 60000);
    return () => clearInterval(timer);
  }, []);

  // Un dropdown abierto se cierra con clic fuera y con Escape.
  // Antes no se cerraba de ninguna de las dos formas: quedaba tapando la
  // pantalla hasta volver a pulsar el botón.
  useEffect(() => {
    if (!menuAbierto) return undefined;
    const contenedor = menuAbierto === 'notificaciones' ? refNotificaciones : refUsuario;

    const alClicFuera = (evento) => {
      if (contenedor.current && !contenedor.current.contains(evento.target)) {
        setMenuAbierto(null);
      }
    };
    const alTeclear = (evento) => {
      if (evento.key === 'Escape') setMenuAbierto(null);
    };

    document.addEventListener('mousedown', alClicFuera);
    document.addEventListener('keydown', alTeclear);
    return () => {
      document.removeEventListener('mousedown', alClicFuera);
      document.removeEventListener('keydown', alTeclear);
    };
  }, [menuAbierto]);

  const pageTitles = {
    '/dashboard': 'Panel Principal',
    '/dashboard/pacientes': 'Gestión de Pacientes',
    '/dashboard/triaje': 'Estación de Triaje',
    '/dashboard/historiales': 'Historias Clínicas',
    '/dashboard/consultorio': 'Consultorio Médico',
    '/dashboard/atenciones': 'Historial de Atenciones',
    '/dashboard/usuarios': 'Control de Usuarios',
  };

  const currentTitle = pageTitles[location.pathname] || 'Panel Médico';
  const alternar = (menu) => setMenuAbierto((prev) => (prev === menu ? null : menu));

  return (
    <header className="h-16 lg:h-20 bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-6 shadow-xs z-30 shrink-0">
      <div className="flex items-center gap-2 lg:gap-4">
        {/* Botón del menú lateral */}
        <button
          onClick={toggleSidebar}
          className="p-2.5 min-h-11 min-w-11 rounded-lg text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer flex items-center justify-center"
          aria-label="Alternar menú lateral"
          title="Alternar Menú"
        >
          <AlignLeft className="w-5 h-5 text-slate-700" aria-hidden="true" />
        </button>

        <h1 className="font-semibold text-slate-800 text-base lg:text-lg hidden sm:block font-lexend">
          {currentTitle}
        </h1>
      </div>

      <div className="flex items-center gap-2 lg:gap-3">
        {/* Indicador de Sesión Activa y Hora */}
        <div className="hidden md:flex items-center gap-2.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs text-slate-600">
          <span className="relative flex h-2.5 w-2.5" aria-hidden="true">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="font-medium text-slate-700">Sesión Activa</span>
          <span className="text-slate-300">|</span>
          <div className="flex items-center gap-1 text-slate-500 font-medium">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{currentTime}</span>
          </div>
        </div>

        {/* Notificaciones */}
        <div className="relative" ref={refNotificaciones}>
          <button
            onClick={() => alternar('notificaciones')}
            aria-label="Notificaciones"
            aria-haspopup="menu"
            aria-expanded={menuAbierto === 'notificaciones'}
            className="relative p-2.5 min-h-11 min-w-11 rounded-full hover:bg-slate-100 text-slate-700 transition-colors cursor-pointer border border-slate-200 flex items-center justify-center"
          >
            <Bell className="w-5 h-5" aria-hidden="true" />
          </button>

          {menuAbierto === 'notificaciones' && (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-white border border-slate-200 rounded-xl shadow-xl py-2 z-50"
            >
              <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800">Notificaciones</p>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <div className="px-4 py-3 text-xs text-slate-500">
                  Aún no hay notificaciones del sistema.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Perfil de Usuario */}
        <div className="relative" ref={refUsuario}>
          <button
            onClick={() => alternar('usuario')}
            aria-haspopup="menu"
            aria-expanded={menuAbierto === 'usuario'}
            aria-label={`Cuenta de ${user?.nombre ?? 'usuario'}`}
            className="flex items-center gap-2 lg:gap-3 py-1.5 px-2 lg:px-3 min-h-11 rounded-full hover:bg-slate-100 transition-colors cursor-pointer border border-slate-200"
          >
            <span className="text-sm font-medium text-slate-700 hidden sm:block">
              {etiquetaRol(user?.rol)}
            </span>
            {/* Avatar con la inicial del nombre */}
            <div className="w-8 h-8 rounded-full bg-[#17324c] text-white flex items-center justify-center font-semibold text-sm uppercase">
              {user?.nombre ? user.nombre.charAt(0) : 'U'}
            </div>
            <ChevronDown
              className={`w-4 h-4 text-slate-500 transition-transform ${
                menuAbierto === 'usuario' ? 'rotate-180' : ''
              }`}
              aria-hidden="true"
            />
          </button>

          {menuAbierto === 'usuario' && (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-56 bg-white border border-slate-200 rounded-lg shadow-xl py-1 z-50"
            >
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="text-xs text-slate-500">Conectado como</p>
                <p className="text-sm font-semibold text-slate-800 truncate">
                  {user?.nombre ?? 'Usuario'}
                </p>
                <p className="text-xs text-slate-500 truncate">{user?.email ?? ''}</p>
              </div>
              <button
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
                className="w-full text-left px-4 py-2.5 min-h-11 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2 cursor-pointer"
              >
                <LogOut className="w-4 h-4" aria-hidden="true" />
                <span>Cerrar Sesión</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
