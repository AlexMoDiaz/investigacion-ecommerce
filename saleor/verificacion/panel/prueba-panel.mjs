// Repite la prueba del panel de informe/01-saleor.md (1.7): la operativa de abrir un país nuevo
// usando solo el Dashboard, como lo haría alguien no técnico, y comprueba el resultado en la BD.
//
//   npm install && npx playwright install chromium   (solo la primera vez)
//   PAIS=France SLUG=fr npm run prueba
//
// Deja capturas de cada paso en ./capturas. Es frágil por diseño: depende de la maquetación
// del Dashboard 3.23 (algunos clics van por coordenadas porque la tabla de variantes es un canvas).
// La promoción (paso 3) no se automatiza en el panel: está documentada en promocion-manual/.

import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';

const DASHBOARD = 'http://localhost:9000/dashboard';
const PAIS = process.env.PAIS ?? 'France';
const SLUG = process.env.SLUG ?? 'fr';
const PRODUCTO = 'Monospace Tee';
const PRECIO = '24.95';
const SALEOR_DIR = new URL('../../', import.meta.url).pathname;

mkdirSync('capturas', { recursive: true });
const sql = (q) =>
  execFileSync('docker', ['compose', 'exec', '-T', 'db', 'psql', '-U', 'saleor', '-d', 'saleor', '-At', '-c', q], {
    cwd: SALEOR_DIR,
    encoding: 'utf8',
  }).trim();
const resultados = [];
const check = (tarea, ok, detalle) => {
  resultados.push(ok);
  console.log(`${ok ? '✅' : '❌'} ${tarea}${detalle ? `\n     → ${detalle}` : ''}`);
};

// Si ya se ejecutó antes, borra el canal y la promoción de la prueba anterior (por API) para empezar limpio
const gql = async (query, variables = {}, token) => {
  const res = await fetch('http://localhost:8000/graphql/', {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify({ query, variables }),
  });
  return (await res.json()).data;
};
const { tokenCreate } = await gql('mutation { tokenCreate(email: "admin@example.com", password: "admin") { token } }');
const { channel } = await gql(`{ channel(slug: "${SLUG}") { id } }`, {}, tokenCreate.token);
if (channel) await gql('mutation($id: ID!) { channelDelete(id: $id) { errors { message } } }', { id: channel.id }, tokenCreate.token);
const { promotions } = await gql(`{ promotions(first: 10, where: { name: { eq: "Prueba panel ${PAIS}" } }) { edges { node { id } } } }`, {}, tokenCreate.token);
for (const { node } of promotions.edges) {
  await gql('mutation($id: ID!) { promotionDelete(id: $id) { errors { message } } }', { id: node.id }, tokenCreate.token);
}

const browser = await chromium.launch();
// Ventana ancha: la tabla de variantes tiene 230 px por canal y con muchos canales el último quedaría fuera
const page = await (await browser.newContext({ viewport: { width: 2600, height: 1000 } })).newPage();
// El panel pregunta "¿salir sin guardar?" al navegar; se acepta para que la prueba no se quede colgada
page.on('dialog', (dialog) => dialog.accept());
const captura = (nombre) => page.screenshot({ path: `capturas/${nombre}.png`, fullPage: true });
// Las opciones de los desplegables no responden a locator.click(); se pulsan con el ratón
const elegir = async (texto) => {
  const box = await page.getByRole('option', { name: texto }).first().boundingBox();
  await page.mouse.click(box.x + 20, box.y + box.height / 2);
  await page.waitForTimeout(800);
};

