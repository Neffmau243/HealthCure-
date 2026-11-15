# Interfaz clínica

La actualización visual conserva la paleta celeste, azul oscuro y fondo cálido.
La interfaz está orientada al trabajo del personal de salud: tareas visibles,
información clínica legible y señales de urgencia diferenciadas del índice ML.

- `PageHeader` unifica título, explicación y acción de cada vista.
- La navegación se inicia cerrada en móvil. Su botón permanece en la barra
  superior y el contenido oculto no recibe foco.
- Los paneles usan borde simple, radios de 12–14 px y espaciado consistente.
- El directorio mantiene tablas con desplazamiento horizontal en pantallas pequeñas.
- Las atenciones separan contexto, alerta, diagnóstico, tratamiento e indicaciones.
- Los mensajes clínicos nombran el hallazgo y la acción. Los niveles, umbrales
  y decisiones de las reglas no se modifican con esta actualización.
- Mediciones, procedencia y alcance siguen disponibles en el detalle desplegable.
- El historial conserva el contenido clínico guardado; el título visual se presenta
  según su nivel registrado, sin recalcularlo.
- Los estados de foco, carga, error y campos deshabilitados se conservan. Se respeta
  la preferencia de movimiento reducido.

La hoja común está en `frontend/src/index.css`. No utiliza imágenes de pacientes
ni métricas de demostración como datos reales. La tipografía Lexend mantiene
la fuente ya utilizada en el proyecto.
