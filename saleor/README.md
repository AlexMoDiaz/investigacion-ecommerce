# Saleor en local (Docker + Dev Container) y revisión de la BD con DBeaver

Entorno probado el 23/10/2026 con **Saleor 3.23**, Docker 29.8 (OrbStack) y Docker Compose v5.5 en macOS.

## Archivos
```
saleor/
├── docker-compose.yml                         # stack completo de Saleor
├── .env.example                               # variables (copiar a .env)
├── .env                                       # tu copia local (no se sube al repo)
├── .devcontainer/
│   ├── devcontainer.json                      # abre el proyecto dentro de un contenedor
│   └── docker-compose.devcontainer.yml        # añade el contenedor "workspace" (Node 22 + psql)
├── sql/consultas-dbeaver.sql                  # consultas para explorar el esquema
└── verificacion/
    ├── verificar.py                           # repite lo "verificado en local" del informe (BD, API, teemis)
    ├── poc_plantilla.py                       # PoC de la plantilla del spike: ES/FR, club y envío Premium
    └── panel/
        ├── prueba-panel.mjs                   # repite la prueba del panel con un navegador automatizado
        └── promocion-manual/                  # paso de la promoción hecho a mano, con capturas
```

Servicios: `db` (Postgres 15), `cache` (Valkey, compatible con Redis), `migrate` (aplica las migraciones y termina), `api`, `worker` (Celery), `beat` (planificador de Celery), `dashboard`, `jaeger` y `mailpit`.

