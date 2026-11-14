import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Activity,
  FileText,
  Stethoscope,
  History,
  ShieldCheck,
  LogOut,
  X,
  HeartPulse,
  BarChart3,
} from 'lucide-react';
import { useAuth } from '../../context/useAuth';
import { PERMISSIONS } from '../../constants/roles';
import { useDialogoAccesible } from '../../hooks/useDialogoAccesible';

// Menú agrupado por secciones, en el orden del flujo real de atención:
// registrar paciente → triaje → consulta → historial.
const SECCIONES = [
  {
    titulo: 'Principal',
    items: [
      { id: 'dashboard', label: 'Inicio', path: '/dashboard', icon: LayoutDashboard },
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
    titulo: 'Análisis',
    items: [
      { id: 'reportes', label: 'Reportes y análisis', path: '/dashboard/reportes', icon: BarChart3 },
    ],
  },
  {
    titulo: 'Administración',
    items: [
      { id: 'usuarios', label: 'Gestión de Usuarios', path: '/dashboard/usuarios', icon: ShieldCheck },
    ],
  },
];

export default function Sidebar({ sidebarOpen, setSidebarOpen, mobileOpen }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { refContenedor, propsContenedor } = useDialogoAccesible({
    abierto: mobileOpen,
    onClose: () => setSidebarOpen(false),
  });

  // Solo se muestran los módulos permitidos y las secciones con al menos un módulo.
  const seccionesVisibles = SECCIONES.map((seccion) => ({
    ...seccion,
    items: seccion.items.filter((item) => {
      const allowedRoles = PERMISSIONS[item.path];
      return allowedRoles && user && allowedRoles.includes(user.rol);
    }),
  })).filter((seccion) => seccion.items.length > 0);

  const cerrarEnMovil = () => {
    if (window.innerWidth < 1024) setSidebarOpen(false);
  };

  return (
    <aside
      {...(mobileOpen ? propsContenedor : { ref: refContenedor })}
      id="navegacion-principal"
      aria-label="Navegación principal"
      inert={!sidebarOpen}
      className={`clinical-sidebar absolute inset-y-0 left-0 z-50 flex flex-col transition-all duration-200 ease-out lg:relative overflow-hidden shrink-0 ${
        sidebarOpen ? 'w-64 shadow-xl lg:shadow-none' : 'w-0 -translate-x-full lg:translate-x-0'
      }`}
    >
      <div className="w-64 flex flex-col h-full">
        <div className="sidebar-brand shrink-0">
          <HeartPulse className="w-8 h-8 shrink-0" aria-hidden="true" />
          <div><span className="block text-lg font-bold tracking-tight">HealthCure</span><span className="block text-xs text-[#24475c]">Gestión de la atención</span></div>
          <button onClick={() => setSidebarOpen(false)} aria-label="Cerrar navegación" className="lg:hidden absolute right-1 top-2 min-h-11 min-w-11 inline-flex items-center justify-center"><X className="w-4 h-4" /></button>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-3" aria-label="Módulos del sistema">
          {seccionesVisibles.map((seccion) => (
            <div key={seccion.titulo} className="flex flex-col gap-1">
              <p className="px-3.5 mb-1 text-[11px] font-medium text-[#536577]">
                {seccion.titulo}
              </p>

              {seccion.items.map((item) => {
                const IconComponent = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    end
                    onClick={cerrarEnMovil}
                    aria-current={isActive ? 'page' : undefined}
                    className={`sidebar-link flex items-center gap-3 w-full px-3.5 py-2.5 min-h-11 rounded-lg text-[13px] font-medium transition-colors cursor-pointer whitespace-nowrap ${
                      isActive
                        ? 'bg-[#17324c] text-white'
                        : 'text-[#17324c] hover:bg-white/45'
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
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-[#17324c]/15 shrink-0">
          <button
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="flex items-center gap-3.5 w-full px-4 py-3 rounded-xl text-sm font-medium text-[#17324c] hover:bg-white/40 transition-colors cursor-pointer whitespace-nowrap"
          >
            <LogOut className="w-5 h-5 shrink-0" />
            <span>Cerrar Sesión</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
