
export default function Tabla({ columnas, datos, caption, mensajeVacio = "No se encontraron registros." }) {
  return (
    <div className="clinical-table">
      {caption && <p className="clinical-table-caption">{caption} · {datos.length} {datos.length === 1 ? 'registro' : 'registros'}</p>}
      <div className="w-full overflow-x-auto">
        {/* Los roles conservan la semántica al presentar las filas como fichas en móvil. */}
        <table role="table" className="w-full text-left border-collapse min-w-[700px]">
          <caption className="sr-only">{caption ?? 'Listado de registros'}</caption>
          <thead role="rowgroup">
            <tr role="row" className="bg-slate-50/70 border-b border-slate-100 text-slate-600 text-xs uppercase tracking-wider font-semibold">
              {columnas.map((col, index) => (
                <th role="columnheader" scope="col" key={index} className={`p-4 ${index === 0 ? 'pl-6' : ''} ${col.align === 'center' ? 'text-center' : ''}`}>
                  {col.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody role="rowgroup" className="divide-y divide-slate-100 text-sm">
            {datos.length > 0 ? (
              datos.map((fila, rowIndex) => (
                <tr role="row" key={fila.id || rowIndex} className="hover:bg-slate-50/50 transition">
                  {columnas.map((col, colIndex) => (
                    <td role="cell" key={colIndex} className={`p-4 ${colIndex === 0 ? 'pl-6' : ''} ${col.align === 'center' ? 'text-center clinical-table-actions' : ''}`}>
                      <span className="clinical-cell-label" aria-hidden="true">{col.titulo}</span>
                      <div className="clinical-cell-value">{col.render ? col.render(fila) : fila[col.campo]}</div>
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr role="row">
                <td role="cell" colSpan={columnas.length} className="clinical-table-empty p-8 text-center text-slate-400">
                  {mensajeVacio}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
