import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

function option(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`Falta ${name}`);
  return process.argv[index + 1];
}

const basePath = option('--excel-incidencia');
const dataPath = option('--datos-inhumacion');
const outputPath = option('--salida');
const data = JSON.parse(await fs.readFile(dataPath, 'utf8'));
if (!/^\d{4}-\d{2}-01$/.test(data.corte)) throw new Error('Corte inválido');
if (!Array.isArray(data.mensual) || !data.mensual.length || !Array.isArray(data.detalle) || !data.detalle.length) {
  throw new Error('Faltan las filas mensuales o detalladas de inhumación');
}
if (data.mensual.some(row => row.length !== 3) || data.detalle.some(row => row.length !== 9)) {
  throw new Error('El número de columnas de inhumación no coincide con la plantilla');
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(basePath));
for (const name of ['Inhumación mensual', 'Inhumación detalle']) {
  if (workbook.worksheets.items.some(sheet => sheet.name === name)) {
    throw new Error(`El Excel de incidencia ya tiene la hoja ${name}`);
  }
}
const [year, month] = data.corte.split('-').map(Number);
const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
const monthName = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][month - 1];
const sourceUrl = 'https://fiscaliaenpersonasdesaparecidas.jalisco.gob.mx/registro-estatal-de-fosas-clandestinas/';
const font = 'Arial';
const fill = '#303040';
const stripe = '#F3F3F5';

const summary = workbook.worksheets.add('Inhumación mensual');
summary.showGridLines = false;
summary.getRange('A1').values = [[`Sitios de inhumación clandestina registrados en Jalisco, al corte del ${lastDay} de ${monthName} de ${year}`]];
summary.mergeCells('A1:C2');
summary.getRange('A1:C2').format = {font:{name:font,size:14,bold:true,color:'#111111'},wrapText:true,verticalAlignment:'center'};
summary.getRange('A1:C2').format.rowHeight = 30;
summary.getRange('A4:C4').values = [[
  'Mes de inicio de procesamiento','Número de sitios registrados','Total preliminar de víctimas localizadas'
]];
const summaryLast = data.mensual.length + 4;
summary.getRange(`A5:C${summaryLast}`).values = data.mensual;
summary.getRange(`A4:C4`).format = {fill,font:{name:font,size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
summary.getRange('A4:C4').format.rowHeight = 54;
summary.getRange(`A5:C${summaryLast}`).format.font = {name:font,size:10,color:'#111111'};
summary.getRange(`B5:C${summaryLast}`).setNumberFormat('#,##0');
for (let row = 5; row <= summaryLast; row += 2) summary.getRange(`A${row}:C${row}`).format.fill = stripe;
summary.getRange('A1:A100').format.columnWidth = 24;
summary.getRange('B1:B100').format.columnWidth = 30;
summary.getRange('C1:C100').format.columnWidth = 34;
summary.freezePanes.freezeRows(4);

const detail = workbook.worksheets.add('Inhumación detalle');
detail.showGridLines = false;
detail.getRange('A1').values = [['Tabla detallada de sitios de inhumación clandestina en Jalisco']];
detail.getRange('A1:I1').format.font = {name:font,size:14,bold:true,color:'#111111'};
detail.getRange('A2').values = [[`Fuente oficial: ${sourceUrl}`]];
detail.getRange('A2:I2').format.font = {name:font,size:9,italic:true,color:'#555555'};
detail.getRange('A4:I4').values = [[
  'Registro','Denominación','Municipio','Fecha inicio de procesamiento',
  'Fecha fin de procesamiento','Total preliminar de víctimas localizadas',
  'Total preliminar de víctimas identificadas','Hombres preliminarmente identificados',
  'Mujeres preliminarmente identificadas'
]];
const detailLast = data.detalle.length + 4;
detail.getRange(`A5:I${detailLast}`).values = data.detalle;
detail.getRange('A4:I4').format = {fill,font:{name:font,size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
detail.getRange('A4:I4').format.rowHeight = 46;
detail.getRange(`A5:I${detailLast}`).format.font = {name:font,size:10,color:'#111111'};
detail.getRange(`B5:C${detailLast}`).format.wrapText = true;
for (let row = 5; row <= detailLast; row += 2) detail.getRange(`A${row}:I${row}`).format.fill = stripe;
detail.getRange(`A1:A${detailLast}`).format.columnWidth = 13;
detail.getRange(`B1:B${detailLast}`).format.columnWidth = 42;
detail.getRange(`C1:C${detailLast}`).format.columnWidth = 28;
detail.getRange(`D1:E${detailLast}`).format.columnWidth = 19;
detail.getRange(`F1:I${detailLast}`).format.columnWidth = 22;
detail.freezePanes.freezeRows(4);

workbook.recalculate();
const preview = await workbook.render({sheetName:'Inhumación mensual',range:'A1:C8',scale:1,format:'png'});
if (process.argv.includes('--vista-previa')) {
  await fs.writeFile(path.join(path.dirname(outputPath), 'vista_previa_inhumacion.png'),new Uint8Array(await preview.arrayBuffer()));
  const detailPreview = await workbook.render({sheetName:'Inhumación detalle',range:'A1:I7',scale:1,format:'png'});
  await fs.writeFile(path.join(path.dirname(outputPath), 'vista_previa_detalle.png'),new Uint8Array(await detailPreview.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath),{recursive:true});
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`Excel combinado: ${outputPath}`);
