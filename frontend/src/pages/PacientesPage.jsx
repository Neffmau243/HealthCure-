import { useEffect, useState } from 'react';
import { Search, Plus, FileText, Edit } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Tabla from '../components/ui/Tabla';
import ModalPaciente from '../components/pacientes/ModalPaciente';
import { Cargando, Alerta } from '../components/ui/Feedback';
import { pacientesService } from '../services/pacientes';
import { catalogosService } from '../services/catalogos';
import { mensajeError } from '../services/api';
import { calcularEdad, etiquetaSexo, nombreCompleto } from '../utils/triaje';

// Opcional = "" -> null (evita strings vacíos y choques de UNIQUE en la BD)
const opcional = (valor) => {
  const limpio = String(valor ?? '').trim();
  return limpio === '' ? null : limpio;
};
const numeroOpcional = (valor) => {
  const limpio = String(valor ?? '').trim();
  if (limpio === '') return null;
  const n = Number(limpio);
  return Number.isFinite(n) ? n : null;
};

const FORM_VACIO = {
  tipo_documento: 'DNI',
  documento_identidad: '',
  numero_historia_clinica: '',
  apellido_paterno: '',
  apellido_materno: '',
  nombres: '',
  fecha_nacimiento: '',
  sexo: 'M',
  telefono: '',
  direccion: '',
  distrito_id: '',
  localidad_id: '',
  tipo_seguro: 'SIS',
  codigo_afiliacion_seguro: '',
  talla_cm: '',
  peso_kg: '',
};

