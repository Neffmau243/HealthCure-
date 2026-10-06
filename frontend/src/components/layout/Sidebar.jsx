import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Activity,
  FileText,
  Stethoscope,
  History,
  ShieldCheck,
  LogOut,
} from 'lucide-react';
import logoImage from '../../assets/logo.png';
import { useAuth } from '../../context/useAuth';
import { PERMISSIONS } from '../../constants/roles';

// Menú agrupado por secciones, en el orden del flujo real de atención:
// registrar paciente → triaje → consulta → historial.
const SECCIONES = [
  {
    titulo: 'Principal',
    items: [
      { id: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    titulo: 'Atención clínica',
    items: [
      { id: 'pacientes', label: 'Pacientes', path: '/dashboard/pacientes', icon: Users, paso: 1 },
      { id: 'triaje', label: 'Triaje', path: '/dashboard/triaje', icon: Activity, paso: 2 },
      { id: 'consultorio', label: 'Consultorio', path: '/dashboard/consultorio', icon: Stethoscope, paso: 3 },
    ],
  },
  {
    titulo: 'Registros',
    items: [
      { id: 'historiales', label: 'Historias Clínicas', path: '/dashboard/historiales', icon: FileText },
      { id: 'atenciones', label: 'Historial de Atenciones', path: '/dashboard/atenciones', icon: History },
    ],
  },
  {
    titulo: 'Administración',
    items: [
      { id: 'usuarios', label: 'Gestión de Usuarios', path: '/dashboard/usuarios', icon: ShieldCheck },
    ],
  },
];

export default function Sidebar({ sidebarOpen, setSidebarOpen }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  // Solo se muestran los módulos permitidos y las secciones con al menos un módulo.
  const seccionesVisibles = SECCIONES.map((seccion) => ({
    ...seccion,
    items: seccion.items.filter((item) => {
      const allowedRoles = PERMISSIONS[item.path];
      return allowedRoles && user && allowedRoles.includes(user.rol);
    }),
  })).filter((seccion) => seccion.items.length > 0);

  const irA = (path) => {
    navigate(path);
    if (window.innerWidth < 1024) setSidebarOpen(false);
  };

  return (
    <aside
      className={`absolute inset-y-0 left-0 z-50 bg-[#56ccf2] flex flex-col transition-all duration-300 ease-in-out lg:relative overflow-hidden ${
        sidebarOpen ? 'w-64 shadow-xl lg:shadow-none' : 'w-0 -translate-x-full lg:translate-x-0'
      }`}
    >
      <div className="w-64 flex flex-col h-full">
        <div className="flex items-center justify-center h-20 px-3 bg-[#7FCFEC] border-b border-sky-300/60 shadow-xs shrink-0">
          <img
            src={logoImage}
            alt="Logo"
            className="w-[210px] h-auto max-h-16 object-contain drop-shadow-sm scale-200"
          />
        </div>

        <nav className="flex-1 overflow-y-auto py-3 px-3 flex flex-col gap-3 custom-scrollbar">
          {seccionesVisibles.map((seccion) => (
            <div key={seccion.titulo} className="flex flex-col gap-1">
              <p className="px-4 text-[10px] font-bold uppercase tracking-widest text-[#17324c]/60">
                {seccion.titulo}
              </p>

              {seccion.items.map((item) => {
                const IconComponent = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <button
                    key={item.id}
                    onClick={() => irA(item.path)}
                    className={`flex items-center gap-3 w-full px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer whitespace-nowrap ${
                      isActive
                        ? 'bg-[#17324c] text-white shadow-md'
                        : 'text-slate-800 hover:bg-sky-300/50'
                    }`}
                  >
                    <IconComponent
                      className={`w-5 h-5 shrink-0 ${isActive ? 'text-white' : 'text-slate-700'}`}
                    />
                    <span className="flex-1 text-left">{item.label}</span>

                    {/* Número de paso del flujo clínico (Pacientes → Triaje → Consultorio) */}
                    {item.paso && (
                      <span
                        className={`w-5 h-5 shrink-0 rounded-full text-[10px] font-bold flex items-center justify-center ${
                          isActive ? 'bg-white/25 text-white' : 'bg-[#17324c]/10 text-[#17324c]'
                        }`}
                        title={`Paso ${item.paso} del flujo de atención`}
                      >
                        {item.paso}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-sky-400/60 shrink-0">
          <button
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="flex items-center gap-3.5 w-full px-4 py-3 rounded-lg text-sm font-medium text-red-700 hover:bg-red-500/10 transition-colors cursor-pointer whitespace-nowrap"
          >
            <LogOut className="w-5 h-5 text-red-600 shrink-0" />
            <span>Cerrar Sesión</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
