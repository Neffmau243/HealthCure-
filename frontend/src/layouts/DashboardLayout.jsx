import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from "../components/layout/Sidebar";
import Topbar from "../components/layout/Topbar";

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.matchMedia('(min-width: 1024px)').matches);
  const [desktop, setDesktop] = useState(() => window.matchMedia('(min-width: 1024px)').matches);
  const mobileOpen = sidebarOpen && !desktop;

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)');
    const actualizar = ({ matches }) => {
      setDesktop(matches);
      setSidebarOpen(matches);
    };
    media.addEventListener('change', actualizar);
    return () => media.removeEventListener('change', actualizar);
  }, []);

  return (
    <div className="clinical-app flex h-dvh w-full overflow-hidden relative">
      <a className="skip-link" href="#contenido-principal">Saltar al contenido</a>
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} mobileOpen={mobileOpen} />

      <div inert={mobileOpen} className="flex-1 min-w-0 flex flex-col h-full overflow-hidden">
        <Topbar sidebarOpen={sidebarOpen} toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main id="contenido-principal" tabIndex={-1} className="clinical-main flex-1 overflow-y-auto flex flex-col">
          <div className="w-full max-w-7xl mx-auto flex-1">
            {/* Aquí se renderiza automáticamente la página hija activa de la URL */}
            <Outlet />
          </div>
          {/* Cierra la página con un final visible en vez de dejar el canvas vacío. */}
          <footer className="w-full max-w-7xl mx-auto mt-10 pt-4 border-t border-[#dce5eb] text-[11px] leading-relaxed text-[#667585] flex flex-wrap items-center justify-between gap-2">
            <span>HealthCure · Gestión de la atención</span>
            <span>El índice del modelo apoya el tamizaje; no reemplaza el criterio clínico.</span>
          </footer>
        </main>
      </div>

      {mobileOpen && (
        <div aria-hidden="true" onClick={() => setSidebarOpen(false)} className="fixed inset-0 bg-slate-950/40 z-40 lg:hidden" />
      )}
    </div>
  );
}
