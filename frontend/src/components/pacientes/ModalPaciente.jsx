import { Loader2 } from 'lucide-react';
import { Alerta } from '../ui/Feedback';

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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-2xl p-6 lg:p-8 max-w-3xl w-full shadow-2xl border border-slate-100 my-8">
        <div className="flex justify-between items-center mb-6 border-b pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">
              {esEdicion ? 'Editar Paciente' : 'Registrar Nuevo Paciente'}
            </h2>
            <p className="text-xs text-slate-500">
              Datos personales, ubicación y seguro del paciente.
            </p>
          </div>
          <button
            onClick={onClose}
            type="button"
            className="text-slate-400 hover:text-slate-600 text-xl font-bold cursor-pointer"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          {error && <Alerta>{error}</Alerta>}

          {/* Identidad */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className={labelClass}>Tipo Documento</label>
              <select
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
              <label className={labelClass}>Nro. Documento *</label>
              <input
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
              <label className={labelClass}>N° Historia Clínica</label>
              <input
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
              <label className={labelClass}>Fecha Nacimiento *</label>
              <input
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
              <label className={labelClass}>Apellido Paterno *</label>
              <input
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
              <label className={labelClass}>Apellido Materno</label>
              <input
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
              <label className={labelClass}>Nombres *</label>
              <input
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
              <label className={labelClass}>Sexo *</label>
              <select name="sexo" value={formData.sexo} onChange={onChange} className={inputClass}>
                <option value="M">Masculino</option>
                <option value="F">Femenino</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Teléfono</label>
              <input
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
              <label className={labelClass}>Dirección</label>
              <input
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
              <label className={labelClass}>Distrito</label>
              <select
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
              <label className={labelClass}>
                Localidad {cargandoLocalidades && '(cargando...)'}
              </label>
              <select
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
              <label className={labelClass}>Tipo de Seguro</label>
              <select
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
              <label className={labelClass}>Código de Afiliación</label>
              <input
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
              <label className={labelClass}>Talla (cm)</label>
              <input
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
              <label className={labelClass}>Peso (kg)</label>
              <input
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

          <div className="flex justify-end gap-3 pt-6 border-t mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 font-medium text-sm transition cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="px-5 py-2.5 bg-[#17324c] hover:bg-slate-800 text-white rounded-xl font-medium text-sm shadow transition cursor-pointer disabled:opacity-60 inline-flex items-center gap-2"
            >
              {guardando && <Loader2 className="w-4 h-4 animate-spin" />}
              {esEdicion ? 'Actualizar Paciente' : 'Guardar Paciente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
