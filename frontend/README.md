# HealthCure — Frontend (React + Vite)

Interfaz del sistema de triaje cardíaco. Consume la API del backend FastAPI
(`/api/v1`). No usa datos mock: todo viene de la API.

## Levantar

```bash
npm install
npm run dev        # http://localhost:5173
```

Requiere el backend corriendo en `http://localhost:8000`:

```bash
# desde la raíz del repo
uvicorn main:app --reload --port 8000
```

## Configuración

La URL del backend se define con `VITE_API_URL` (por defecto
`http://localhost:8000/api/v1`). Copia la plantilla:

```bash
cp .env.example .env
```

## Cuentas de prueba (seed del backend)

| Rol | Email | Password |
|-----|-------|----------|
| Admin | `admin@healthcure.com` | `admin123` |
| Personal de salud | `dr.garcia@healthcure.com` | `doctor123` |
| Personal de salud | `ana.martinez@healthcure.com` | `enfermera123` |

## Scripts

```bash
npm run dev      # servidor de desarrollo con HMR
npm run build    # build de producción a dist/
npm run lint     # ESLint
npm run preview  # sirve el build
```

## Estructura

```
src/
├── components/
│   ├── layout/     Sidebar, Topbar
│   ├── pacientes/  ModalPaciente
│   ├── triaje/     ModalTriaje, TarjetaTriaje
│   └── ui/         Tabla, Feedback (carga/error/vacío)
├── constants/      roles y matriz de permisos
├── context/        AuthContext (provider) + useAuth (hook)
├── layouts/        DashboardLayout
├── pages/          Login, Dashboard, Pacientes, Triaje,
│                   HistoriasClinicas, Consultorio, Atenciones, Usuarios
├── routes/         AppRouter, ProtectedRoute
├── services/       api (axios) + un módulo por recurso
└── utils/          triaje (IMC, prioridad, payload del modelo)
```

## Rutas

| Ruta | Descripción |
|------|-------------|
| `/login` | Inicio de sesión (JWT) |
| `/dashboard` | Métricas y últimas evaluaciones |
| `/dashboard/pacientes` | Directorio, alta y edición de pacientes |
| `/dashboard/triaje` | Registro de triaje y evaluación ML |
| `/dashboard/historiales` | Expediente del paciente (evaluaciones, atenciones, FUA) |
| `/dashboard/consultorio` | Resultado del modelo, atención y FUA |
| `/dashboard/atenciones` | Historial general de atenciones |
| `/dashboard/usuarios` | Gestión de usuarios (solo admin) |

Documentación de la integración: [`../docs/MAPEO_RUTAS_FRONT_BACK.md`](../docs/MAPEO_RUTAS_FRONT_BACK.md).
