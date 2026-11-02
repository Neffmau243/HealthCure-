import PageHeader from '../components/ui/PageHeader';
import { useEffect, useState } from 'react';
import { History } from 'lucide-react';
import { atencionesService } from '../services/atenciones';
import TarjetaAtencion from '../components/atenciones/TarjetaAtencion';
import { mensajeError } from '../services/api';
import { Cargando, Alerta, Vacio } from '../components/ui/Feedback';

const PAGINA = 25;

export default function AtencionesPage() {
  const [atenciones, setAtenciones] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [error, setError] = useState(null);
  const [hayMas, setHayMas] = useState(true);

  // Carga inicial: los setState ocurren DESPUÉS del await, así el efecto
  // no provoca renders en cascada.
  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const data = await atencionesService.listar({ limit: PAGINA, offset: 0 });
        if (!activo) return;
        setAtenciones(data);
        setHayMas(data.length === PAGINA);
        setError(null);
      } catch (e) {
        if (activo) setError(mensajeError(e, 'No se pudieron cargar las atenciones'));
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, []);

  const cargarMas = async () => {
    setCargandoMas(true);
    setError(null);
    try {
      const data = await atencionesService.listar({
        limit: PAGINA,
        offset: atenciones.length,
      });
      setAtenciones((prev) => [...prev, ...data]);
      setHayMas(data.length === PAGINA);
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar las atenciones'));
    } finally {
      setCargandoMas(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Historial de atenciones" description="Consulta las atenciones registradas, sus hallazgos clínicos y el FUA de cada visita." />

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {cargando ? (
        <Cargando texto="Cargando atenciones..." />
      ) : atenciones.length === 0 ? (
        <Vacio
          titulo="Sin atenciones registradas"
          detalle="Las atenciones que registres en el Consultorio aparecerán aquí."
          icono={History}
        />
      ) : (
        <>
          <div className="clinical-panel divide-y divide-slate-100">
            {atenciones.map((a) => (
              <div key={a.id} className="p-5">
                <TarjetaAtencion atencion={a} mostrarPaciente />
              </div>
            ))}
          </div>

          {hayMas && (
            <div className="flex justify-center">
              <button
                onClick={cargarMas}
                disabled={cargandoMas}
                className="px-5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 transition cursor-pointer disabled:opacity-60"
              >
                {cargandoMas ? 'Cargando...' : 'Cargar más'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