try {
  await page.goto(`${DASHBOARD}/`);
  await page.fill('input[name=email]', 'admin@example.com');
  await page.fill('input[name=password]', 'admin');
  await page.keyboard.press('Enter');
  await page.waitForURL(/dashboard\/home/);

  // 1. Crear el canal: al elegir el país, el panel rellena la moneda solo
  await page.goto(`${DASHBOARD}/channels/add`);
  await page.waitForTimeout(3000);
  await page.fill('input[name=name]', PAIS);
  await page.fill('input[name=slug]', SLUG);
  await page.locator('input[name=defaultCountry]').click();
  await page.keyboard.type(PAIS, { delay: 50 });
  await page.waitForTimeout(800);
  await elegir(new RegExp(`^${PAIS}$`));
  const moneda = await page.inputValue('input[name=currencyCode]');
  await page.getByRole('button', { name: 'Create', exact: true }).click();
  await page.waitForURL(/channels\/.+\?action=setup/);
  await captura('1-canal-creado');
  const canal = sql(`select currency_code || ' ' || (select prices_entered_with_tax from tax_taxconfiguration t where t.channel_id = c.id) from channel_channel c where slug = '${SLUG}'`);
  check(`1. Canal "${PAIS}" creado y moneda rellenada sola`, canal.startsWith(moneda) && moneda === 'EUR', `moneda=${moneda}`);
  check('   El canal nuevo usa precios con IVA incluido', canal.endsWith('true'), canal);

  // 2. Producto disponible en el país y precio por variante en la tabla tipo Excel
  const productId = sql(`select id from product_product where name = '${PRODUCTO}'`);
  const productGid = Buffer.from(`Product:${productId}`).toString('base64');
  await page.goto(`${DASHBOARD}/products/${productGid}`);
  await page.waitForTimeout(4000);
  await page.getByRole('button', { name: 'Manage', exact: true }).click();
  await page.locator('[role=dialog]').getByText(PAIS, { exact: true }).click();
  await page.locator('[role=dialog]').getByRole('button', { name: /Confirm/ }).click();
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForTimeout(4000);
  // La tabla de variantes es un canvas: columnas fijas (variante, SKU), un par Disponible/Precio
  // de 230 px por canal y después los almacenes. El país nuevo es el último par de canal.
  // Se cuentan los canales en la BD y no las columnas, porque el número de almacenes varía.
  const abrirTabla = async () => {
    await page.getByRole('button', { name: 'Bulk edit' }).click();
    await page.waitForTimeout(2000);
    const grupo = Number(sql(`select count(*) from product_productchannellisting where product_id = ${productId}`)) - 1;
    return { xDisponible: 448 + 230 * grupo + 40, xPrecio: 448 + 230 * grupo + 155 };
  };
  const guardarTabla = async () => {
    await page.locator('#modal-root [data-test-id=button-exit-fullscreen]').click();
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await page.waitForTimeout(4000);
  };
  const preciosGuardados = () => sql(`select string_agg(distinct l.price_amount::text, ',') from product_productvariantchannellisting l join product_productvariant v on v.id = l.variant_id join channel_channel c on c.id = l.channel_id where c.slug = '${SLUG}' and v.product_id = ${productId}`);
  const filas = [216, 256, 296, 336, 376];

  // 2a. Marcar "Disponible" sin escribir precio (el despiste que encontramos)
  let { xDisponible, xPrecio } = await abrirTabla();
  for (const y of filas) await page.mouse.click(xDisponible, y);
  await captura('2a-disponible-sin-precio');
  await guardarTabla();
  const sinPrecio = preciosGuardados();
  check('   Si se marca "Disponible" sin precio, el panel guarda las variantes a 0 €', sinPrecio === '0.000', `precio guardado: ${sinPrecio}`);

  // 2b. Poner el precio: doble clic en la celda, escribir e Intro
  ({ xPrecio } = await abrirTabla());
  for (const y of filas) {
    await page.mouse.dblclick(xPrecio, y);
    const editor = page.locator('.clip-region input');
    await editor.fill(PRECIO);
    await editor.press('Enter');
  }
  await captura('2b-precios-pais');
  await guardarTabla();
  const precios = preciosGuardados();
  check(`2. Precio ${PRECIO} € en todas las variantes desde la tabla tipo Excel`, precios === `${PRECIO}0`, precios);

  // 3. Promoción −20 % solo en ese país (una regla por canal).
  // En el panel se hace a mano (ver promocion-manual/README.md): sus desplegables sin etiqueta
  // dejaban la prueba colgada. Aquí se crea por API con los mismos datos para poder medir el paso 4.
  const { channel: canalNuevo } = await gql(`{ channel(slug: "${SLUG}") { id } }`, {}, tokenCreate.token);
  // Experimento (PREPARAR=canal,producto): activar el canal y/o publicar el producto antes de la promoción
  const preparar = (process.env.PREPARAR ?? '').split(',').filter(Boolean);
  if (preparar.includes('canal')) {
    await gql('mutation($id: ID!) { channelUpdate(id: $id, input: {isActive: true}) { errors { message } } }',
      { id: canalNuevo.id }, tokenCreate.token);
  }
  if (preparar.includes('producto')) {
    await gql(`mutation($id: ID!, $c: ID!) { productChannelListingUpdate(id: $id, input: {updateChannels: [{channelId: $c,
      isPublished: true, visibleInListings: true, isAvailableForPurchase: true}]}) { errors { message } } }`,
      { id: productGid, c: canalNuevo.id }, tokenCreate.token);
  }
  if (preparar.length) console.log(`   (preparado antes de la promoción: ${preparar.join(', ')})`);
  const { promotionCreate } = await gql(
    `mutation($input: PromotionCreateInput!) { promotionCreate(input: $input) { errors { field message } } }`,
    {
      input: {
        name: `Prueba panel ${PAIS}`,
        type: 'CATALOGUE',
        rules: [{
          name: `-20% ${PRODUCTO} ${SLUG}`,
          channels: [canalNuevo.id],
          rewardValueType: 'PERCENTAGE',
          rewardValue: 20,
          cataloguePredicate: { productPredicate: { ids: [productGid] } },
        }],
      },
    },
    tokenCreate.token,
  );
  if (promotionCreate.errors.length) throw new Error(JSON.stringify(promotionCreate.errors));
  const promo = sql(`select r.reward_value_type || ' ' || r.reward_value from discount_promotionrule r join discount_promotionrule_channels rc on rc.promotionrule_id = r.id join channel_channel c on c.id = rc.channel_id where c.slug = '${SLUG}'`);
  check('3. Promoción guardada para ese país (creada por API; en el panel es paso manual)', promo === 'percentage 20.000', promo);

  // 4. ¿Se recalcula el precio rebajado del catálogo? (lo lanza beat cada 30 s)
  let rebajado = '';
  for (let s = 0; s < 120; s += 10) {
    rebajado = sql(`select min(l.discounted_price_amount) from product_productvariantchannellisting l join product_productvariant v on v.id = l.variant_id join channel_channel c on c.id = l.channel_id where c.slug = '${SLUG}' and v.product_id = ${productId}`);
    if (rebajado !== `${PRECIO}0`) break;
    await page.waitForTimeout(10_000);
  }
  check('4. El precio rebajado se aplica en menos de 2 minutos', rebajado === '19.960',
    rebajado === '19.960' ? rebajado : `sigue en ${rebajado}: ¿beat arranca con --scheduler saleor.schedulers.schedulers.PersistentScheduler? (README, problemas conocidos)`);
} finally {
  await browser.close();
}

console.log(`\n${resultados.filter(Boolean).length}/${resultados.length} comprobaciones correctas (capturas en ./capturas)`);
process.exit(resultados.every(Boolean) ? 0 : 1);
