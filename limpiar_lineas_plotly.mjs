/** Quita líneas punteadas y títulos de ejes redundantes en las gráficas Plotly. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const WIDGET = /<div class="plotly html-widget[^\"]*" id="([^\"]+)"[^>]*><\/div>\s*<script type="application\/json" data-for="\1">[\s\S]*?<\/script>/g;
const DATOS = /(<script type="application\/json" data-for="[^"]+">)([\s\S]*?)(<\/script>)/;

export function limpiarWidgetPlotly(fragmento) {
  const match = DATOS.exec(fragmento);
  if (!match) throw new Error('No se encontraron los datos JSON de la gráfica Plotly.');
  const grafica = JSON.parse(match[2]);
  const series = grafica?.x?.data;
  if (!Array.isArray(series)) throw new Error('La gráfica Plotly no contiene una lista de series.');
  grafica.x.data = series.filter(serie => !serie.line?.dash || serie.line.dash === 'solid');
  const quitadas = series.length - grafica.x.data.length;
  if (quitadas !== 0 && quitadas !== 6) {
    throw new Error(`La gráfica contiene ${quitadas} líneas punteadas; se esperaban 0 o 6.`);
  }
  let titulosQuitados = 0;
  for (const [nombre, eje] of Object.entries(grafica.x.layout ?? {})) {
    if (/^[xy]axis\d*$/.test(nombre) && eje?.title?.text) {
      delete eje.title;
      titulosQuitados++;
    }
  }
  if (quitadas === 0 && titulosQuitados === 0) return {html:fragmento, quitadas, titulosQuitados};
  return {
    html:fragmento.replace(match[0], match[1] + JSON.stringify(grafica) + match[3]),
    quitadas,
    titulosQuitados,
  };
}

export function limpiarTresGraficas(html) {
  let cantidad = 0;
  let quitadas = 0;
  const resultado = html.replace(WIDGET, fragmento => {
    cantidad++;
    const limpio = limpiarWidgetPlotly(fragmento);
    quitadas += limpio.quitadas;
    return limpio.html;
  });
  if (cantidad !== 3) throw new Error(`Se esperaban tres gráficas Plotly; se encontraron ${cantidad}.`);
  return {html:resultado, quitadas};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [entrada, salida] = process.argv.slice(2).map(archivo => path.resolve(archivo));
  if (!entrada || !salida || entrada === salida) {
    throw new Error('Uso: node limpiar_lineas_plotly.mjs ENTRADA.html SALIDA.html (archivos distintos)');
  }
  if (!fs.existsSync(entrada)) throw new Error(`No existe el archivo de entrada: ${entrada}`);
  if (fs.existsSync(salida)) throw new Error(`La salida ya existe: ${salida}`);
  const resultado = limpiarTresGraficas(fs.readFileSync(entrada, 'utf8'));
  fs.writeFileSync(salida, resultado.html, 'utf8');
  console.log(`Generado: ${salida}. Líneas punteadas quitadas: ${resultado.quitadas}.`);
}
