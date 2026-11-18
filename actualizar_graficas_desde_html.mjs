/** Copia gráficas y cifras de la tabla de 16 delitos de un HTML mensual nuevo. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {limpiarWidgetPlotly} from './limpiar_lineas_plotly.mjs';
import {normalizarWidgetMapa} from './normalizar_mapa_leaflet.mjs';

const CARPETA = path.dirname(fileURLToPath(import.meta.url));
const PLANTILLA = path.join(CARPETA, 'reporte_mensual_con_tabla.html');
const SALIDA = path.join(CARPETA, 'reporte_mensual_con_graficas_nuevas.html');
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MESES_INGLES = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
const FECHA_CORTE = /Corte de información al\s*<strong>(\d{1,2})<\/strong>\s*de\s*<strong>([A-Za-zÁÉÍÓÚáéíóú]+)<\/strong>\s*de\s*<strong>(\d{4})<\/strong>/gi;

const GRAFICAS = [
  {nombre:'Incidencia total', tipo:'plotly', origen:/^(Incidencia delictiva total|Carpetas de investigación iniciadas de 16 tipos)/, destino:/^Carpetas de investigación iniciadas de 16 tipos/},
  {nombre:'Homicidios: eventos', tipo:'plotly', origen:/^(Homicidios dolosos - eventos|Carpetas de investigación iniciadas por el delito de homicidio doloso)/, destino:/^Carpetas de investigación iniciadas por el delito de homicidio doloso/},
  {nombre:'Homicidios: víctimas', tipo:'plotly', origen:/^(Homicidios dolosos - víctimas|Víctimas de homicidios dolosos)/, destino:/^Víctimas de homicidios dolosos/},
  {nombre:'Delitos patrimoniales', tipo:'imagen', origen:/^(Comportamiento de delitos patrimoniales|Carpetas de investigación de delitos patrimoniales seleccionados, [a-záéíóú]+ de \d{4})$/, destino:/^Carpetas de investigación de delitos patrimoniales seleccionados, [a-záéíóú]+ de \d{4}$/},
  {nombre:'Patrimoniales por zona', tipo:'imagen', origen:/^(Comparativa de delitos patrimoniales por zona geográfica|Carpetas de investigación de delitos patrimoniales seleccionados por zona geográfica)/, destino:/^Carpetas de investigación de delitos patrimoniales seleccionados por zona geográfica/},
  {nombre:'Patrimoniales por violencia', tipo:'imagen', origen:/^(Comparativa de delitos patrimoniales por tipo de violencia|Carpetas de investigación de delitos patrimoniales seleccionados, según modalidad)/, destino:/^Carpetas de investigación de delitos patrimoniales seleccionados, según modalidad/},
  {nombre:'Delitos contra la vida', tipo:'imagen', origen:/^(Comportamiento de delitos contra la vida|Carpetas de investigación por delitos contra la vida seleccionados)/, destino:/^Carpetas de investigación por delitos contra la vida seleccionados/},
  {nombre:'Vida por zona', tipo:'imagen', origen:/^(Comparativa de delitos contra la vida en tasas por zona geográfica|Tasa de carpetas de investigación de delitos contra la vida seleccionados)/, destino:/^Tasa de carpetas de investigación de delitos contra la vida seleccionados/},
  {nombre:'Mapa municipal', tipo:'leaflet', origen:/^(Mapa de tasas delictivas por delito|Mapa de tasa de carpetas de investigación de los 16 delitos seleccionados)/, destino:/^Mapa de tasa de carpetas de investigación de los 16 delitos seleccionados/},
];

function argumentos(argv) {
  const options = {plantilla:PLANTILLA, salida:SALIDA, reemplazar:false};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (key === '--reemplazar') { options.reemplazar = true; continue; }
    if (!['--nuevo', '--plantilla', '--salida'].includes(key) || !argv[i + 1]) {
      throw new Error(`Argumento desconocido o incompleto: ${key}`);
    }
    options[key.slice(2)] = path.resolve(argv[++i]);
  }
  if (!options.nuevo) throw new Error('Uso: node actualizar_graficas_desde_html.mjs --nuevo NUEVO.html [--salida BORRADOR.html]');
  for (const key of ['nuevo', 'plantilla']) {
    if (!fs.existsSync(options[key])) throw new Error(`No existe ${key}: ${options[key]}`);
  }
  if (options.salida === options.plantilla || options.salida === options.nuevo) {
    throw new Error('La salida debe ser otro archivo: no se sobrescriben los originales.');
  }
  if (fs.existsSync(options.salida) && !options.reemplazar) {
    throw new Error(`La salida ya existe: ${options.salida}. Usa --reemplazar solo tras revisarla.`);
  }
  return options;
}

function secciones(html) {
  const headings = [...html.matchAll(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi)];
  return headings.map((m, i) => ({
    titulo: m[2].replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim(),
    inicio: m.index,
    fin: headings[i + 1]?.index ?? html.length,
    cuerpo: html.slice(m.index, headings[i + 1]?.index ?? html.length),
  }));
}

function unica(lista, patron, etiqueta) {
  const resultado = lista.filter(s => patron.test(s.titulo));
  if (resultado.length !== 1) throw new Error(`Se esperaba una sección ${etiqueta}; se encontraron ${resultado.length}.`);
  return resultado[0];
}

function visual(seccion, tipo) {
  let patron;
  if (tipo === 'imagen') {
    patron = /<img\b[^>]*\bsrc="(data:image\/[^\"]+)"[^>]*>/gi;
  } else {
    patron = new RegExp(`<div class="${tipo} html-widget[^\"]*" id="([^\"]+)"[^>]*><\\/div>\\s*<script type="application\\/json" data-for="\\1">[\\s\\S]*?<\\/script>`, 'gi');
  }
  const encontrados = [...seccion.cuerpo.matchAll(patron)];
  if (encontrados.length !== 1 && !(tipo === 'imagen' && encontrados.length === 2 && seccion.titulo.includes('violencia'))) {
    throw new Error(`La sección «${seccion.titulo}» tiene ${encontrados.length} gráficos ${tipo}; se esperaba uno.`);
  }
  const m = encontrados[0];
  if (tipo === 'imagen') {
    const srcPos = m[0].indexOf(m[1]);
    return {inicio:seccion.inicio + m.index + srcPos, fin:seccion.inicio + m.index + srcPos + m[1].length, contenido:m[1]};
  }
  return {inicio:seccion.inicio + m.index, fin:seccion.inicio + m.index + m[0].length, contenido:m[0]};
}

function fechaCorte(html, etiqueta) {
  const fechas = [...html.matchAll(FECHA_CORTE)];
  if (fechas.length !== 1) throw new Error(`Se esperaba una fecha de corte en ${etiqueta}; encontradas: ${fechas.length}.`);
  const [, diaTexto, mesTexto, anioTexto] = fechas[0];
  const mes = mesTexto.toLocaleLowerCase('es-MX');
  let indice = MESES.indexOf(mes);
  if (indice < 0) indice = MESES_INGLES.indexOf(mes);
  if (indice < 0) throw new Error(`Mes no reconocido en ${etiqueta}: ${mesTexto}`);
  const dia = Number(diaTexto);
  const anio = Number(anioTexto);
  if (dia < 1 || dia > new Date(Date.UTC(anio, indice + 1, 0)).getUTCDate()) {
    throw new Error(`Día de corte no válido en ${etiqueta}: ${dia} de ${mesTexto} de ${anio}`);
  }
  return {dia, mes:MESES[indice], anio};
}

function primeraTabla(html, patron, etiqueta) {
  const seccion = unica(secciones(html), patron, etiqueta);
  const match = /<table\b[^>]*>[\s\S]*?<\/table>/i.exec(seccion.cuerpo);
  if (!match) throw new Error(`No se encontró la tabla de ${etiqueta}.`);
  return {inicio:seccion.inicio + match.index, fin:seccion.inicio + match.index + match[0].length, html:match[0]};
}

function celdas(row) {
  return [...row.matchAll(/(<td\b[^>]*>)([\s\S]*?)(<\/td>)/gi)];
}

function nombreDelito(celda) {
  return celda.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace('Robo a int de vehiculos', 'Robo a interior de vehiculos');
}

function datosDelitos(tabla) {
  const tbody = /<tbody>([\s\S]*?)<\/tbody>/i.exec(tabla);
  if (!tbody) throw new Error('La tabla de delitos no tiene cuerpo.');
  const filas = new Map();
  for (const row of tbody[1].matchAll(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi)) {
    const cells = celdas(row[0]);
    if (cells.length === 1) continue; // Fila de grupo: bien jurídico afectado.
    if (cells.length !== 7) throw new Error(`Una fila de delitos tiene ${cells.length} celdas; se esperaban 7.`);
    const nombre = nombreDelito(cells[0][2]);
    if (filas.has(nombre)) throw new Error(`Delito duplicado en la tabla: ${nombre}`);
    filas.set(nombre, cells.slice(1).map(c => c[2]));
  }
  if (filas.size !== 16) throw new Error(`Se esperaban 16 delitos; se encontraron ${filas.size}.`);
  return filas;
}

function actualizarTablaDelitos(nuevo, resultado, fechaNueva) {
  const fuente = primeraTabla(nuevo,
    /^(Promedio mensual de delitos|Carpetas de investigación de 16 tipos de delitos, promedio mensual)/,
    'delitos del HTML nuevo');
  const objetivo = primeraTabla(resultado,
    /^Carpetas de investigación de 16 tipos de delitos, promedio mensual/,
    'delitos de la plantilla');
  const mesFuente = MESES_INGLES[MESES.indexOf(fechaNueva.mes)];
  const encabezadoFuente = fuente.html.slice(0, fuente.html.indexOf('<tbody>')).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
  if (!encabezadoFuente.toLocaleLowerCase('es-MX').includes(`${mesFuente} ${fechaNueva.anio}`) &&
      !encabezadoFuente.toLocaleLowerCase('es-MX').includes(`${fechaNueva.mes} de ${fechaNueva.anio}`)) {
    throw new Error('El mes de la tabla de delitos no coincide con la fecha de corte del HTML nuevo.');
  }
  const datos = datosDelitos(fuente.html);
  const usados = new Set();
  let filasActualizadas = 0;
  let tablaNueva = objetivo.html.replace(/<tbody>([\s\S]*?)<\/tbody>/i, (todo, cuerpo) => {
    const actualizado = cuerpo.replace(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi, row => {
      const cells = celdas(row);
      if (cells.length === 1) return row;
      if (cells.length !== 7) throw new Error('La plantilla tiene una fila de delitos con número inesperado de celdas.');
      const nombre = nombreDelito(cells[0][2]);
      const valores = datos.get(nombre);
      if (!valores) throw new Error(`El HTML nuevo no contiene el delito de la plantilla: ${nombre}`);
      usados.add(nombre);
      filasActualizadas++;
      let indice = 0;
      return row.replace(/(<td\b[^>]*>)([\s\S]*?)(<\/td>)/gi, (todo, apertura, contenido, cierre) => {
        const i = indice++;
        return apertura + (i === 0 ? contenido : valores[i - 1]) + cierre;
      });
    });
    return `<tbody>${actualizado}</tbody>`;
  });
  if (filasActualizadas !== 16 || usados.size !== datos.size) {
    throw new Error('Las 16 filas de delitos del HTML nuevo y la plantilla no coinciden.');
  }
  const titulos = [...tablaNueva.matchAll(/Cifras de ([a-záéíóú]+) de (\d{4})/gi)];
  if (titulos.length !== 1) throw new Error('No se encontró un único encabezado de cifras en la tabla de delitos.');
  const tituloAnterior = titulos[0][0];
  const tituloNuevo = `Cifras de ${fechaNueva.mes} de ${fechaNueva.anio}`;
  tablaNueva = tablaNueva.replace(tituloAnterior, tituloNuevo);
  return {html:resultado.slice(0, objetivo.inicio) + tablaNueva + resultado.slice(objetivo.fin), filas:filasActualizadas};
}

function actualizar(nuevo, plantilla) {
  const fechaNueva = fechaCorte(nuevo, 'el HTML nuevo');
  const fechaAnterior = fechaCorte(plantilla, 'la plantilla');
  const origen = secciones(nuevo);
  const destino = secciones(plantilla);
  const protegida = unica(destino, /^Sitios de inhumación clandestina registrados en Jalisco/, 'de inhumación');
  let lineasQuitadas = 0;
  const cambios = GRAFICAS.map(item => {
    const fuente = visual(unica(origen, item.origen, `de origen: ${item.nombre}`), item.tipo);
    const objetivo = visual(unica(destino, item.destino, `de plantilla: ${item.nombre}`), item.tipo);
    if (objetivo.inicio >= protegida.inicio && objetivo.inicio < protegida.fin) {
      throw new Error('Una gráfica apunta accidentalmente a la tabla de inhumación.');
    }
    const limpio = item.tipo === 'plotly'
      ? limpiarWidgetPlotly(fuente.contenido)
      : {html:item.tipo === 'leaflet' ? normalizarWidgetMapa(fuente.contenido) : fuente.contenido, quitadas:0};
    lineasQuitadas += limpio.quitadas;
    return {nombre:item.nombre, ...objetivo, nuevo:limpio.html};
  });
  cambios.sort((a,b) => b.inicio - a.inicio);
  let resultado = plantilla;
  for (const cambio of cambios) {
    resultado = resultado.slice(0, cambio.inicio) + cambio.nuevo + resultado.slice(cambio.fin);
  }
  const anteriorCompleta = `${fechaAnterior.dia} de ${fechaAnterior.mes} de ${fechaAnterior.anio}`;
  const nuevaCompleta = `${fechaNueva.dia} de ${fechaNueva.mes} de ${fechaNueva.anio}`;
  const anteriorMes = `${fechaAnterior.mes} de ${fechaAnterior.anio}`;
  const nuevaMes = `${fechaNueva.mes} de ${fechaNueva.anio}`;
  const seccionesResultado = secciones(resultado);
  const fechasEnGraficas = GRAFICAS.map(item => unica(seccionesResultado, item.destino, `para fecha: ${item.nombre}`))
    .sort((a,b) => b.inicio - a.inicio);
  let fechasActualizadas = 0;
  for (const seccion of fechasEnGraficas) {
    const actualizada = seccion.cuerpo.split(/(<script\b[^>]*>[\s\S]*?<\/script>)/gi)
      .map((parte, i) => i % 2 ? parte : parte.replaceAll(anteriorCompleta, nuevaCompleta)
        .replaceAll(anteriorMes, nuevaMes)).join('');
    if (actualizada !== seccion.cuerpo) fechasActualizadas++;
    resultado = resultado.slice(0, seccion.inicio) + actualizada + resultado.slice(seccion.fin);
  }
  if (fechaNueva.dia !== fechaAnterior.dia || nuevaMes !== anteriorMes) {
    const corteAnterior = `<strong>${fechaAnterior.dia}</strong> de <strong>${fechaAnterior.mes}</strong> de <strong>${fechaAnterior.anio}</strong>`;
    const corteNuevo = `<strong>${fechaNueva.dia}</strong> de <strong>${fechaNueva.mes}</strong> de <strong>${fechaNueva.anio}</strong>`;
    if (resultado.split(corteAnterior).length - 1 !== 1) throw new Error('No se encontró una única fecha antigua en la introducción.');
    resultado = resultado.replace(corteAnterior, corteNuevo);
  }
  const tablaDelitos = actualizarTablaDelitos(nuevo, resultado, fechaNueva);
  resultado = tablaDelitos.html;
  const final = unica(secciones(resultado), /^Sitios de inhumación clandestina registrados en Jalisco/, 'de inhumación resultante');
  if (final.cuerpo !== protegida.cuerpo) throw new Error('Cambió la sección de inhumación; no se guardó nada.');
  return {html:resultado, nombres:cambios.map(c => c.nombre), fecha:nuevaCompleta, fechasActualizadas, lineasQuitadas, delitos:tablaDelitos.filas};
}

const args = argumentos(process.argv.slice(2));
const nuevo = fs.readFileSync(args.nuevo, 'utf8');
const plantilla = fs.readFileSync(args.plantilla, 'utf8');
const result = actualizar(nuevo, plantilla);
fs.writeFileSync(args.salida, result.html, 'utf8');
console.log(`Borrador generado: ${args.salida}`);
console.log(`Gráficas actualizadas: ${result.nombres.length} (${result.nombres.join(', ')}).`);
console.log(`Líneas punteadas eliminadas de Plotly: ${result.lineasQuitadas}.`);
console.log(`Fecha de incidencia: ${result.fecha}; se actualizó la introducción y ${result.fechasActualizadas} secciones de gráficas.`);
console.log(`Tabla de 16 delitos: ${result.delitos} filas actualizadas con sus valores e indicadores.`);
console.log('Se conservaron la tabla de inhumación y el enlace de descarga de la plantilla.');
console.log('Revisa el corte de inhumación y el Excel descargable antes de publicar: NO se actualizan con este programa.');
