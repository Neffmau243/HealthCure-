import { Loader2 } from 'lucide-react';
import { Alerta } from '../ui/Feedback';
import { useDialogoAccesible } from '../../hooks/useDialogoAccesible';

const inputClass =
  'w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none disabled:opacity-60';
const labelClass = 'block text-xs font-medium text-slate-700 mb-1';

const TIPOS_DOCUMENTO = ['DNI', 'CE', 'Pasaporte'];
const TIPOS_SEGURO = ['SIS', 'EsSalud', 'Privado', 'Otro'];

export default function ModalPaciente({
  isOpen,
  onClose,
  formData,
  onChange,
  onSubmit,
  esEdicion,
  distritos = [],
  localidades = [],
  cargandoLocalidades = false,
  guardando = false,
  error = null,
}) {
  // Scroll bloqueado, Escape, clic fuera y foco inicial: ver el hook.
  // Se llama ANTES del early return para no romper el orden de los hooks.
  const { propsContenedor, alClicFondo } = useDialogoAccesible({
    abierto: isOpen,
    onClose,
    ocupado: guardando,
  });

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50"
      onClick={alClicFondo}
    >
      <div
        {...propsContenedor}
        aria-labelledby="titulo-modal-paciente"
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] shadow-2xl border border-slate-100 flex flex-col"
      >
        <div className="flex justify-between items-center p-6 lg:p-8 pb-4 border-b border-slate-100 shrink-0">
          <div>
            <h2 id="titulo-modal-paciente" className="text-xl font-bold text-slate-800">
              {esEdicion ? 'Editar Paciente' : 'Registrar Nuevo Paciente'}
            </h2>
            <p className="text-xs text-slate-500">
              Datos personales, ubicación y seguro del paciente.
            </p>
          </div>
          <button
            onClick={onClose}
            type="button"
            className="text-slate-400 hover:text-slate-600 text-xl font-bold cursor-pointer w-11 h-11 flex items-center justify-center rounded-lg hover:bg-slate-100"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="flex flex-col min-h-0 flex-1">
          <div className="overflow-y-auto p-6 lg:p-8 pt-5 space-y-5 flex-1">
            {error && <Alerta>{error}</Alerta>}

            {/* Identidad */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div>
                <label className={labelClass} htmlFor="pac-tipo_documento">
                  Tipo Documento
                </label>
                <select
                  id="pac-tipo_documento"
                  name="tipo_documento"
                  value={formData.tipo_documento}
                  onChange={onChange}
                  className={inputClass}
                >
                  {TIPOS_DOCUMENTO.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-documento_identidad">
                  Nro. Documento *
                </label>
                <input
                  id="pac-documento_identidad"
                  type="text"
                  name="documento_identidad"
                  required
                  minLength={5}
                  maxLength={30}
                  disabled={esEdicion}
                  value={formData.documento_identidad}
                  onChange={onChange}
                  placeholder="72345634"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-numero_historia_clinica">
                  N° Historia Clínica
                </label>
                <input
                  id="pac-numero_historia_clinica"
                  type="text"
                  name="numero_historia_clinica"
                  maxLength={30}
                  value={formData.numero_historia_clinica}
                  onChange={onChange}
                  placeholder="72769512"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-fecha_nacimiento">
                  Fecha Nacimiento *
                </label>
                <input
                  id="pac-fecha_nacimiento"
                  type="date"
                  name="fecha_nacimiento"
                  required
                  value={formData.fecha_nacimiento}
                  onChange={onChange}
                  className={inputClass}
                />
              </div>
            </div>

            {/* Nombres */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className={labelClass} htmlFor="pac-apellido_paterno">
                  Apellido Paterno *
                </label>
                <input
                  id="pac-apellido_paterno"
                  type="text"
                  name="apellido_paterno"
                  required
                  minLength={2}
                  maxLength={100}
                  value={formData.apellido_paterno}
                  onChange={onChange}
                  placeholder="Pérez"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-apellido_materno">
                  Apellido Materno
                </label>
                <input
                  id="pac-apellido_materno"
                  type="text"
                  name="apellido_materno"
                  maxLength={100}
                  value={formData.apellido_materno}
                  onChange={onChange}
                  placeholder="Rodríguez"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-nombres">
                  Nombres *
                </label>
                <input
                  id="pac-nombres"
                  type="text"
                  name="nombres"
                  required
                  minLength={2}
                  maxLength={100}
                  value={formData.nombres}
                  onChange={onChange}
                  placeholder="Juan"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Contacto + sexo */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className={labelClass} htmlFor="pac-sexo">
                  Sexo *
                </label>
                <select
                  id="pac-sexo"
                  name="sexo"
                  value={formData.sexo}
                  onChange={onChange}
                  className={inputClass}
                >
                  <option value="M">Masculino</option>
                  <option value="F">Femenino</option>
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-telefono">
                  Teléfono
                </label>
                <input
                  id="pac-telefono"
                  type="text"
                  name="telefono"
                  maxLength={20}
                  value={formData.telefono}
                  onChange={onChange}
                  placeholder="987654321"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-direccion">
                  Dirección
                </label>
                <input
                  id="pac-direccion"
                  type="text"
                  name="direccion"
                  maxLength={200}
                  value={formData.direccion}
                  onChange={onChange}
                  placeholder="Av. Arequipa 123"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Ubicación (catálogos) + seguro */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className={labelClass} htmlFor="pac-distrito_id">
                  Distrito
                </label>
                <select
                  id="pac-distrito_id"
                  name="distrito_id"
                  value={formData.distrito_id}
                  onChange={onChange}
                  className={inputClass}
                >
                  <option value="">Sin distrito</option>
                  {distritos.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-localidad_id">
                  Localidad {cargandoLocalidades && '(cargando...)'}
                </label>
                <select
                  id="pac-localidad_id"
                  name="localidad_id"
                  value={formData.localidad_id}
                  onChange={onChange}
                  disabled={!formData.distrito_id || cargandoLocalidades}
                  className={inputClass}
                >
                  <option value="">Sin localidad</option>
                  {localidades.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-tipo_seguro">
                  Tipo de Seguro
                </label>
                <select
                  id="pac-tipo_seguro"
                  name="tipo_seguro"
                  value={formData.tipo_seguro}
                  onChange={onChange}
                  className={inputClass}
                >
                  {TIPOS_SEGURO.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-codigo_afiliacion_seguro">
                  Código de Afiliación
                </label>
                <input
                  id="pac-codigo_afiliacion_seguro"
                  type="text"
                  name="codigo_afiliacion_seguro"
                  maxLength={50}
                  value={formData.codigo_afiliacion_seguro}
                  onChange={onChange}
                  placeholder="040-2-1032456789"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Mediciones */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelClass} htmlFor="pac-talla_cm">
                  Talla (cm)
                </label>
                <input
                  id="pac-talla_cm"
                  type="number"
                  step="0.1"
                  min="1"
                  max="300"
                  name="talla_cm"
                  value={formData.talla_cm}
                  onChange={onChange}
                  placeholder="170.5"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="pac-peso_kg">
                  Peso (kg)
                </label>
                <input
                  id="pac-peso_kg"
                  type="number"
                  step="0.1"
                  min="1"
                  max="500"
                  name="peso_kg"
                  value={formData.peso_kg}
                  onChange={onChange}
                  placeholder="72.3"
                  className={inputClass}
                />
              </div>
            </div>
          </div>

          {/* Acciones fijas: no hay que bajar todo el formulario para guardar */}
          <div className="px-6 lg:px-8 py-4 border-t border-slate-100 bg-slate-50/70 rounded-b-2xl flex flex-col-reverse sm:flex-row sm:justify-end gap-3 shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 min-h-11 border border-slate-200 rounded-xl text-slate-600 hover:bg-white bg-white font-medium text-sm transition cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="px-5 py-2.5 min-h-11 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl font-medium text-sm shadow transition cursor-pointer disabled:opacity-60 inline-flex items-center justify-center gap-2"
            >
              {guardando && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
              {esEdicion ? 'Actualizar Paciente' : 'Guardar Paciente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
