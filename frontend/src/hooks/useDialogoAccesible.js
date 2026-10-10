import { useEffect, useRef } from 'react';

/**
 * Comportamiento de DIÁLOGO ACCESIBLE, compartido por los modales.
 *
 * Resuelve cuatro cosas que antes no pasaban en ninguno de ellos:
 *   1. Bloquea el scroll del fondo mientras el modal está abierto.
 *   2. Lleva el foco adentro al abrir (antes quedaba en <body>, detrás del
 *      overlay, así que el teclado no entraba al formulario).
 *   3. Cierra con la tecla Escape (nunca si hay una operación en curso).
 *   4. Cierra al hacer clic en el fondo.
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
    document.body.style.overflow = 'hidden';
    refContenedor.current?.querySelector('input, select, textarea, button')?.focus();

    const alPresionar = (evento) => {
      if (evento.key === 'Escape' && !ocupadoRef.current) onCloseRef.current?.();
    };
    document.addEventListener('keydown', alPresionar);

    return () => {
      document.body.style.overflow = overflowPrevio;
      document.removeEventListener('keydown', alPresionar);
    };
  }, [abierto]);

  const alClicFondo = () => {
    if (!ocupadoRef.current) onCloseRef.current?.();
  };

  return {
    refContenedor,
    propsContenedor: { ref: refContenedor, role: 'dialog', 'aria-modal': 'true' },
    alClicFondo,
  };
}