Cambios respecto al oficial [saleor-platform](https://github.com/saleor/saleor-platform):
- **Servicio `migrate`**: la API no arranca hasta que la base de datos está migrada. Te ahorras el paso manual y el error de "relation does not exist".
- **Healthcheck en Postgres** para que `migrate` no intente conectarse antes de tiempo.
- **Puertos publicados solo en `127.0.0.1`**: la BD con la contraseña `saleor` no queda expuesta a tu red wifi.
- **Versiones fijadas**, para que el entorno sea reproducible (`SALEOR_VERSION` en `.env`).
- **`beat` como servicio aparte** en lugar de `worker -B`. En las pruebas, el planificador dejó de lanzar el recálculo de promociones y los descuentos nuevos no se aplicaban hasta reiniciarlo (ver informe 1.7). Si te pasa, `docker compose restart beat`.

## Requisitos
- Docker Desktop u OrbStack, con **al menos 5 GB de RAM** para Docker.
- Puertos libres: 5432, 8000, 9000, 8025, 16686. Si ya tienes un Postgres en el 5432, cambia `POSTGRES_HOST_PORT` en `.env`.
- Opcional: VS Code + extensión **Dev Containers**.
- [DBeaver Community](https://dbeaver.io/download/).

## Opción A: con Docker Compose (la más directa)
```bash
cd saleor
cp .env.example .env                 # solo la primera vez
docker compose up -d                 # descarga imágenes (~2-3 GB la primera vez) y arranca
docker compose ps                    # migrate debe salir "Exited (0)" y el resto "Up"

# Datos de ejemplo + superusuario admin@example.com / admin (solo la primera vez, ~2 min)
docker compose exec api python3 manage.py populatedb --createsuperuser
```

## Opción B: con Dev Container (VS Code)
Probado con la herramienta oficial (`npx @devcontainers/cli up --workspace-folder saleor`): levanta todos los servicios y, desde el contenedor `workspace`, `psql` y la API responden por nombre de servicio.

1. Abre la carpeta `saleor/` en VS Code.
2. `Cmd+Shift+P` → **Dev Containers: Reopen in Container**.
3. VS Code levanta todos los servicios de `docker-compose.yml` y además un contenedor `workspace` (Node 22, pnpm y psql) en la misma red. Desde su terminal:
   ```bash
   psql -c '\dt channel_*'                               # PGHOST=db ya viene configurado
   curl -s $SALEOR_API_URL -H 'content-type: application/json' \
     -d '{"query":"{ products(first:3, channel:\"default-channel\"){ edges { node { name } } } }"}'
   ```
4. Para los datos de ejemplo, ejecuta en la terminal de tu Mac (no en la del contenedor) el `populatedb` de la opción A.

> Este contenedor sirve para desarrollar apps de Saleor (por ejemplo, la de teemis) con acceso directo a `api:8000` y `db:5432`.

## URLs
| Qué | URL | Credenciales |
|---|---|---|
| Dashboard | http://localhost:9000 | admin@example.com / admin |
| API GraphQL (playground) | http://localhost:8000/graphql/ | — |
| Emails de prueba | http://localhost:8025 | — |
| Trazas | http://localhost:16686 | — |

## Verificar lo que dice el informe
Con el stack levantado y los datos de ejemplo cargados:
```bash
python3 verificacion/verificar.py
```
El script repite las 22 comprobaciones marcadas como *"verificado en local"* en `informe/01-saleor.md`:
- el esquema de la BD (tablas, columnas que existen y que no existen, solo exportación CSV, IVA por canal, traducciones, SEO y facturas externas);
- la API (webhooks síncronos y asíncronos, `price` en `CheckoutLineInput`, que no hay listas de precios ni grupos de clientes, y que los tipos de cliente de la 3.23 no afectan a precios ni catálogo);
- la prueba de concepto de teemis: la app rebaja el precio de una línea, el staff no puede hacerlo, y un producto pagado al 100 % con teemis cierra el pedido sin pago.

Solo usa la librería estándar de Python. Crea una app temporal y la borra al terminar. Cada vez que se ejecuta deja un pedido de 0 € en la BD local. Si falla alguna comprobación, termina con código 1.

### PoC de la plantilla del spike
```bash
python3 verificacion/poc_plantilla.py
```
Hace la "PoC mínima" de `informe/spike-saleor.md` (14 comprobaciones):
- **Dos países:** crea los canales `poc-es` y `poc-fr` con IVA (21 % / 20 %), precio, envío e idioma distintos, y comprueba el total de un checkout en cada uno.
- **Club:** comprueba hasta dónde puede Saleor esconder un producto de club. No puede: un producto despublicado o un canal inactivo bloquean también a nuestra app. Lo que sí funciona es filtrar en la tienda por `metadata` y que la app **quite los envíos** a quien no es socio (webhook síncrono `CHECKOUT_FILTER_SHIPPING_METHODS`).
- **Envío gratis Premium:** la app añade un método de envío a 0 € solo a clientes Premium (`SHIPPING_LIST_METHODS_FOR_CHECKOUT`).

Mientras dura la prueba levanta un servidor de webhooks en el puerto **8765** del Mac. Saleor lo llama a través de `host.docker.internal`, y por eso `.env` lleva `HTTP_IP_FILTER_ENABLED=False`. Deja creados los canales, el tipo de cliente del club y tres clientes de prueba para verlos en el panel o en DBeaver. Si se vuelve a ejecutar, los borra antes. ⚠️ La app necesita `MANAGE_SHIPPING` y `MANAGE_CHECKOUTS`: sin ellos, Saleor **ignora el webhook sin avisar**.

### Prueba del panel (navegador automatizado)
```bash
cd verificacion/panel
npm install && npx playwright install chromium   # solo la primera vez
PAIS=France SLUG=fr npm run prueba
```
Hace desde el Dashboard, como lo haría alguien de operaciones:
1. Crear el canal de un país.
2. Ponerle precio a un producto desde la tabla tipo Excel.
3. Crear una promoción del −20 % solo en ese país. **Este paso es manual en el panel** (pasos y capturas en `verificacion/panel/promocion-manual/`). El script la crea por API con los mismos datos, porque los desplegables sin etiqueta de la condición dejaban colgada la automatización.
4. Esperar hasta 2 minutos a que el catálogo muestre el precio rebajado.

Después comprueba en la BD que todo quedó bien, incluidos los dos problemas encontrados: el precio a 0 € al marcar "Disponible" sin precio y el tiempo que tarda en aplicarse la promoción. Deja capturas en `verificacion/panel/capturas/`. Si ya se ejecutó antes, borra primero el canal y la promoción anteriores. **Es frágil por diseño**: depende de la maquetación del Dashboard 3.23 (la tabla de variantes es un canvas y se pulsa por coordenadas).

Último resultado: **5/6**. Falla el paso 4, que es justo el problema del planificador. El precio sigue en 24,95 € pasados 2 minutos. Con `docker compose restart beat` baja a 19,96 € en menos de 10 s.

## Comandos útiles
```bash
docker compose logs -f api worker beat   # ver logs
docker compose stop                  # parar sin borrar datos
docker compose up -d                 # volver a arrancar
docker compose down -v               # ⚠️ borra todo, incluida la BD
```

## Conectarse con DBeaver
1. **Database → New Database Connection → PostgreSQL → Next.**
2. Pestaña *Main*:
   | Campo | Valor |
   |---|---|
   | Host | `localhost` |
   | Port | `5432` (o tu `POSTGRES_HOST_PORT`) |
   | Database | `saleor` |
   | Username / Password | `saleor` / `saleor` (marca *Save password*) |
3. Si te lo pide, deja que DBeaver **descargue el driver** de PostgreSQL. **Test Connection → Finish.**
4. Navega a `saleor → Schemas → public → Tables` (148 tablas).
5. **Diagrama ER:** selecciona las tablas que te interesan (por ejemplo `channel_channel`, `product_product`, `product_productvariant`, `product_productchannellisting`, `product_productvariantchannellisting`, `discount_promotion`, `discount_promotionrule`, `discount_promotionrule_channels`, `checkout_checkout`, `checkout_checkoutline`, `discount_checkoutlinediscount`), clic derecho → **View Diagram**. Si seleccionas solo esas, el diagrama se entiende; con las 148 no.
6. **SQL Editor → Open SQL script** → abre `sql/consultas-dbeaver.sql` y ejecuta cada consulta con `Ctrl+Enter`.

### Qué mirar (guion de revisión)
| Pregunta | Dónde | Consulta |
|---|---|---|
| ¿Cómo se representa un país? | `channel_channel` (una moneda por canal) | 1 |
| ¿Dónde está el precio por país? | `product_productvariantchannellisting.price_amount` | 2 |
| ¿Cómo tiene cada país un catálogo distinto? | Hay o no fila en `product_productchannellisting` | 3, 4 |
| ¿Cómo se limita una promoción a un país? | `discount_promotionrule_channels` | 5 |
| ¿Dónde se precalcula el precio rebajado? | `product_variantchannellistingpromotionrule` | 6 |
| ¿Cómo varía un voucher por país? | `discount_voucherchannellisting` | 7 |
| ¿Dónde aplicaría la app de precios Toteemi el precio rebajado? | `checkout_checkoutline.price_override` y `price_override_reason` | 8 |
| ¿Qué descuentos tiene una línea y de dónde vienen? | `discount_checkoutlinediscount` | 9 |

> Los datos de ejemplo traen 2 canales (`default-channel` en USD y `channel-pln` en PLN) y 81 variantes con precio en ambos. Para simular nuestro caso, crea canales en el Dashboard (*Configuration → Channels*: `es`, `fr`, `de`… en EUR) y asígnales productos y precios.
