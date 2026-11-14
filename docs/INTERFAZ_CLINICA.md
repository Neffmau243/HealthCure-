# Interfaz clínica

La actualización visual conserva la paleta celeste, azul oscuro y fondo cálido.
El celeste suave del menú permite concentrar la atención en el contenido y la
selección activa. El panel inicial y los indicadores usan una jerarquía compacta.
La interfaz está orientada al registro administrativo del personal: pacientes,
categorías por visita, datos del FUA e índice cardiovascular del modelo.

- `PageHeader` unifica título, explicación y acción de cada vista.
- La navegación se inicia cerrada en móvil. Su botón permanece en la barra
  superior y el contenido oculto no recibe foco. Los módulos son enlaces reales.
  El menú móvil mantiene el foco dentro, se cierra con Escape y devuelve el foco
  al botón de apertura; el contenido del fondo queda inerte mientras está abierto.
- Los paneles usan borde simple, radios de 12–14 px y espaciado consistente.
- Las tablas compartidas de pacientes, triaje y usuarios se presentan como fichas
  con etiquetas y acciones visibles en móvil, conservando la semántica de tabla.
  El detalle analítico mantiene sus columnas comparables y permite desplazarse
  con teclado, con una indicación de desplazamiento en móvil.
- Los indicadores de reportes comparten una franja y mantienen sus valores
  alineados. El selector de periodo usa botones con estado presionado accesible.
  La tendencia sin registros explica su estado en lugar de mostrar ejes vacíos.
- Las atenciones separan contexto, diagnóstico, tratamiento e indicaciones.
- El historial conserva el contexto y los datos guardados en cada visita.
- Los estados de foco, carga, error y campos deshabilitados se conservan. Se respeta
  la preferencia de movimiento reducido.
- Los diálogos mantienen el foco dentro y lo devuelven al control de apertura.
  El acceso permite mostrar u ocultar la contraseña y la página declara su idioma
  español. Los campos de móvil usan 16 px para evitar zoom al escribir.
- Registro, Triaje y Consultorio comparten la categoría General / Gestante /
  Puérpera, con los datos específicos del FUA según la selección. Consultorio
  prioriza la atención: el formulario aparece al elegir paciente, el ML es una
  referencia opcional desplegable y la confirmación permite descargar el FUA.
- Triaje mantiene a la vista los datos utilizados por el modelo; peso, talla,
  presión sistólica/diastólica, atención (ambulatoria, referencia o emergencia)
  y lugar (intramural o extramural) para el FUA se encuentran en un desplegable
  opcional. Consultorio registra esos mismos datos antes de emitir el FUA. Los
  campos antiguos que no se usaban ni se guardaban fueron retirados.
  Para sexo masculino, General se muestra como contexto de lectura con la razón
  por la que no se ofrecen las categorías maternas.
- Este flujo no solicita valoración pediátrica, obstétrica, revisión de síntomas
  ni decisiones de urgencia. No consulta `/clinica/revisar`. Las tarjetas y los
  reportes de pantalla muestran el índice ML y los datos administrativos; la
  evaluación asistencial corresponde al área encargada.

La hoja común está en `frontend/src/index.css`. No utiliza imágenes de pacientes
ni métricas de demostración como datos reales. La tipografía Lexend mantiene
la fuente ya utilizada en el proyecto.
