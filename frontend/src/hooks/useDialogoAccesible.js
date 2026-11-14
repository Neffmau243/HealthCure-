import { useEffect, useRef } from 'react';

/**
 * Comportamiento de DIÁLOGO ACCESIBLE, compartido por los modales.
 *
 * Comportamiento compartido:
 *   1. Bloquea el scroll del fondo mientras el modal está abierto.
 *   2. Lleva el foco adentro al abrir (antes quedaba en <body>, detrás del
 *      overlay, así que el teclado no entraba al formulario).
 *   3. Cierra con la tecla Escape (nunca si hay una operación en curso).
 *   4. Cierra al hacer clic en el fondo.
 *   5. Mantiene el recorrido de Tab dentro y restaura el foco al cerrar.
 *
 * USO:
 *   const { propsContenedor, alClicFondo } = useDialogoAccesible({
 *     abierto: isOpen, onClose, ocupado: guardando,
 *   });
 *
 *   <div className="fixed inset-0 ..." onClick={alClicFondo}>
 *     <div {...propsContenedor} aria-labelledby="titulo-del-modal"
 *          onClick={(e) => e.stopPropagation()}>
 *       ...
 *     </div>
 *   </div>
 *
 * `propsContenedor` trae `ref`, `role="dialog"` y `aria-modal="true"`.
 */
export function useDialogoAccesible({ abierto = true, onClose, ocupado = false }) {
  const refContenedor = useRef(null);

  // Refs "always-latest" para que el efecto no tenga que depender de props
  // que cambian de identidad en cada render (y se actualicen en un efecto,
  // no durante el render).
  const ocupadoRef = useRef(ocupado);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    ocupadoRef.current = ocupado;
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!abierto) return undefined;

    const overflowPrevio = document.body.style.overflow;
    const focoPrevio = document.activeElement;
    document.body.style.overflow = 'hidden';
    const enfocables = () => [...(refContenedor.current?.querySelectorAll(
      'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]'
    ) ?? [])].filter((elemento) => elemento.getClientRects().length > 0 && !elemento.closest('[inert]'));
    (enfocables()[0] ?? refContenedor.current)?.focus();

    const alPresionar = (evento) => {
      if (evento.key === 'Escape' && !ocupadoRef.current) onCloseRef.current?.();
      if (evento.key !== 'Tab') return;
      const elementos = enfocables();
      const primero = elementos[0];
      const ultimo = elementos.at(-1);
      if (!primero) {
        evento.preventDefault();
        refContenedor.current?.focus();
      } else if (evento.shiftKey && (document.activeElement === primero || document.activeElement === refContenedor.current)) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primero.focus();
      }
    };
    document.addEventListener('keydown', alPresionar);

    return () => {
      document.body.style.overflow = overflowPrevio;
      document.removeEventListener('keydown', alPresionar);
      if (focoPrevio?.isConnected && !focoPrevio.closest('[inert]')) focoPrevio.focus();
    };
  }, [abierto]);

  const alClicFondo = () => {
    if (!ocupadoRef.current) onCloseRef.current?.();
  };

  return {
    refContenedor,
    propsContenedor: { ref: refContenedor, role: 'dialog', 'aria-modal': 'true', tabIndex: -1 },
    alClicFondo,
  };
}
