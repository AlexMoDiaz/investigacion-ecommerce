# Spike Saleor: ¿puede sustituir a WooCommerce en la tienda de Toteemi?

Investigación de ACID TANGO para la apertura internacional de la tienda de Toteemi (hoy WordPress + WooCommerce en `toteemi.com`). Hay tres spikes en paralelo con la misma plantilla: **Saleor** (este repo), Medusa y Shopify Plus.

El repo contiene el entregable y todo lo necesario para **repetir las pruebas**: un Saleor 3.23 en local con Docker y tres scripts que comprueban cada afirmación marcada como *verificado*.

## Conclusión en corto
**⚠️ Seguir con reservas.**
- **Lo que trae de serie:** el multipaís (un canal por país con su IVA, precio, envío e idioma) y el caso crítico de los **Teemis**. Para los Teemis una app nuestra sobrescribe el precio de las líneas del checkout, incluido el pago 100 % con Teemis.
- **Lo que hay que construir:** casi todo lo propio de Toteemi es desarrollo propio o un servicio externo: Premium (Stripe Billing), clubs, cupones por rol, packs, Business Central y la propia tienda (es headless).
- **Estimación orientativa:** ≈ 145–220 días-persona y ≈ 450–650 $/mes de infraestructura en AWS.

El detalle está en **[`informe/spike-saleor.md`](informe/spike-saleor.md)**.

## Qué hay en el repo
```
.
├── informe/
│   ├── spike-saleor.md            ← ENTREGABLE: la plantilla del spike rellena (se pega tal cual en Notion)
│   ├── 00-situacion-actual.md     anexo: qué hace hoy la tienda WooCommerce, requisitos y definición de los Teemis
│   ├── 01-saleor.md               anexo: análisis completo de Saleor (arquitectura, BD, checkout, panel, riesgos)
│   └── 06-transversales.md        anexo: IVA/OSS, facturación, idiomas, SEO, migración y desglose de costes
└── saleor/
    ├── docker-compose.yml         Saleor 3.23 completo (9 servicios)
    ├── .env.example               variables; se copia a .env (que no se sube)
    ├── .devcontainer/             lo mismo, abierto desde VS Code dentro de un contenedor
    ├── sql/consultas-dbeaver.sql  10 consultas para entender el esquema
    └── verificacion/
        ├── verificar.py           comprueba el análisis: BD, API y PoC de Teemis (22 comprobaciones)
        ├── poc_plantilla.py       la "PoC mínima" de la plantilla: ES/FR, club y envío Premium (14)
        └── panel/                 prueba del panel con un navegador automatizado (6) + paso manual con capturas
```

