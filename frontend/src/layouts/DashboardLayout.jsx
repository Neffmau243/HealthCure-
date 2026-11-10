import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from "../components/layout/Sidebar";
import Topbar from "../components/layout/Topbar";

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.matchMedia('(min-width: 1024px)').matches);

  return (
    <div className="clinical-app flex h-dvh w-full overflow-hidden relative">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <div className="flex-1 min-w-0 flex flex-col h-full overflow-hidden">
        <Topbar sidebarOpen={sidebarOpen} toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main id="contenido-principal" className="clinical-main flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {/* Aquí se renderiza automáticamente la página hija activa de la URL */}
            <Outlet />
          </div>
        </main>
      </div>

      {sidebarOpen && (
        <button aria-label="Cerrar menú lateral" onClick={() => setSidebarOpen(false)} className="fixed inset-0 bg-slate-950/40 z-40 lg:hidden" />
      )}
    </div>
  );
}
