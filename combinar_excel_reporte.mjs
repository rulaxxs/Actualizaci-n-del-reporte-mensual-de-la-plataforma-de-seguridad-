import fs from 'node:fs/promises';
import path from 'node:path';
const { FileBlob, SpreadsheetFile } = await import(process.env.CODEX_ARTIFACT_MODULE || '@oai/artifact-tool');

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
if (!Array.isArray(data.mensual) || !data.mensual.length) {
  throw new Error('Faltan las filas mensuales de inhumación');
}
if (data.mensual.some(row => row.length !== 3)) {
  throw new Error('El número de columnas de inhumación no coincide con la plantilla');
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(basePath));
for (const name of ['Sitios de inhumación', 'Inhumación mensual', 'Inhumación detalle']) {
  if (workbook.worksheets.items.some(sheet => sheet.name === name)) {
    throw new Error(`El Excel de incidencia ya tiene la hoja ${name}`);
  }
}
const font = 'Arial';
const fill = '#303040';
const stripe = '#F3F3F5';

const summary = workbook.worksheets.add('Sitios de inhumación');
summary.showGridLines = false;
summary.getRange('A1').values = [['Sitios de inhumación']];
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

workbook.recalculate();
const preview = await workbook.render({sheetName:'Sitios de inhumación',range:'A1:C8',scale:1,format:'png'});
if (process.argv.includes('--vista-previa')) {
  await fs.writeFile(path.join(path.dirname(outputPath), 'vista_previa_inhumacion.png'),new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath),{recursive:true});
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`Excel combinado: ${outputPath}`);
