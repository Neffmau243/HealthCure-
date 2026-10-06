import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Search,
  Activity,
  FileText,
  UserPlus,
  ArrowRight,
  BrainCircuit,
  ClipboardList,
  CheckCircle2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Tabla from '../components/ui/Tabla';
import ModalTriaje from '../components/triaje/ModalTriaje';
import TarjetaTriaje from '../components/triaje/TarjetaTriaje';
import { Cargando, Alerta } from '../components/ui/Feedback';
import { pacientesService } from '../services/pacientes';
import { evaluacionesService } from '../services/evaluaciones';
import { mensajeError } from '../services/api';
import {
  calcularEdad,
  construirPayloadEvaluacion,
  etiquetaSexo,
  nombreCompleto,
  clasesClasificacion,
} from '../utils/triaje';

const LIMITE_EVALUACIONES = 200;

const FILTROS = [
  { id: 'pendientes', label: 'Pendientes de triaje' },
  { id: 'evaluados', label: 'Ya evaluados' },
  { id: 'todos', label: 'Todos' },
];

export default function TriajePage() {
  const navigate = useNavigate();
  const refResultado = useRef(null);

  const [pacientes, setPacientes] = useState([]);
  const [evaluaciones, setEvaluaciones] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState('todos');

  const [pacienteSeleccionado, setPacienteSeleccionado] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState(null);
  const [resultado, setResultado] = useState(null);

  const cargarTodo = async () => {
    try {
      const [listaPacientes, listaEvaluaciones] = await Promise.all([
        pacientesService.listar(),
        evaluacionesService.listar({ limit: LIMITE_EVALUACIONES }),
      ]);
      setPacientes(listaPacientes);
      setEvaluaciones(listaEvaluaciones);
      setError(null);
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar los datos'));
    } finally {
      setCargando(false);
    }
  };

  // Carga inicial: los setState ocurren DESPUÉS del await, así el efecto
  // no provoca renders en cascada.
  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [listaPacientes, listaEvaluaciones] = await Promise.all([
          pacientesService.listar(),
          evaluacionesService.listar({ limit: LIMITE_EVALUACIONES }),
        ]);
        if (!activo) return;
        setPacientes(listaPacientes);
        setEvaluaciones(listaEvaluaciones);
        setError(null);
      } catch (e) {
        if (activo) setError(mensajeError(e, 'No se pudieron cargar los datos'));
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, []);

  // Al generar una evaluación, llevamos la vista al resultado del modelo.
  useEffect(() => {
    if (resultado && refResultado.current) {
      refResultado.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [resultado]);

  // Última evaluación de cada paciente (el backend ya devuelve lo más reciente primero).
  const evaluacionesPorPaciente = useMemo(() => {
    const mapa = {};
    for (const ev of evaluaciones) {
      if (!mapa[ev.paciente_id]) mapa[ev.paciente_id] = [];
      mapa[ev.paciente_id].push(ev);
    }
    return mapa;
  }, [evaluaciones]);

  const pendientes = useMemo(
    () => pacientes.filter((p) => !evaluacionesPorPaciente[p.id]?.length),
    [pacientes, evaluacionesPorPaciente]
  );
  const evaluados = useMemo(
    () => pacientes.filter((p) => evaluacionesPorPaciente[p.id]?.length),
    [pacientes, evaluacionesPorPaciente]
  );

  const guardarTriaje = async (datos) => {
    if (!pacienteSeleccionado) return;
    setGuardando(true);
    setErrorModal(null);
    try {
      const edad = calcularEdad(pacienteSeleccionado.fecha_nacimiento);
      const payload = construirPayloadEvaluacion(pacienteSeleccionado, datos, edad);
      const evaluacion = await evaluacionesService.crear(payload);
      // El backend devuelve el nombre del paciente en la evaluación, así que
      // guardamos contexto para mostrarlo en el resultado.
      setResultado({
        ...evaluacion,
        _pacienteNombre: nombreCompleto(pacienteSeleccionado),
      });
      setPacienteSeleccionado(null);
      await cargarTodo();
    } catch (e) {
      setErrorModal(mensajeError(e, 'No se pudo registrar el triaje'));
    } finally {
      setGuardando(false);
    }
  };

  const abrirTriaje = (paciente) => {
    setErrorModal(null);
    setPacienteSeleccionado(paciente);
  };

  const termino = busqueda.trim().toLowerCase();
  const coincideBusqueda = (p) =>
    [p.documento_identidad, p.nombre_completo, p.apellido_paterno, p.nombres]
      .filter(Boolean)
      .some((c) => String(c).toLowerCase().includes(termino));

  const base =
    filtro === 'pendientes' ? pendientes : filtro === 'evaluados' ? evaluados : pacientes;
  const pacientesFiltrados = termino ? base.filter(coincideBusqueda) : base;

  // Los pendientes primero: son los que requieren acción.
  const datosOrdenados = [...pacientesFiltrados].sort((a, b) => {
    const aPend = evaluacionesPorPaciente[a.id]?.length ? 1 : 0;
    const bPend = evaluacionesPorPaciente[b.id]?.length ? 1 : 0;
    return aPend - bPend;
  });

  const columnasTriaje = [
    {
      titulo: 'Documento',
      render: (row) => <span className="font-semibold text-slate-700">{row.documento_identidad}</span>,
    },
    {
      titulo: 'Paciente',
      render: (row) => <span className="font-medium text-slate-900">{nombreCompleto(row)}</span>,
    },
    {
      titulo: 'Edad',
      render: (row) => {
        const edad = calcularEdad(row.fecha_nacimiento);
        return (
          <span className={edad != null && edad >= 18 ? 'text-slate-600' : 'text-amber-700'}>
            {edad != null ? `${edad} años` : '—'}
          </span>
        );
      },
    },
    {
      titulo: 'Sexo',
      render: (row) => <span className="text-slate-600">{etiquetaSexo(row.sexo)}</span>,
    },
    {
      titulo: 'Estado',
      render: (row) => {
        const lista = evaluacionesPorPaciente[row.id];
        if (!lista?.length) {
          return (
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
              Pendiente de triaje
            </span>
          );
        }
        const ev = lista[0];
        return (
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${clasesClasificacion(
                ev.clasificacion
              )}`}
            >
              {ev.clasificacion} · {(ev.probabilidad * 100).toFixed(1)}%
            </span>
            <span className="text-xs text-slate-400">
              {lista.length} {lista.length === 1 ? 'evaluación' : 'evaluaciones'}
            </span>
          </div>
        );
      },
    },
    {
      titulo: 'Acciones',
      align: 'center',
      render: (row) => {
        const tieneEvaluaciones = Boolean(evaluacionesPorPaciente[row.id]?.length);
        return (
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => abrirTriaje(row)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition inline-flex items-center gap-1.5 cursor-pointer ${
                tieneEvaluaciones
                  ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  : 'bg-[#17324c] text-white hover:bg-slate-800 shadow-sm'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>{tieneEvaluaciones ? 'Nueva evaluación' : 'Iniciar triaje'}</span>
            </button>
            <button
              onClick={() => navigate('/dashboard/historiales', { state: { pacienteId: row.id } })}
              title="Ver historia clínica"
              className="p-1.5 bg-sky-50 text-sky-600 rounded-lg hover:bg-sky-100 transition cursor-pointer inline-flex items-center justify-center"
            >
              <FileText className="w-4 h-4" />
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Estación de Triaje</h1>
          <p className="text-sm text-slate-500 mt-1">
            Registra los signos vitales y el modelo de Machine Learning calcula el riesgo
            cardiovascular y su triaje clínico.
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard/pacientes')}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl text-sm font-medium shadow-md transition cursor-pointer w-full sm:w-auto"
        >
          <UserPlus className="w-4 h-4" />
          <span>Registrar paciente</span>
        </button>
      </div>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {/* Guía del proceso: deja claro el flujo paciente → triaje → modelo ML */}
      <div className="bg-white p-5 rounded-2xl shadow-xs border border-slate-100">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
          Cómo funciona el proceso
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-50 border border-slate-100">
            <span className="w-7 h-7 shrink-0 rounded-full bg-[#17324c] text-white text-xs font-bold flex items-center justify-center">
              1
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                <UserPlus className="w-4 h-4 text-slate-500" /> Registra al paciente
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Se guardan sus datos personales, ubicación y seguro.
              </p>
              <p className="text-xs font-semibold text-slate-700 mt-2">
                {pacientes.length} {pacientes.length === 1 ? 'paciente' : 'pacientes'} en total
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 rounded-xl bg-sky-50 border border-sky-100">
            <span className="w-7 h-7 shrink-0 rounded-full bg-sky-600 text-white text-xs font-bold flex items-center justify-center">
              2
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                <ClipboardList className="w-4 h-4 text-sky-600" /> Inicia el triaje
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Peso, talla, presión, antecedentes, hábitos y percepción de salud.
              </p>
              <p className="text-xs font-semibold text-sky-800 mt-2">
                {pendientes.length} pendiente{pendientes.length === 1 ? '' : 's'} de evaluar
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 rounded-xl bg-indigo-50 border border-indigo-100">
            <span className="w-7 h-7 shrink-0 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
              3
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                <BrainCircuit className="w-4 h-4 text-indigo-600" /> El modelo ML calcula el riesgo
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Probabilidad, clasificación y triaje clínico con semáforo y recomendaciones.
              </p>
              <p className="text-xs font-semibold text-indigo-800 mt-2">
                {evaluaciones.length} {evaluaciones.length === 1 ? 'evaluación realizada' : 'evaluaciones realizadas'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Resultado del modelo (aparece al registrar un triaje) */}
      {resultado && (
        <div ref={refResultado} className="space-y-2 scroll-mt-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-700 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Resultado del modelo ML
              {resultado._pacienteNombre && (
                <span className="font-normal text-slate-500">· {resultado._pacienteNombre}</span>
              )}
            </h2>
            <button
              onClick={() => setResultado(null)}
              className="text-xs text-slate-500 hover:text-slate-700 cursor-pointer"
            >
              Ocultar
            </button>
          </div>
          <TarjetaTriaje evaluacion={resultado} />
        </div>
      )}

      {/* Lista de pacientes en cola */}
      <div className="bg-white p-4 rounded-2xl shadow-xs border border-slate-100 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {FILTROS.map((f) => {
            const conteo =
              f.id === 'pendientes'
                ? pendientes.length
                : f.id === 'evaluados'
                  ? evaluados.length
                  : pacientes.length;
            const activo = filtro === f.id;
            return (
              <button
                key={f.id}
                onClick={() => setFiltro(f.id)}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  activo
                    ? 'bg-[#17324c] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {f.label} ({conteo})
              </button>
            );
          })}
        </div>

        <div className="relative">
          <Search className="absolute left-3.5 top-3 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar paciente por documento o nombres..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-11 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 transition"
          />
        </div>
      </div>

      {cargando ? (
        <Cargando texto="Cargando pacientes..." />
      ) : (
        <Tabla
          columnas={columnasTriaje}
          datos={datosOrdenados}
          mensajeVacio={
            filtro === 'pendientes'
              ? 'No hay pacientes pendientes de triaje. ¡Todos están evaluados!'
              : 'No se encontraron pacientes con ese criterio.'
          }
        />
      )}

      {/* Atajo al siguiente paso del flujo */}
      {!cargando && evaluados.length > 0 && (
        <div className="flex items-center justify-between gap-4 bg-slate-900 text-white p-4 rounded-2xl">
          <p className="text-sm">
            <span className="font-semibold">Siguiente paso:</span> revisa el resultado con el
            paciente en el Consultorio y registra la atención.
          </p>
          <button
            onClick={() => navigate('/dashboard/consultorio')}
            className="shrink-0 inline-flex items-center gap-2 px-4 py-2 bg-white text-slate-900 rounded-xl text-sm font-semibold hover:bg-slate-100 transition cursor-pointer"
          >
            Ir al Consultorio <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {pacienteSeleccionado && (
        <ModalTriaje
          paciente={pacienteSeleccionado}
          ultimaEvaluacion={evaluacionesPorPaciente[pacienteSeleccionado.id]?.[0] ?? null}
          onClose={() => setPacienteSeleccionado(null)}
          onGuardar={guardarTriaje}
          guardando={guardando}
          error={errorModal}
        />
      )}
    </div>
  );
}