## 1. Requisitos
- **Docker Desktop u OrbStack**, con al menos **5 GB de RAM** asignados a Docker.
- **Python 3.10 o superior** (solo la librería estándar) para los scripts de verificación.
- **Node 20 o superior**, solo para la prueba del panel.
- Puertos libres: **5432, 8000, 9000, 8025, 16686** y **8765** (este último lo usa `poc_plantilla.py`). Si ya tienes un Postgres en el 5432, cambia `POSTGRES_HOST_PORT` en `.env`.
- Opcional: [DBeaver Community](https://dbeaver.io/download/), y VS Code con la extensión **Dev Containers**.

## 2. Levantar Saleor
```bash
cd saleor
cp .env.example .env              # solo la primera vez
docker compose up -d              # la primera vez descarga ~2-3 GB de imágenes
docker compose ps                 # "migrate" debe salir Exited (0) y el resto Up

# Datos de ejemplo + superusuario admin@example.com / admin (solo la primera vez)
docker compose exec api python3 manage.py populatedb --createsuperuser
```
**Qué pasa por dentro:**
1. Arranca Postgres. Su healthcheck avisa cuando acepta conexiones.
2. Entonces `migrate` crea las **148 tablas** y termina.
3. Solo después arrancan `api`, `worker` y `beat`.
4. `populatedb` carga 29 productos, 2 canales (USD y PLN), almacenes y zonas de envío.

Desde cero tarda unos 80 s en arrancar y unos 17 s en cargar los datos (medido en un Mac con OrbStack).

| Qué | URL | Acceso |
|---|---|---|
| Panel de administración (Dashboard) | http://localhost:9000 | `admin@example.com` / `admin` |
| API GraphQL (con *playground*) | http://localhost:8000/graphql/ | — |
| Emails que envía Saleor (Mailpit) | http://localhost:8025 | — |
| Trazas (Jaeger) | http://localhost:16686 | — |

### Alternativa: Dev Container (VS Code)
Abre la carpeta `saleor/` en VS Code → `Cmd+Shift+P` → **Dev Containers: Reopen in Container**. Levanta los mismos servicios y además un contenedor `workspace` (Node 22, pnpm y `psql`) en la misma red. Sirve para **desarrollar apps de Saleor** con acceso directo a `api:8000` y `db:5432`:
```bash
psql -c '\dt channel_*'          # PGHOST=db ya viene configurado
curl -s $SALEOR_API_URL -H 'content-type: application/json' \
  -d '{"query":"{ products(first:3, channel:\"default-channel\"){ edges { node { name } } } }"}'
```
El `populatedb` se ejecuta igualmente desde la terminal del Mac. Lo he probado con `npx @devcontainers/cli up --workspace-folder saleor`.

### Por qué el `docker-compose.yml` no es el oficial tal cual
Está basado en [saleor-platform](https://github.com/saleor/saleor-platform), con estos cambios:

| Cambio | Por qué |
|---|---|
| Servicio **`migrate`** del que dependen `api`, `worker` y `beat` | La API no arranca hasta que la BD está migrada. Evita el paso manual y el error *relation does not exist* |
| **Healthcheck** en Postgres | Para que `migrate` no intente conectarse antes de tiempo |
| Puertos publicados solo en **`127.0.0.1`** | La BD, con contraseña `saleor`, no queda expuesta a la red wifi |
| **Versiones fijadas** (`SALEOR_VERSION=3.23` y las imágenes auxiliares) | Que el entorno sea reproducible |
| **`beat` como servicio aparte** en vez de `worker -B` | El planificador de tareas se paraba y las promociones no se aplicaban (ver *Problemas conocidos*). Aparte se puede reiniciar sin tocar el worker |
| `HTTP_IP_FILTER_ENABLED=False` en `.env` | Para que Saleor pueda llamar a webhooks en tu Mac (`host.docker.internal`). **En producción, `True`** |

## 3. Repetir las pruebas
Con el stack levantado y los datos de ejemplo cargados, desde la raíz del repo:

| Script | Qué comprueba | Resultado esperado | Qué deja en la BD |
|---|---|---|---|
| `python3 saleor/verificacion/verificar.py` | Lo marcado como *verificado* en el análisis | **22/22** | Un pedido de 0 € por ejecución |
| `python3 saleor/verificacion/poc_plantilla.py` | La PoC mínima de la plantilla | **14/14** | Canales `poc-es` y `poc-fr`, el tipo de cliente del club y 3 clientes (los rehace en cada ejecución) |
| `cd saleor/verificacion/panel && npm run prueba` | El panel, usado como lo haría alguien no técnico | **5/6** (el fallo es un problema real de Saleor) | Canal `fr` y promoción "Prueba panel France" (los rehace en cada ejecución) |

Los tres terminan con código 1 si falla algo, y las apps temporales que crean se borran al terminar.

### `verificar.py`: el análisis de Saleor
Consulta la BD con `psql` dentro del contenedor (no hace falta instalar nada) y la API por GraphQL:
- **Base de datos:**
  - Las tablas de canal, precio por canal, descuentos, envíos e impuestos.
  - La línea de checkout tiene `price_override`.
  - El precio por país **no** tiene `metadata`.
  - Solo hay exportación CSV.
  - 14 tablas de traducciones.
  - SEO traducible.
  - Las facturas pueden apuntar a un documento externo.
- **API:**
  - No hay webhook síncrono de descuentos ni de validación.
  - Existen los webhooks que usa el diseño.
  - Las promociones no se pueden filtrar por cliente.
  - No hay listas de precios.
  - Los *tipos de cliente* de la 3.23 no afectan a precios ni a catálogo.
- **PoC de Teemis:**
  - Una app con `HANDLE_CHECKOUTS` baja el precio de una línea.
  - Un usuario de staff no puede hacerlo.
  - Un producto pagado al 100 % con Teemis cierra el pedido **sin pasar por el pago**.

### `poc_plantilla.py`: la PoC de la plantilla
- **Dos países:** crea `poc-es` y `poc-fr` con IVA del 21 % y del 20 %, precio de 24,95 € y 26,95 €, envío de 4,90 € y 5,90 €, y el producto en francés. Después comprueba un checkout en cada país.
- **Club:** comprueba hasta dónde puede Saleor limitar un producto a los socios. **Saleor no puede ocultarlo**: un producto despublicado o un canal inactivo bloquean también a nuestra app. Lo que sí funciona:
  - la tienda filtra el catálogo por `metadata`;
  - nuestra app **quita los envíos** a quien no es socio (webhook síncrono `CHECKOUT_FILTER_SHIPPING_METHODS`), y sin envío no se puede cerrar la compra.
- **Envío gratis Premium:** la app añade un envío a 0 € solo a clientes Premium (`SHIPPING_LIST_METHODS_FOR_CHECKOUT`).

Mientras dura, el script hace de "app" con un servidor de webhooks en el puerto **8765** del Mac. Saleor lo llama a través de `host.docker.internal`.

### Prueba del panel
```bash
cd saleor/verificacion/panel
npm install && npx playwright install chromium   # solo la primera vez
PAIS=France SLUG=fr npm run prueba
```
Con un navegador sin ventana, hace en el Dashboard:
1. Crear el canal de un país. Comprueba que la moneda se rellena sola y que el canal sale con IVA incluido.
2. Ponerle precio a un producto en la tabla tipo Excel, incluido el despiste de marcarlo como disponible sin precio, que lo guarda a **0 €**.
3. La promoción del −20 %. Se crea **por API**, porque en el panel se hizo a mano: los desplegables sin etiqueta impedían automatizarlo. Los pasos y las capturas están en `panel/promocion-manual/`.
4. Esperar 2 minutos a que el catálogo muestre el precio rebajado. **Falla**: ver *Problemas conocidos*.

Deja capturas en `panel/capturas/`. Es frágil por diseño: depende de la maquetación del Dashboard 3.23, porque la tabla de variantes es un canvas y se pulsa por coordenadas.

## 4. Explorar la base de datos con DBeaver
1. **Database → New Database Connection → PostgreSQL.** Host `localhost`, puerto `5432`, base de datos `saleor`, usuario y contraseña `saleor` / `saleor`. Deja que descargue el driver → **Test Connection → Finish**.
2. `saleor → Schemas → public → Tables` (148 tablas). Para un **diagrama ER** legible, selecciona solo estas y haz clic derecho → **View Diagram**: `channel_channel`, `product_product`, `product_productvariant`, `product_productchannellisting`, `product_productvariantchannellisting`, `discount_promotion`, `discount_promotionrule`, `discount_promotionrule_channels`, `checkout_checkout`, `checkout_checkoutline`, `discount_checkoutlinediscount`.
3. **SQL Editor → Open SQL script** → `saleor/sql/consultas-dbeaver.sql`, y `Ctrl+Enter` en cada consulta.

| Pregunta | Dónde | Consulta |
|---|---|---|
| ¿Cómo se representa un país? | `channel_channel` (una moneda por canal) | 1 |
| ¿Dónde está el precio por país? | `product_productvariantchannellisting.price_amount` | 2 |
| ¿Cómo tiene cada país un catálogo distinto? | Hay o no fila en `product_productchannellisting` | 3, 4 |
| ¿Cómo se limita una promoción a un país? | `discount_promotionrule_channels` | 5 |
| ¿Dónde se precalcula el precio rebajado? | `product_variantchannellistingpromotionrule` | 6 |
| ¿Cómo varía un voucher por país? | `discount_voucherchannellisting` | 7 |
| ¿Dónde aplica nuestra app el precio con Teemis? | `checkout_checkoutline.price_override` y `price_override_reason` | 8 |
| ¿Qué descuentos tiene una línea y de dónde vienen? | `discount_checkoutlinediscount` | 9 |

Después de ejecutar `poc_plantilla.py` puedes ver en el panel y en DBeaver los canales `poc-es` y `poc-fr`, el tipo de cliente "Club Ciclista X" y sus clientes.

## 5. Comandos útiles
```bash
cd saleor
docker compose logs -f api worker beat   # ver logs
docker compose stop                      # parar sin borrar datos
docker compose up -d                     # volver a arrancar
docker compose restart beat              # si las promociones no se aplican (ver abajo)
docker compose down -v                   # ⚠️ borra todo, incluida la BD. Después: up -d y populatedb
```

## 6. Problemas conocidos
- **Las promociones nuevas no se aplican** hasta reiniciar `beat`. El planificador lanza el recálculo una vez y luego deja de hacerlo, aunque está programado cada 30 s. Se ha reproducido 3 veces, la última en una instalación nueva. Causa sin determinar. Solución en local: `docker compose restart beat`. En producción hay que monitorizarlo.
- **Precio 0 € por despiste:** si en el panel se marca un producto como disponible en un país sin escribir precio, se guarda a 0 €.
- **Webhooks síncronos que no llegan:** Saleor los ignora **sin avisar** si la app no tiene el permiso que pide el evento. Por ejemplo, `MANAGE_SHIPPING` para listar envíos y `MANAGE_CHECKOUTS` para filtrarlos.
- **Canales creados por API:** nacen **inactivos** si no se indica `isActive: true`. Desde el panel salen activos.
- **El puerto 5432 está ocupado:** cambia `POSTGRES_HOST_PORT` en `.env` y usa ese puerto en DBeaver.

## 7. Publicar en Notion
Copia el contenido de `informe/spike-saleor.md` en la página del spike. Mantiene la estructura de la plantilla: casillas, recuadros ✍️, tablas y valoraciones.

## Pendiente
- Pago de prueba con Stripe (faltan claves de test).
- Las dudas abiertas de la plantilla, que tiene que responder negocio o el equipo de la API de Toteemi.
- Comparar con los spikes de Medusa y Shopify Plus.