export default function PacientesPage() {
  const navigate = useNavigate();

  const [pacientes, setPacientes] = useState([]);
  const [distritos, setDistritos] = useState([]);
  const [localidades, setLocalidades] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pacienteEditando, setPacienteEditando] = useState(null);
  const [formData, setFormData] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState(null);
  const [cargandoLocalidades, setCargandoLocalidades] = useState(false);
  const [busqueda, setBusqueda] = useState('');

  // --- Carga de datos ---
  // Se llama desde el efecto inicial y tras guardar un paciente.
  const cargarPacientes = async () => {
    try {
      setPacientes(await pacientesService.listar());
      setError(null);
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar los pacientes'));
    }
  };

  // Carga inicial: los setState ocurren DESPUÉS del await, así el efecto
  // no provoca renders en cascada.
  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [listaPacientes, listaDistritos] = await Promise.all([
          pacientesService.listar(),
          catalogosService.distritos(),
        ]);
        if (!activo) return;
        setPacientes(listaPacientes);
        setDistritos(listaDistritos);
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

  // --- Localidades encadenadas al distrito elegido ---
  useEffect(() => {
    const distritoId = formData.distrito_id;
    if (!isModalOpen || !distritoId) return;

    let activo = true;
    (async () => {
      try {
        const data = await catalogosService.localidades(distritoId);
        if (activo) setLocalidades(data);
      } catch (e) {
        if (activo) setErrorForm(mensajeError(e, 'No se pudieron cargar las localidades'));
      } finally {
        if (activo) setCargandoLocalidades(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, [isModalOpen, formData.distrito_id]);

  // --- Handlers ---
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
      // Al cambiar de distrito, reseteamos la localidad (pertenece al distrito previo)
      ...(name === 'distrito_id' ? { localidad_id: '' } : {}),
    }));
    if (name === 'distrito_id') {
      setLocalidades([]);
      setCargandoLocalidades(Boolean(value));
    }
  };

  const abrirModalNuevo = () => {
    setPacienteEditando(null);
    setFormData(FORM_VACIO);
    setLocalidades([]);
    setCargandoLocalidades(false);
    setErrorForm(null);
    setIsModalOpen(true);
  };

  const abrirModalEditar = (paciente) => {
    setPacienteEditando(paciente);
    setFormData({
      tipo_documento: paciente.tipo_documento ?? 'DNI',
      documento_identidad: paciente.documento_identidad ?? '',
      numero_historia_clinica: paciente.numero_historia_clinica ?? '',
      apellido_paterno: paciente.apellido_paterno ?? '',
      apellido_materno: paciente.apellido_materno ?? '',
      nombres: paciente.nombres ?? '',
      fecha_nacimiento: paciente.fecha_nacimiento ?? '',
      sexo: paciente.sexo ?? 'M',
      telefono: paciente.telefono ?? '',
      direccion: paciente.direccion ?? '',
      distrito_id: paciente.distrito_id ?? '',
      localidad_id: paciente.localidad_id ?? '',
      tipo_seguro: paciente.tipo_seguro ?? 'SIS',
      codigo_afiliacion_seguro: paciente.codigo_afiliacion_seguro ?? '',
      talla_cm: paciente.talla_cm ?? '',
      peso_kg: paciente.peso_kg ?? '',
    });
    setLocalidades([]);
    setCargandoLocalidades(Boolean(paciente.distrito_id));
    setErrorForm(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setErrorForm(null);
    try {
      const payload = {
        tipo_documento: formData.tipo_documento,
        numero_historia_clinica: opcional(formData.numero_historia_clinica),
        apellido_paterno: formData.apellido_paterno.trim(),
        apellido_materno: opcional(formData.apellido_materno),
        nombres: formData.nombres.trim(),
        fecha_nacimiento: formData.fecha_nacimiento,
        sexo: formData.sexo,
        telefono: opcional(formData.telefono),
        direccion: opcional(formData.direccion),
        distrito_id: numeroOpcional(formData.distrito_id),
        localidad_id: numeroOpcional(formData.localidad_id),
        tipo_seguro: formData.tipo_seguro,
        codigo_afiliacion_seguro: opcional(formData.codigo_afiliacion_seguro),
        talla_cm: numeroOpcional(formData.talla_cm),
        peso_kg: numeroOpcional(formData.peso_kg),
      };

      if (pacienteEditando) {
        await pacientesService.actualizar(pacienteEditando.id, payload);
      } else {
        await pacientesService.crear({
          ...payload,
          documento_identidad: formData.documento_identidad.trim(),
        });
      }

      setIsModalOpen(false);
      await cargarPacientes();
    } catch (err) {
      setErrorForm(mensajeError(err, 'No se pudo guardar el paciente'));
    } finally {
      setGuardando(false);
    }
  };

  // --- Filtro local (la lista completa ya está cargada) ---
  const termino = busqueda.trim().toLowerCase();
  const pacientesFiltrados = termino
    ? pacientes.filter((p) =>
        [p.documento_identidad, p.nombre_completo, p.nombres, p.apellido_paterno, p.apellido_materno]
          .filter(Boolean)
          .some((campo) => String(campo).toLowerCase().includes(termino))
      )
    : pacientes;

  const columnasPacientes = [
    {
      titulo: 'Documento',
      render: (row) => (
        <span className="font-semibold text-slate-700">{row.documento_identidad}</span>
      ),
    },
    {
      titulo: 'Paciente',
      render: (row) => (
        <div>
          <p className="font-medium text-slate-900">{nombreCompleto(row)}</p>
          {row.numero_historia_clinica && (
            <p className="text-xs text-slate-400">H.C. {row.numero_historia_clinica}</p>
          )}
        </div>
      ),
    },
    {
      titulo: 'Edad',
      render: (row) => {
        const edad = calcularEdad(row.fecha_nacimiento);
        return <span className="text-slate-600">{edad != null ? `${edad} años` : '—'}</span>;
      },
    },
    {
      titulo: 'Sexo',
      render: (row) => <span className="text-slate-600">{etiquetaSexo(row.sexo)}</span>,
    },
    {
      titulo: 'Ubicación',
      render: (row) => (
        <span className="text-slate-600">{row.distrito || row.localidad || '—'}</span>
      ),
    },
    {
      titulo: 'Seguro',
      render: (row) => (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
          {row.tipo_seguro}
        </span>
      ),
    },
    {
      titulo: 'Acciones',
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => navigate('/dashboard/historiales', { state: { pacienteId: row.id } })}
            title="Ver Historia Clínica"
            className="p-1.5 bg-sky-50 text-sky-600 rounded-lg hover:bg-sky-100 transition cursor-pointer inline-flex items-center justify-center"
          >
            <FileText className="w-4 h-4" />
          </button>
          <button
            onClick={() => abrirModalEditar(row)}
            title="Editar Paciente"
            className="p-1.5 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition cursor-pointer inline-flex items-center justify-center"
          >
            <Edit className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Gestión de Pacientes</h1>
          <p className="text-sm text-slate-500 mt-1">
            Directorio y registro general de datos personales de pacientes.
          </p>
        </div>
        <button
          onClick={abrirModalNuevo}
          className="flex items-center justify-center gap-2 bg-[#17324c] hover:bg-slate-800 text-white px-4 py-2.5 rounded-xl font-medium shadow-md transition-all cursor-pointer w-full sm:w-auto"
        >
          <Plus className="w-5 h-5" />
          <span>Nuevo Paciente</span>
        </button>
      </div>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      <div className="bg-white p-4 rounded-2xl shadow-xs border border-slate-100 flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por documento, nombres o apellidos..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-11 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:bg-white transition"
          />
        </div>
      </div>

      {cargando ? (
        <Cargando texto="Cargando pacientes..." />
      ) : (
        <Tabla
          columnas={columnasPacientes}
          datos={pacientesFiltrados}
          mensajeVacio="No se encontraron registros de pacientes."
        />
      )}

      <ModalPaciente
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        formData={formData}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        esEdicion={!!pacienteEditando}
        distritos={distritos}
        localidades={localidades}
        cargandoLocalidades={cargandoLocalidades}
        guardando={guardando}
        error={errorForm}
      />
    </div>
  );
}
