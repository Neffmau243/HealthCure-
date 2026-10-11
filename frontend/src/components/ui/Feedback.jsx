import { Loader2, AlertCircle, CheckCircle2, Inbox } from 'lucide-react';

/** Indicador de carga centrado. */
export function Cargando({ texto = 'Cargando...' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-slate-500 text-sm">
      <Loader2 className="w-5 h-5 animate-spin text-sky-500" />
      <span>{texto}</span>
    </div>
  );
}

/** Mensaje de error o confirmación. */
export function Alerta({ tipo = 'error', children, onClose }) {
  if (!children) return null;
  const estilos =
    tipo === 'exito'
      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
      : 'bg-rose-50 border-rose-200 text-rose-800';
  const Icono = tipo === 'exito' ? CheckCircle2 : AlertCircle;

  return (
    <div
      className={`flex items-start gap-3 p-3.5 border rounded-xl text-sm ${estilos}`}
      role={tipo === 'error' ? 'alert' : 'status'}
    >
      <Icono className="w-4 h-4 mt-0.5 shrink-0" />
      <div className="flex-1">{children}</div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="text-current opacity-60 hover:opacity-100 cursor-pointer"
          aria-label="Cerrar"
        >
          ✕
        </button>
      )}
    </div>
  );
}

/** Estado vacío para listados. */
export function Vacio({ titulo, detalle, icono: Icono = Inbox }) {
  return (
    <div className="bg-white rounded-2xl shadow-xs border border-slate-100 p-10 text-center">
      <Icono className="w-12 h-12 text-slate-300 mx-auto mb-3" />
      <h3 className="text-base font-semibold text-slate-700">{titulo}</h3>
      {detalle && <p className="text-sm text-slate-500 mt-1">{detalle}</p>}
    </div>
  );
}
