/** Convierte el fondo Esri del HTML recibido en una capa Leaflet autocontenida. */
const DATOS = /(<script type="application\/json" data-for="[^"]+">)([\s\S]*?)(<\/script>)/;
const URL_ESRI_GRIS = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}';

export function normalizarWidgetMapa(fragmento) {
  const match = DATOS.exec(fragmento);
  if (!match) throw new Error('No se encontraron los datos JSON del mapa Leaflet.');
  const mapa = JSON.parse(match[2]);
  const calls = mapa?.x?.calls;
  if (!Array.isArray(calls)) throw new Error('El mapa no contiene sus capas.');
  const providers = calls.filter(call => call.method === 'addProviderTiles');
  if (providers.length === 0) return fragmento;
  if (providers.length !== 1 || providers[0].args?.[0] !== 'Esri.WorldGrayCanvas') {
    throw new Error('El mapa usa un proveedor de teselas no reconocido.');
  }
  const provider = providers[0];
  provider.method = 'addTiles';
  provider.args = [URL_ESRI_GRIS, provider.args[1], provider.args[2], {
    minZoom: 0,
    maxZoom: 16,
    tileSize: 256,
    subdomains: 'abc',
    errorTileUrl: '',
    tms: false,
    noWrap: false,
    zoomOffset: 0,
    zoomReverse: false,
    opacity: 1,
    zIndex: 1,
    detectRetina: false,
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    ...provider.args[3],
  }];
  return fragmento.replace(match[0], match[1] + JSON.stringify(mapa) + match[3]);
}
