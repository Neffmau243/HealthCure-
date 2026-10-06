import { useEffect, useState } from 'react';
import { UserPlus, Loader2, Pencil, UserCheck, UserX } from 'lucide-react';
import Tabla from '../components/ui/Tabla';
import { Cargando, Alerta } from '../components/ui/Feedback';
import { usuariosService } from '../services/usuarios';
import { mensajeError } from '../services/api';
import { useAuth } from '../context/useAuth';
import { ROLES, etiquetaRol } from '../constants/roles';

const FORM_VACIO = { nombre: '', email: '', password: '', rol: ROLES.USUARIO, activo: true };

export default function UsuariosPage() {
  const { user } = useAuth();

  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState(null);
  const [ocupadoId, setOcupadoId] = useState(null);

  const cargar = async () => {
    setCargando(true);
    try {
      setUsuarios(await usuariosService.listar());
      setError(null);
    } catch (e) {
      setError(mensajeError(e, 'No se pudieron cargar los usuarios'));
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
        const data = await usuariosService.listar();
        if (!activo) return;
        setUsuarios(data);
        setError(null);
      } catch (e) {
        if (activo) setError(mensajeError(e, 'No se pudieron cargar los usuarios'));
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, []);

  const abrirNuevo = () => {
    setEditando(null);
    setForm(FORM_VACIO);
    setErrorForm(null);
    setModalOpen(true);
  };

  const abrirEditar = (u) => {
    setEditando(u);
    setForm({
      nombre: u.nombre,
      email: u.email,
      password: '',
      rol: u.rol,
      activo: u.activo,
    });
    setErrorForm(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setErrorForm(null);
    try {
      if (editando) {
        // Update parcial: solo mandamos password si se escribió una nueva.
        const payload = {
          nombre: form.nombre.trim(),
          email: form.email.trim(),
          rol: form.rol,
          activo: form.activo,
        };
        if (form.password.trim()) payload.password = form.password;
        await usuariosService.actualizar(editando.id, payload);
      } else {
        await usuariosService.crear({
          nombre: form.nombre.trim(),
          email: form.email.trim(),
          password: form.password,
          rol: form.rol,
        });
      }
      setModalOpen(false);
      await cargar();
    } catch (err) {
      setErrorForm(mensajeError(err, 'No se pudo guardar el usuario'));
    } finally {
      setGuardando(false);
    }
  };

  const cambiarEstado = async (u) => {
    setOcupadoId(u.id);
    setError(null);
    try {
      if (u.activo) await usuariosService.desactivar(u.id);
      else await usuariosService.activar(u.id);
      await cargar();
    } catch (e) {
      setError(mensajeError(e, 'No se pudo cambiar el estado del usuario'));
    } finally {
      setOcupadoId(null);
    }
  };

  const columnas = [
    {
      titulo: 'Usuario',
      render: (u) => (
        <div>
          <p className="font-medium text-slate-900">
            {u.nombre}
            {u.id === user?.id && <span className="text-xs text-sky-600 ml-2">(tú)</span>}
          </p>
          <p className="text-xs text-slate-500">{u.email}</p>
        </div>
      ),
    },
    {
      titulo: 'Rol',
      render: (u) => (
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
            u.rol === ROLES.ADMIN ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100 text-slate-700'
          }`}
        >
          {etiquetaRol(u.rol)}
        </span>
      ),
    },
    {
      titulo: 'Estado',
      render: (u) => (
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
            u.activo ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
          }`}
        >
          {u.activo ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
    {
      titulo: 'Creado',
      render: (u) => (
        <span className="text-xs text-slate-500">
          {new Date(u.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      titulo: 'Acciones',
      align: 'center',
      render: (u) => (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => abrirEditar(u)}
            title="Editar"
            className="p-1.5 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition cursor-pointer inline-flex items-center justify-center"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={() => cambiarEstado(u)}
            disabled={ocupadoId === u.id}
            title={u.activo ? 'Desactivar' : 'Activar'}
            className={`p-1.5 rounded-lg transition cursor-pointer inline-flex items-center justify-center disabled:opacity-50 ${
              u.activo
                ? 'bg-rose-50 text-rose-600 hover:bg-rose-100'
                : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
            }`}
          >
            {ocupadoId === u.id ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : u.activo ? (
              <UserX className="w-4 h-4" />
            ) : (
              <UserCheck className="w-4 h-4" />
            )}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Gestión de Usuarios</h2>
          <p className="text-sm text-slate-500">
            Administra las cuentas y roles del personal del sistema.
          </p>
        </div>
        <button
          onClick={abrirNuevo}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-[#17324c] hover:bg-[#0f2235] text-white rounded-lg text-sm font-medium transition-colors cursor-pointer shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          <span>Nuevo Usuario</span>
        </button>
      </div>

      {error && <Alerta onClose={() => setError(null)}>{error}</Alerta>}

      {cargando ? (
        <Cargando texto="Cargando usuarios..." />
      ) : (
        <Tabla columnas={columnas} datos={usuarios} mensajeVacio="No hay usuarios registrados." />
      )}

      {modalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 lg:p-8 max-w-lg w-full shadow-2xl border border-slate-100">
            <div className="flex justify-between items-center mb-5 border-b pb-4">
              <h3 className="text-lg font-bold text-slate-800">
                {editando ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold cursor-pointer"
                aria-label="Cerrar"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {errorForm && <Alerta>{errorForm}</Alerta>}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Nombre *</label>
                <input
                  type="text"
                  required
                  minLength={2}
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Email *</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Contraseña {editando ? '(dejar vacío para no cambiar)' : '*'}
                </label>
                <input
                  type="password"
                  required={!editando}
                  minLength={6}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Rol</label>
                  <select
                    value={form.rol}
                    onChange={(e) => setForm({ ...form, rol: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none"
                  >
                    <option value={ROLES.USUARIO}>{etiquetaRol(ROLES.USUARIO)}</option>
                    <option value={ROLES.ADMIN}>{etiquetaRol(ROLES.ADMIN)}</option>
                  </select>
                </div>

                {editando && (
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Estado</label>
                    <select
                      value={form.activo ? '1' : '0'}
                      onChange={(e) => setForm({ ...form, activo: e.target.value === '1' })}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-sky-400 focus:outline-none"
                    >
                      <option value="1">Activo</option>
                      <option value="0">Inactivo</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
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
                  {editando ? 'Guardar cambios' : 'Crear usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
