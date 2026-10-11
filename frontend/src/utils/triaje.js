// Funciones puras del módulo de triaje. No dependen de React.

// Umbral con el que se marca hipertensión a partir de UNA lectura de presión.
const PRESION_SISTOLICA_ALTA = 140;
const PRESION_DIASTOLICA_ALTA = 90;

// Peso (kg) y altura (cm) -> IMC con un decimal. Devuelve null si faltan datos.
export const calcularIMC = (peso, altura) => {
  const p = parseFloat(peso);
  const a = parseFloat(altura) / 100;
  if (!p || !a || a <= 0) return null;
  return Number((p / (a * a)).toFixed(1));
};

// Prioridad de atención por reglas simples (no usa el modelo de ML).
export const calcularPrioridadAutomatica = (temp, fc) => {
  const temperatura = parseFloat(temp) || 0;
  const frecuencia = parseFloat(fc) || 0;

  if (temperatura > 38.5 || frecuencia > 110) {
    return { nivel: 'Alto (Urgencia)', color: 'bg-rose-100 text-rose-800' };
  }
  if (temperatura > 37.5 || frecuencia > 90) {
    return { nivel: 'Moderado (Urgencia Menor)', color: 'bg-amber-100 text-amber-800' };
  }
  return { nivel: 'Bajo (No Urgente)', color: 'bg-emerald-100 text-emerald-800' };
};

// "120/80" -> { sistolica: 120, diastolica: 80 }. Devuelve null si el formato no es válido.
export const parsePresion = (texto) => {
  const match = /^(\d{2,3})\s*\/\s*(\d{2,3})$/.exec(String(texto ?? '').trim());
  if (!match) return null;
  return { sistolica: Number(match[1]), diastolica: Number(match[2]) };
};

export const esPresionElevada = (texto) => {
  const presion = parsePresion(texto);
  if (!presion) return false;
  return (
    presion.sistolica >= PRESION_SISTOLICA_ALTA ||
    presion.diastolica >= PRESION_DIASTOLICA_ALTA
  );
};

// Edad en años -> categoría 1 a 13 del dataset BRFSS.
// 1 = 18-24, 2 = 25-29, ..., 12 = 75-79, 13 = 80 o más. Menores de 18 -> null.
export const edadACategoria = (edad) => {
  const e = Number(edad);
  if (!Number.isFinite(e) || e < 18) return null;
  if (e >= 80) return 13;
  if (e < 25) return 1;
  return Math.floor((e - 25) / 5) + 2;
};

// Fecha de nacimiento ("YYYY-MM-DD") -> edad en años. Null si falta o no es válida.
export const calcularEdad = (fechaNacimiento) => {
  if (!fechaNacimiento) return null;
  const nacimiento = new Date(`${fechaNacimiento}T00:00:00`);
  if (Number.isNaN(nacimiento.getTime())) return null;

  const hoy = new Date();
  let edad = hoy.getFullYear() - nacimiento.getFullYear();
  const yaCumplio =
    hoy.getMonth() > nacimiento.getMonth() ||
    (hoy.getMonth() === nacimiento.getMonth() && hoy.getDate() >= nacimiento.getDate());
  if (!yaCumplio) edad -= 1;
  return edad;
};

// Edad del paciente a partir de su fecha de nacimiento (formato del backend).
export const obtenerEdad = (paciente) =>
  calcularEdad(paciente?.fecha_nacimiento);

// Sexo del paciente tal como lo devuelve el backend ("M" | "F").
export const obtenerSexo = (paciente) => paciente?.sexo ?? null;

// Nombre completo en el formato del backend (apellidos, nombres).
export const nombreCompleto = (paciente) => {
  if (!paciente) return '';
  if (paciente.nombre_completo) return paciente.nombre_completo;
  const apellidos = [paciente.apellido_paterno, paciente.apellido_materno]
    .filter(Boolean)
    .join(' ');
  return `${apellidos}${apellidos && paciente.nombres ? ', ' : ''}${paciente.nombres ?? ''}`;
};

// "M" -> "Masculino", "F" -> "Femenino".
export const etiquetaSexo = (sexo) =>
  sexo === 'M' ? 'Masculino' : sexo === 'F' ? 'Femenino' : '—';

/**
 * Arma el payload EXACTO que espera POST /api/v1/evaluaciones/.
 * Son las 9 variables predictoras del modelo + paciente_id.
 *
 * `datos` es lo que captura el ModalTriaje (signos vitales + antecedentes).
 */
export const construirPayloadEvaluacion = (paciente, datos, edad) => ({
  paciente_id: paciente.id,
  edad: Number(edad),
  // Presión alta si ya tiene diagnóstico previo O si la lectura del triaje es elevada.
  presion_alta: Boolean(datos.hipertensionPrevia) || esPresionElevada(datos.presionArterial),
  colesterol_alto: Boolean(datos.colesterolAlto),
  tabaquismo: Boolean(datos.fuma),
  actividad_fisica: Boolean(datos.actividadFisica),
  antecedente_acv: Boolean(datos.derrame),
  // En el formulario 0 = No tiene, 1 = Prediabetes, 2 = Diabetes.
  diabetes: String(datos.diabetes) !== '0',
  salud_general: Number(datos.saludGeneral) || 3,
  dificultad_para_caminar: Boolean(datos.dificultadCaminar),
});

// Clases Tailwind por semáforo del triaje clínico.
export const clasesSemaforo = (codigoColor) => {
  switch (codigoColor) {
    case 'rojo':
      return {
        borde: 'border-rose-200',
        fondo: 'bg-rose-50',
        texto: 'text-rose-800',
        punto: 'bg-rose-500',
      };
    case 'amarillo':
      return {
        borde: 'border-amber-200',
        fondo: 'bg-amber-50',
        texto: 'text-amber-800',
        punto: 'bg-amber-500',
      };
    case 'verde':
      return {
        borde: 'border-emerald-200',
        fondo: 'bg-emerald-50',
        texto: 'text-emerald-800',
        punto: 'bg-emerald-500',
      };
    default:
      return {
        borde: 'border-slate-200',
        fondo: 'bg-slate-50',
        texto: 'text-slate-700',
        punto: 'bg-slate-400',
      };
  }
};

// Clases Tailwind por clasificación de riesgo del modelo.
export const clasesClasificacion = (clasificacion) => {
  switch (clasificacion) {
    case 'alto':
      return 'bg-rose-100 text-rose-800';
    case 'moderado':
      return 'bg-amber-100 text-amber-800';
    case 'bajo':
      return 'bg-emerald-100 text-emerald-800';
    default:
      return 'bg-slate-100 text-slate-600';
  }
};
