# Spike Saleor: ¿puede sustituir a WooCommerce en la tienda de Toteemi?

Investigación de ACID TANGO para la apertura internacional de la tienda de Toteemi (hoy WordPress + WooCommerce en `toteemi.com`). Hay tres *spikes* en paralelo con la misma plantilla de Notion: **Saleor** (este repo), Medusa y Shopify Plus. Un *spike* es una investigación acotada para responder una pregunta técnica antes de decidir.

Este README sirve para tres cosas:
1. **Entender de dónde sale cada respuesta** de la plantilla de Notion ([`informe/spike-saleor.md`](informe/spike-saleor.md)): qué experimento o fuente la respalda y por qué se le puso esa valoración (secciones 3 a 6).
2. **Repetir los experimentos** uno mismo (secciones 7 a 10).
3. **Saber qué no está demostrado** (sección 11).

## Índice
1. [Conclusión en corto](#1-conclusión-en-corto)
2. [Qué hay en el repo](#2-qué-hay-en-el-repo)
3. [Conceptos que hay que conocer](#3-conceptos-que-hay-que-conocer)
4. [Cómo se ha investigado](#4-cómo-se-ha-investigado)
5. [Los experimentos, uno a uno](#5-los-experimentos-uno-a-uno)
6. [De dónde sale cada respuesta de la plantilla](#6-de-dónde-sale-cada-respuesta-de-la-plantilla)
7. [Levantar Saleor en local](#7-levantar-saleor-en-local)
8. [Repetir las pruebas](#8-repetir-las-pruebas)
9. [Explorar la base de datos con DBeaver](#9-explorar-la-base-de-datos-con-dbeaver)
10. [Comandos útiles y problemas conocidos](#10-comandos-útiles-y-problemas-conocidos)
11. [Qué no está demostrado y qué queda pendiente](#11-qué-no-está-demostrado-y-qué-queda-pendiente)

---

## 1. Conclusión en corto
**⚠️ Seguir con reservas.**
- **Lo que trae de serie:** el multipaís (un canal por país con su IVA, su precio, su envío y su idioma) y el caso crítico de los **Teemis**. Para los Teemis, una app nuestra sobrescribe el precio de las líneas del checkout, incluido el pago 100 % con Teemis. Está demostrado en local (experimentos E2, E4 y E5).
- **Lo que hay que construir:** casi todo lo propio de Toteemi es desarrollo propio o un servicio externo:
  - Premium (con Stripe Billing).
  - Clubs y cupones por rol. Saleor no puede esconder un producto, así que lo hace nuestra app bloqueando los envíos (E7 y E8).
  - Packs.
  - Business Central.
  - La propia tienda, porque Saleor es *headless*.
- **Estimación orientativa** (opinión, no medida): ≈ 145–220 días-persona y ≈ 450–650 $/mes de infraestructura en AWS.

## 2. Qué hay en el repo
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
        ├── verificar.py           E2–E4: BD, API y Teemis (22 comprobaciones)
        ├── poc_plantilla.py       E5–E8: ES/FR, club, envío Premium y caché de envíos (16 comprobaciones)
        └── panel/                 E9: el panel con un navegador automatizado (6 comprobaciones)
            └── promocion-manual/  el paso de la promoción, hecho a mano, con capturas
```

## 3. Conceptos que hay que conocer
Sin estos conceptos, el resto del documento no se entiende. Están explicados con el ejemplo de Toteemi.

| Concepto | Qué es | Ejemplo en Toteemi |
|---|---|---|
| **Headless** | El e-commerce solo tiene la parte de "atrás" (catálogo, precios, pedidos) y una API. La tienda que ve el cliente (el "frontend") es una aplicación aparte que hacemos nosotros | La tienda sería una web en Next.js que llama a la API de Saleor |
| **API GraphQL** | Una sola URL (`/graphql/`) a la que se le pide exactamente lo que se quiere. Una *query* lee y una *mutation* escribe | `{ product(slug: "ascii-tee", channel: "poc-es") { name } }` |
| **Introspección** | GraphQL permite preguntarle a la API por **su propio esquema**: qué tipos, campos y eventos tiene. Si algo no aparece ahí, no existe | La usamos para demostrar que no hay webhook de "calcular descuento" |
| **Canal** (*channel*) | La forma de Saleor de separar mercados. Cada canal tiene una moneda, sus precios, su catálogo, sus envíos y su configuración de impuestos | Un canal por país: `es`, `fr`… |
| **Producto y variante** | El producto es la ficha (la camiseta). La variante es lo que se compra de verdad (la talla S). El precio va en la variante | "Monospace Tee", talla S |
| **Checkout** | El carrito con la dirección y el envío, antes de convertirse en pedido | — |
| **Metadata** | Un campo JSON libre que tienen casi todas las entidades, para guardar datos propios sin tocar el esquema | `club = club-ciclista-x` en un producto |
| **App** | Un servicio **nuestro**, aparte de Saleor, que se instala con un **token** con permisos concretos. Es la forma de añadir lógica sin modificar Saleor | La futura "app de precios Toteemi" |
| **Webhook asíncrono** | Saleor **avisa** a la app de que algo ha pasado ("pedido pagado") y sigue a lo suyo | Registrar el gasto de Teemis en la API Django |
| **Webhook síncrono** | Saleor **pregunta** a la app y **espera** su respuesta antes de seguir | "¿Qué envíos puede usar este carrito?" |
| **BFF** (*Backend For Frontend*) | Un pequeño servidor de la tienda que hace de intermediario con Saleor y guarda las claves | Validar los Teemis justo antes de cerrar la compra |
| **Celery, worker y beat** | Celery es la librería de tareas en segundo plano de Saleor. El *worker* ejecuta tareas; *beat* es el reloj que las lanza cada X segundos | Recalcular cada 30 s los precios rebajados por promociones |
| **PoC** (*Proof of Concept*) | Una prueba mínima para demostrar que algo se puede hacer, no la implementación final | `poc_plantilla.py` |

## 4. Cómo se ha investigado
### Tres tipos de afirmaciones
Cada frase de la plantilla es de uno de estos tres tipos. En la plantilla, las del primer tipo llevan **"(verificado)"**.

| Tipo | Cómo se ha obtenido | Hasta qué punto fiarse |
|---|---|---|
| **Verificado en local** | Ejecutando algo contra un Saleor 3.23.44 levantado con Docker: consultas a la BD, llamadas a la API, scripts o lectura del código fuente de Saleor dentro del contenedor | Alta: cualquiera puede repetirlo con los comandos de este README |
| **Sacado de documentación** | Documentación oficial de Saleor, GitHub, la web de precios, Microsoft Learn… El enlace está en la plantilla | Media: la documentación puede estar desactualizada. Se ha contrastado el 23/10/2026 (ver E14) |
| **Estimación** | Coste de AWS y días de desarrollo | Baja: es una opinión razonada. Está marcada como "orientativa" y hay que revisarla con el equipo |

### Proceso y revisión
1. **Análisis inicial:** documentación y código de Saleor, la tienda actual (`toteemi.com`) y el repositorio de la app de Toteemi (para entender los Teemis y Premium).
2. **Entorno local** con Docker y **scripts** que comprueban cada afirmación (`verificar.py`, `poc_plantilla.py`, `prueba-panel.mjs`).
3. **Revisión paso a paso desde cero:** se borró todo (`docker compose down -v`), se volvió a levantar y se comprobó cada afirmación **a mano**, con consultas propias, sin fiarse de lo que imprimen los scripts. Esta revisión encontró **varios errores** en la primera versión de la plantilla. Están todos corregidos y explicados en los experimentos (busca "**Corrección**").

### Por qué no basta con que un script diga ✅
Un script solo comprueba lo que su autor pensó comprobar. En la revisión pasaron dos cosas que lo demuestran:
- La PoC daba ✅ en el envío gratis Premium, pero porque **no pedía los envíos antes de iniciar sesión**. Al hacerlo a mano, como lo haría la tienda, falló (E8).
- La prueba del panel culpaba a "un fallo de Saleor" que en realidad era **nuestra configuración** (E9).

Por eso cada experimento de abajo explica también cómo comprobarlo **sin el script**.

---

## 5. Los experimentos, uno a uno
Formato de cada experimento: **pregunta → qué se hizo → qué salió → conclusión → cómo repetirlo**. Los comandos se ejecutan desde la raíz del repo con el stack levantado (sección 7).

Para no repetir el mismo texto en cada experimento, se usan dos atajos:
```bash
# Consulta SQL a la BD de Saleor (no hace falta instalar psql)
SQL='docker compose -f saleor/docker-compose.yml exec -T db psql -U saleor -d saleor -c'
# Llamada anónima a la API (como lo haría la tienda)
API='curl -s localhost:8000/graphql/ -H content-type:application/json -d'
```

### E1 · El entorno arranca desde cero y es el que dice el informe
- **Pregunta:** ¿qué versión exacta se ha probado y qué piezas necesita Saleor?
- **Qué se hizo:** borrar todo (`down -v`), levantar (`up -d`) y cargar los datos de ejemplo (`populatedb`). Después se preguntó la versión **al código que está corriendo** y se contaron las tablas en el catálogo de Postgres.
- **Qué salió:** Python 3.12.15, Django 5.2.18 y Saleor 3.23.44. **148 tablas**. 8 servicios en marcha más `migrate`, que termina con `Exited (0)`. Unos 80 s en arrancar y 17 s en cargar los datos.
- **Conclusión:** respalda el bloque 1 (stack y versión) y el bloque 2 (componentes: api, worker, beat, Postgres, Valkey).
- **Repetir:**
  ```bash
  docker compose -f saleor/docker-compose.yml exec -T api python3 -c "import sys, django, saleor; print(sys.version.split()[0], django.get_version(), saleor.__version__)"
  $SQL "select count(*) from information_schema.tables where table_schema = 'public'"
  ```

### E2 · Cómo guarda Saleor un país (modelo de datos)
- **Pregunta:** ¿cómo se consiguen un precio y un catálogo distintos por país?
- **Qué se hizo:** consultas a las tablas de canales, precios y publicación, y a los índices.
- **Qué salió:**
  - `channel_channel` tiene **una sola columna `currency_code`**, es decir, una moneda por canal.
  - La misma talla S tiene **una fila de precio por canal** en `product_productvariantchannellisting` (20 USD, 90 PLN, 24,95 €, 26,95 €…), y un índice **UNIQUE `(variant_id, channel_id)`** impide dos precios para la misma variante y canal.
  - Un producto existe en un país solo si tiene fila en `product_productchannellisting`. "Dash Force" no tiene fila en los canales franceses, y la API devuelve `null` al pedirlo allí.
  - La tabla de precio por canal **no tiene `metadata`**; la variante sí.
- **Conclusión:** respalda el bloque 7 (país: precio y catálogo por país) y el bloque 8 (multitenant por columna `channel_id`, crecimiento variantes × canales). El máximo de Teemis por país no tiene sitio "natural", así que va en la `metadata` de la variante o en la API Django.
- **Repetir:** `saleor/sql/consultas-dbeaver.sql` (consultas 1 a 4), o:
  ```bash
  $SQL "select id, name, slug, currency_code, is_active from channel_channel order by id"
  $SQL "select indexdef from pg_indexes where tablename = 'product_productvariantchannellisting' and indexdef like '%UNIQUE%'"
  ```

### E3 · Qué existe en la API y qué no (introspección)
- **Pregunta:** ¿hay algún mecanismo de Saleor pensado para "descuentos a medida" o para limitar promociones por cliente?
- **Qué se hizo:** preguntar a la API por su esquema.
- **Qué salió:**
  - **16 webhooks síncronos**: impuestos, pagos y envíos. **Ninguno de descuentos ni de "validar el checkout"**.
  - `CheckoutLineInput` tiene `price` y `priceOverrideReason`, que *"solo pueden usar las apps con `HANDLE_CHECKOUTS`"*.
  - Las condiciones de las promociones de catálogo solo admiten **producto, variante, categoría y colección**. Las de pedido, solo el **importe del carrito**.
  - Los **tipos de cliente** (nuevos en 3.23) solo aparecen en campos de clientes: ninguna promoción, voucher, canal ni producto los usa.
- **Conclusión:**
  - Los Teemis no pueden ir como "descuento": van como **precio sobrescrito** por una app (bloque 3).
  - Premium y clubs no se pueden resolver con promociones: lo tiene que hacer nuestra app (bloques 3 y 7).
  - El club **sí se puede guardar** en Saleor (tipo de cliente), pero Saleor no hace nada con ese dato.
- **Matiz que no está en la plantilla:** lo más parecido a un "hook de precios" es el webhook de impuestos, pero usarlo para descuentos falsearía el IVA.
- **Hallazgo:** el **mensaje de error** de Saleor dice que hace falta `MANAGE_CHECKOUTS`, pero el permiso real es `HANDLE_CHECKOUTS` (lo dicen el esquema y la prueba del E4).
- **Repetir:**
  ```bash
  $API '{"query":"{ __type(name: \"WebhookEventTypeSyncEnum\") { enumValues { name } } }"}'
  $API '{"query":"{ __type(name: \"CheckoutLineInput\") { inputFields { name description } } }"}'
  ```

### E4 · Teemis: la app cambia el precio de la línea
- **Pregunta:** ¿se puede aplicar el saldo de Teemis como rebaja real del checkout, incluido el pago 100 % con Teemis?
- **Qué se hizo:** `verificar.py` crea una app con `HANDLE_CHECKOUTS`, un checkout y le cambia el precio. Después se comprobó **en la BD**, con consultas propias, lo que quedó guardado.
- **Qué salió:**
  - La línea quedó a **40** con el motivo `teemis: 5 canjeados`, mientras el precio oficial de esa variante en el canal es **45**.
  - Con el token del **staff** (admin), Saleor **rechaza** el cambio.
  - Con un producto de 8,99 puesto a 0, el pedido se creó con **total 0, cobro `full` y 0 pagos** en las dos tablas de pagos de Saleor.
  - El precio base guardado en la línea **también es 40**. Saleor no recuerda que valía 45, solo el motivo.
- **Conclusión:**
  - El caso crítico es viable con un mecanismo oficial (bloque 3, valoración 🟡: viable, pero hay que construir la app).
  - Solo la app puede cambiar precios, nunca el cliente.
  - La trazabilidad hay que guardarla nosotros (motivo y `metadata`).
  - **Matiz de IVA:** el canal de ejemplo tiene precios **sin** IVA, así que 40 se convierte en **48,40** con dirección española. Por eso la plantilla pide canales con **precios con IVA incluido**.
- **Repetir:** `python3 saleor/verificacion/verificar.py` (sección "Prueba de concepto de teemis"). Luego:
  ```bash
  $SQL "select price_override, price_override_reason, undiscounted_unit_price_amount from checkout_checkoutline where price_override is not null order by created_at desc limit 1"
  $SQL "select number, total_gross_amount, charge_status, (select count(*) from payment_transactionitem t where t.order_id = o.id) as pagos from order_order o order by number desc limit 1"
  ```

### E5 · Dos países: IVA, precio y envío propios
- **Pregunta:** ¿el mismo producto puede tener en ES y FR otro precio, otro IVA y otro envío?
- **Qué se hizo:** `poc_plantilla.py` crea los canales `poc-es` y `poc-fr`. Después se crearon **checkouts anónimos con `curl`**, como lo haría la tienda, con una dirección de Madrid y otra de París.
- **Qué salió:**
  - **ES:** 24,95 € de los que 4,33 € son IVA (24,95 / 1,21), y UPS a 4,90 €.
  - **FR:** 26,95 € de los que 4,49 € son IVA (26,95 / 1,20), y UPS a 5,90 €.
  - En los dos se usó **el mismo id de variante**.
  - En la BD, la configuración de impuestos es **por canal** (precios con IVA incluido), pero los **tipos son por país y por clase de producto**: la tabla no tiene columna de canal.
- **Conclusión:** respalda el bloque 7 (país 🟢: resuelto de serie).
- **Corrección:** los tipos reducidos por clase que hay en la BD (por ejemplo, alimentación al 10 % en Francia) son **datos de ejemplo de `populatedb`**, no los legales. Los reales los tiene que dar la asesoría.
- **Repetir:** ver "Comprobación a mano" en la sección 8.

### E6 · Idioma del catálogo
- **Pregunta:** ¿el catálogo se puede pedir en el idioma de cada país?
- **Qué se hizo:** la PoC traduce el producto al francés y se pidió en tres combinaciones de canal e idioma.
- **Qué salió:**
  - En el canal francés pidiendo francés: "T-shirt Monospace".
  - En el canal español pidiendo español: `null`, porque no hay traducción y la tienda tiene que usar el nombre original.
  - En el canal **español** pidiendo **francés**: también "T-shirt Monospace".
- **Conclusión:** traducciones nativas (14 tablas `*translation`, verificado en E2–E3). El idioma lo elige la tienda en cada consulta, no depende del canal (bloque 7).
- **Matiz:** la comprobación "ES en español" de la PoC pasa porque no hay traducción, no porque la haya. Lo que de verdad demuestra el idioma es el caso francés.
- **Repetir:**
  ```bash
  $API '{"query":"{ fr: product(slug: \"ascii-tee\", channel: \"poc-fr\") { translation(languageCode: FR) { name } } esEnFrances: product(slug: \"ascii-tee\", channel: \"poc-es\") { translation(languageCode: FR) { name } } }"}'
  ```

### E7 · Clubs: ¿se puede limitar un producto a los socios?
- **Pregunta:** ¿cómo se consigue que un producto solo lo compren los socios de un club?
- **Qué se hizo, en tres partes:**
  1. **Sin app:** se buscó el producto del club con la API pública y se intentó comprarlo como anónimo.
  2. **¿Se puede esconder?** Se probó despublicarlo y meterlo en un canal inactivo, y se **leyó el código de Saleor** para ver si alguien se salta esas comprobaciones.
  3. **Con app:** se instaló una app mínima (dentro de `poc_plantilla.py`) que responde al webhook síncrono `CHECKOUT_FILTER_SHIPPING_METHODS`, y se repitió la compra como no socio y como socio.
- **Qué salió:**
  1. La API pública devuelve el producto y su `metadata club = club-ciclista-x` a cualquiera, y un anónimo **puede crear el checkout con UPS activo**. Sin app, cualquiera lo compra.
  2. Despublicado → `PRODUCT_NOT_PUBLISHED`; canal inactivo → `CHANNEL_INACTIVE`. En el código, `validate_channel(channel_slug, error_class)` y `validate_variants_are_published(variants_id, channel_id)` **no reciben quién hace la petición**, así que bloquean también a nuestra app. Esconderlo no sirve: no lo podríamos vender ni a los socios.
  3. Con la app, el no socio ve UPS **`active: false`** con *"Producto exclusivo para socios del club"* y no puede elegir envío (`DELIVERY_METHOD_NOT_APPLICABLE`). El socio ve UPS activo. Cada llamada aparece en **Jaeger** (`webhooks.checkout_filter_shipping_methods`, app `poc-plantilla`).
- **Conclusión:** bloque 7, club 🟡. La tienda **muestra** el catálogo del club filtrando por `metadata`, y la app **impide la compra** quitando los envíos.
- **Límite:** solo funciona con productos **con envío**. Para inscripciones o productos digitales habría que cancelar el pedido después.
- **Hallazgo:** si la app no tiene el permiso que pide el evento (`MANAGE_CHECKOUTS` para filtrar, `MANAGE_SHIPPING` para listar), Saleor **no la llama y no avisa**. Se encontró leyendo el código, al ver que el webhook no llegaba.
- **Corrección:** la plantilla decía que los webhooks "quedan registrados en `core_eventdelivery`". **Falso:** Saleor borra las entregas que salen bien (`clear_successful_delivery`) y solo guarda las que fallan. El historial está en las trazas.
- **Repetir:** sección 8, `poc_plantilla.py --esperar`.

### E8 · Envío gratis Premium y la caché de envíos
- **Pregunta:** ¿se puede dar envío gratis solo a los Premium (un "cupón por rol")?
- **Qué se hizo:** la misma app responde a `SHIPPING_LIST_METHODS_FOR_CHECKOUT` y añade "Envío gratis Premium" a 0 € si el cliente tiene `metadata premium = true`. Se probó a mano en el orden en que lo haría la tienda: el cliente ve los envíos como anónimo y **después** inicia sesión.
- **Qué salió:**
  - Como anónimo: solo UPS.
  - Al unir al cliente Premium: **seguía saliendo solo UPS**.
  - Con la mutación `deliveryOptionsCalculate` (nueva en 3.23) apareció "Envío gratis Premium" a 0.
  - En el código, `checkout_customer_attach.py` no invalida los envíos guardados.
- **Conclusión:** bloque 3 (cupones por rol 🟡). Los vouchers de Saleor no se pueden limitar por rol (solo `onlyForStaff`, un uso por cliente, etc.), así que el envío Premium lo pone nuestra app.
- **Corrección:** Saleor **guarda los envíos en caché**. El BFF tiene que llamar a `deliveryOptionsCalculate` al identificar al usuario y antes de cerrar la compra, o Premium y clubs se aplicarán con datos viejos. La PoC ya prueba este caso (riesgo 7 de la plantilla).

### E9 · El panel, usado como lo haría alguien no técnico
- **Pregunta:** ¿puede el equipo de operaciones abrir un país, poner precios y lanzar una campaña sin ayuda técnica?
- **Qué se hizo:** `prueba-panel.mjs` usa el Dashboard con un navegador automatizado (Playwright). La promoción se hizo **a mano**, con capturas en `panel/promocion-manual/`.
- **Qué salió:**
  - Crear el canal son **3 clics**: la moneda se rellena sola y sale con IVA incluido, pero **inactivo**.
  - Los precios se ponen en una tabla tipo Excel con una columna por país.
  - ⚠️ Si se marca "Disponible" sin escribir precio, **se guarda a 0 €**.
  - Las promociones van **una regla por país**, con desplegables sin etiqueta y el valor en EUR por defecto en vez de %.
- **Conclusión:** bloque 4 (🟡). Sirve para el día a día, pero hay que evitar los 0 € y formar al equipo en las promociones.
- **Corrección (canales inactivos):** la plantilla decía que desde el panel los canales nacían activos. Falso: el canal `fr` de la prueba tiene `is_active = false`.
- **Corrección (el "fallo de beat"):** la versión anterior decía que *"el recálculo de promociones se para y no hemos encontrado la causa"*. **La causa era nuestra configuración:**
  1. **Síntoma:** la promoción no se aplicaba hasta reiniciar `beat`. Pasó 4 veces, también en una instalación nueva.
  2. **Pista:** el log de `beat` mostraba que enviaba **todas** sus tareas una vez al arrancar y ninguna después. No era algo de las promociones.
  3. **Diagnóstico:** se lanzó un segundo `beat` con logs de depuración. La tarea de promociones decía `is_due=True` (le toca) y aun así no se enviaba, y beat se despertaba cada 60 s, el intervalo de otra tarea (`update-products-search-vectors`), que usa una **planificación propia de Saleor**.
  4. **Causa, en el código de Saleor:** `saleor/schedulers/schedulers.py` explica que el planificador por defecto de Celery tiene un fallo. Si la primera tarea de la cola dice "todavía no", no mira las demás, y *"the worker will be stuck forever"*. Saleor trae uno corregido que se activa con `--scheduler saleor.schedulers.schedulers.PersistentScheduler`, y nuestro `docker-compose.yml` no lo usaba. Tampoco lo usa el oficial `saleor-platform`, de donde se copió.
  5. **Solución y comprobación:** con `--scheduler`, beat envía las tareas cada 30 s, y la prueba del panel da **6/6** (precio rebajado en menos de 2 minutos) en las 8 ejecuciones siguientes (la última, en una instalación nueva). ⚠️ La **primera** ejecución justo después del cambio sí falló, y no se ha podido explicar: la promoción se procesó, pero el precio no se recalculó hasta marcar el producto como pendiente a mano. Por eso se mantiene la recomendación de vigilar en producción que los precios rebajados se recalculan.
  6. **Descartado:** se sospechó que el canal inactivo o el producto sin publicar impedían el recálculo. Un experimento con las cuatro combinaciones (`PREPARAR=canal`, `producto`, ambos o ninguno) dio 6/6 en todas, así que no influyen.
- **Repetir:** sección 8, "Prueba del panel".

### E10 · Webhooks por dentro (leyendo el código)
- **Pregunta:** ¿qué garantías da Saleor al avisar a nuestras apps?
- **Qué se hizo:** leer `webhook/transport/` dentro del contenedor.
- **Qué salió:**
  - Los asíncronos se reintentan **5 veces con espera exponencial desde 10 s** (`retry_backoff=10`, `max_retries=5`).
  - Los síncronos esperan **18 s** como máximo.
  - Se pueden mandar a **SQS** en vez de por HTTP.
  - Solo se guardan las entregas que fallan.
- **Conclusión:** bloque 6. La entrega es "al menos una vez", así que un aviso **puede llegar repetido** y la API Django tiene que ser idempotente: si recibe dos veces el gasto de Teemis del mismo pedido, solo lo descuenta una.
- **No demostrado:** los reintentos se han leído en el código, no se han provocado.

### E11 · Configuración del core (leyendo `settings.py` y probando)
- **Qué salió:**
  - **Sentry** nativo (`SENTRY_DSN`).
  - Medios en **S3** (`AWS_MEDIA_BUCKET_NAME`).
  - **Réplica de lectura** de Postgres (`DATABASE_URL_REPLICA`).
  - Trazas OpenTelemetry (se ven en Jaeger).
  - La imagen arranca con **`DEBUG = True`**, y por eso los errores de la API incluyen la traza de Python.
  - Un **token inválido no da error**: Saleor trata la petición como anónima (`{ me { email } }` devuelve `null`).
- **Conclusión:** bloques 1, 2 y 6 (Sentry, S3, escalado). En producción hay que poner `DEBUG=False`.

### E12 · Numeración de pedidos y facturas
- **Qué salió:**
  - El número de pedido sale de **una única secuencia global** (`order_order_number_seq`, en `order/models.py`), sin series por país.
  - `invoiceCreate` acepta **número y URL externos**.
  - La app oficial de facturas **se eliminó** del repositorio en agosto de 2024 (commit *Remove Invoices app from monorepo #1496*).
- **Conclusión:** bloque 3. La numeración `FR-0001` y la factura legal las tiene que poner **Business Central**, y Saleor solo guarda la referencia.
- **Corrección:** la plantilla decía que la app de facturas "era muy básica, solo en inglés". Ya no existe.

### E13 · Índices de las consultas críticas
- **Qué salió:**
  - Índices únicos por `(variant_id, channel_id)` y `(product_id, channel_id)`.
  - **GIN en `metadata`** de producto y pedido, así que el filtro por club tiene índice.
  - Pedidos indexados por `user_id`, `user_email` y `channel_id`.
- **Conclusión:** bloque 8 (🟢).
- **Repetir:**
  ```bash
  $SQL "select tablename, indexname from pg_indexes where tablename in ('product_product','order_order') and indexdef like '%gin%'"
  ```

### E14 · Afirmaciones de documentación (contrastadas el 23/10/2026)
| Afirmación | Fuente | Resultado |
|---|---|---|
| Cloud: Select 1.599 $/mes (≤200k $ GMV, 0,8 %), Volume 3.999 $ (≤1M $, 0,4 %), Enterprise desde 0,2 % | [saleor.io/pricing](https://saleor.io/pricing) | ✅ Coincide |
| Regiones UE: Irlanda (principal) y Francia (secundaria); sin compartir datos con EE. UU. | [docs: regions](https://docs.saleor.io/cloud/regions) | ✅ Coincide |
| App de Stripe: sin Stripe Checkout, una sola captura, la configuración no se edita, requiere 3.23 | [docs: Stripe](https://docs.saleor.io/developer/app-store/apps/stripe/overview) | ✅ Coincide |
| App de Stripe: métodos de pago | [docs: métodos soportados](https://docs.saleor.io/developer/app-store/apps/stripe/supported-payment-methods) | **Corrección:** solo tarjeta, Apple Pay, Google Pay, Klarna, PayPal, SEPA, ACH y Link. La plantilla decía "los métodos activados en Stripe". El 3DS solo lo menciona la [ficha comercial](https://apps.saleor.io/apps/stripe) |
| Apps SMTP y Products feed | README de cada app en [saleor/apps](https://github.com/saleor/apps) | **Corrección:** las dos están **obsoletas**. La sustituta de SMTP (Customer Emails) **solo funciona en Saleor Cloud** |
| Casos de éxito (Lush, Breitling, PCDIGA, Kencove…; Butterfly Network, Seven Cells, TBD Health y Yuno en *Subscriptions*) | [saleor.io/case-study](https://saleor.io/case-study) | ✅ Coincide |
| Business Central trae conector nativo con Shopify | [Microsoft Learn](https://learn.microsoft.com/en-gb/dynamics365/business-central/shopify/shopify-connector-overview) | ✅ Coincide (solo BC online) |
| No hay chart de Helm oficial | [docs: Kubernetes](https://docs.saleor.io/setup/deploy-kubernetes) | ✅ Solo de la comunidad |
| Repositorio desde 2013, 23,5k ⭐; apps oficiales con su último release el 19/10/2026 | API de GitHub | ✅ Coincide |

### Estimaciones (no son experimentos)
- **Coste de AWS (≈ 450–650 $/mes):** se dimensionó cada pieza (2 contenedores de API, worker y beat, tienda, 3 apps, RDS Multi-AZ, ElastiCache, balanceador, S3 y CloudFront) y se le puso un precio aproximado de eu-west-1. El desglose está en `informe/06-transversales.md` (6.6). Hay que pasarlo por la calculadora de AWS.
- **Esfuerzo (≈ 145–220 días-persona):** rangos por bloque de trabajo (tienda y checkout, app de precios, Premium, BC, identidad, migración, CMS, infraestructura, QA), con el mismo desglose. Es la parte menos fiable del informe y la tiene que revisar quien lo vaya a construir.

---

## 6. De dónde sale cada respuesta de la plantilla
Cómo se decidió cada valoración. El criterio de la plantilla es 🟢 resuelto de serie · 🟡 posible con desarrollo a medida · 🔴 no viable.

| Bloque de la plantilla | Valoración | Por qué | Experimentos y fuentes |
|---|---|---|---|
| **1 · Arquitectura de código** | 🟢 | La lógica propia va en apps aparte, sin tocar Saleor, así que actualizar no rompe nuestro código. API versionada, y Sentry y trazas de serie | E1, E3, E11 + documentación de apps |
| **2 · Infraestructura** | 🟡 | Imágenes Docker estándar que encajan en AWS, una instancia para todos los países. Pero son 4 piezas de Saleor más las nuestras, no hay Helm oficial y beat necesita el `--scheduler` correcto | E1, E9 (planificador), E11, E14 + estimación de coste |
| **3 · Personalización funcional** | 🟡 | Los Teemis son viables con un mecanismo oficial (E4). Premium, cupones por rol (E8), packs y numeración por país (E12) son desarrollo propio | E3, E4, E8, E10, E12 |
| **4 · UI y CMS** | 🟡 | La tienda es 100 % nuestra (control total, pero todo es desarrollo). El panel sirve con matices (E9). El contenido editorial necesita un CMS aparte | E6, E9 + documentación de la app CMS |
| **5 · Plugins / apps** | 🟡 | Unas 10 apps oficiales. Suscripciones, packs, wishlist, Mailchimp y 2FA no tienen app, y las apps de email y feed están obsoletas | E14 + README de `saleor/apps` |
| **6 · Integraciones** | 🟡 | Stripe (con métodos limitados), Sentry y S3 de serie. Business Central, Teemis e identidad son a medida y es lo más caro | E4, E10, E11, E14 |
| **7 · Multitenant** | 🟢 país / 🟡 club | País de serie (E2, E5, E6). Club solo con nuestra app (E7) y con el hueco de los productos sin envío | E2, E3, E5, E6, E7, E8 |
| **8 · Base de datos** | 🟢 | Postgres relacional, multipaís por columna, índices adecuados y `metadata` para datos propios | E2, E12, E13 |
| **PoC mínima** | 4 de 5 hechas | Falta el pago con Stripe (no hay claves de test) | E1, E4, E5, E7, E8 |
| **Recomendación** | ⚠️ Seguir con reservas | Lo crítico (país y Teemis) está demostrado. El coste de construir lo propio de Toteemi es alto y hay que compararlo con Medusa y Shopify Plus | Todo lo anterior |

---

## 7. Levantar Saleor en local
**Requisitos:**
- **Docker Desktop u OrbStack**, con al menos **5 GB de RAM** para Docker.
- **Python 3.10 o superior**, para los scripts.
- **Node 20 o superior**, para la prueba del panel.
- Puertos libres: **5432, 8000, 9000, 8025, 16686** y **8765**. Si el 5432 está ocupado, cambia `POSTGRES_HOST_PORT` en `.env`.

```bash
cd saleor
cp .env.example .env              # solo la primera vez
docker compose up -d              # la primera vez descarga ~2-3 GB de imágenes
docker compose ps                 # "migrate" debe salir Exited (0) y el resto Up

# Datos de ejemplo + superusuario admin@example.com / admin (cada vez que empieces de cero)
docker compose exec api python3 manage.py populatedb --createsuperuser
```
**Qué pasa por dentro:**
1. Arranca Postgres, y su *healthcheck* avisa cuando acepta conexiones.
2. `migrate` crea las 148 tablas y termina.
3. Solo entonces arrancan `api`, `worker` y `beat`.
4. `populatedb` carga productos de ejemplo, 2 canales (USD y PLN), almacenes, zonas de envío y **promociones al azar**, que pueden afectar a algunos productos.

| Qué | URL | Acceso |
|---|---|---|
| Panel de administración (Dashboard) | http://localhost:9000 | `admin@example.com` / `admin` |
| API GraphQL (con *playground*) | http://localhost:8000/graphql/ | — |
| Emails que envía Saleor (Mailpit) | http://localhost:8025 | — |
| Trazas (Jaeger) | http://localhost:16686 | — |

**Alternativa, Dev Container (VS Code):** abre `saleor/` → `Cmd+Shift+P` → **Dev Containers: Reopen in Container**. Añade un contenedor `workspace` (Node 22, pnpm y `psql`) en la misma red, para desarrollar apps con acceso a `api:8000` y `db:5432`. El `populatedb` se lanza desde el Mac.

### Por qué el `docker-compose.yml` no es el oficial tal cual
Está basado en [saleor-platform](https://github.com/saleor/saleor-platform), con estos cambios:

| Cambio | Por qué |
|---|---|
| Servicio **`migrate`** del que dependen `api`, `worker` y `beat` | La API no arranca con la BD sin migrar (evita el error *relation does not exist*) |
| **Healthcheck** en Postgres | Para que `migrate` no se conecte antes de tiempo |
| Puertos solo en **`127.0.0.1`** | La BD, con contraseña `saleor`, no queda expuesta a la red wifi |
| **Versiones fijadas** | Que el entorno sea reproducible |
| **`beat` aparte y con `--scheduler saleor.schedulers.schedulers.PersistentScheduler`** | Con el planificador por defecto de Celery (también con `worker -B`, como en el oficial) las tareas periódicas solo se ejecutan una vez y las promociones no se aplican (E9) |
| `HTTP_IP_FILTER_ENABLED=False` en `.env` | Para que Saleor pueda llamar a los webhooks de tu Mac (`host.docker.internal`). **En producción, `True`** |

## 8. Repetir las pruebas
Desde la raíz del repo, con el stack levantado y los datos cargados:

| Script | Experimentos | Resultado esperado | Qué deja en la BD |
|---|---|---|---|
| `python3 saleor/verificacion/verificar.py` | E2–E4 | **22/22** | Un pedido de 0 € por ejecución |
| `python3 saleor/verificacion/poc_plantilla.py` | E5–E8 | **16/16** | Canales `poc-es` y `poc-fr`, el tipo de cliente del club y 3 clientes (se rehacen en cada ejecución) |
| `cd saleor/verificacion/panel && npm run prueba` | E9 | **6/6** | Canal `fr` y la promoción "Prueba panel France" (se rehacen en cada ejecución) |

Si faltan los datos de ejemplo, los scripts lo dicen y dan el comando. Terminan con código 1 si algo falla, y borran las apps temporales que crean.

### Comprobación a mano de la PoC (E5, E7 y E8)
1. En **otra terminal**: `python3 saleor/verificacion/poc_plantilla.py --esperar`. Hace las comprobaciones y deja la app instalada. Muestra su **token** y los **ids de los clientes**, e imprime cada webhook que recibe hasta que pulses Intro.
2. Busca el id de una variante: `$API '{"query":"{ product(slug: \"ascii-tee\", channel: \"poc-es\") { variants { id name } } }"}'`. El slug no es el nombre: "Monospace Tee" es `ascii-tee`.
3. Crea checkouts anónimos con `checkoutCreate` en `poc-es` o `poc-fr`. En España la dirección necesita `countryArea`.
4. Para un cliente concreto, crea el checkout con `-H 'authorization: Bearer <token>'`, únele el cliente con `checkoutCustomerAttach` y, si ya habías pedido los envíos, recalcúlalos con `deliveryOptionsCalculate`.
5. Mira las llamadas en Jaeger: *Service* `saleor` → *Operation* `webhooks.checkout_filter_shipping_methods`.

### Prueba del panel
```bash
cd saleor/verificacion/panel
npm install && npx playwright install chromium   # solo la primera vez
PAIS=France SLUG=fr npm run prueba
PREPARAR=canal,producto npm run prueba            # variante del experimento E9: activa canal y publica antes
```
Deja capturas en `panel/capturas/`. Es frágil por diseño: depende de la maquetación del Dashboard 3.23, porque la tabla de variantes es un canvas y se pulsa por coordenadas.

## 9. Explorar la base de datos con DBeaver
1. **Database → New Database Connection → PostgreSQL.** Host `localhost`, puerto `5432`, BD `saleor`, usuario y contraseña `saleor` / `saleor` → **Test Connection → Finish**.
2. Diagrama ER legible: selecciona solo `channel_channel`, `product_product`, `product_productvariant`, `product_productchannellisting`, `product_productvariantchannellisting`, `discount_promotion`, `discount_promotionrule`, `discount_promotionrule_channels`, `checkout_checkout`, `checkout_checkoutline` y `discount_checkoutlinediscount` → clic derecho → **View Diagram**.
3. **SQL Editor → Open SQL script** → `saleor/sql/consultas-dbeaver.sql`:

| Pregunta | Dónde | Consulta |
|---|---|---|
| ¿Cómo se representa un país? | `channel_channel` | 1 |
| ¿Dónde está el precio por país? | `product_productvariantchannellisting.price_amount` | 2 |
| ¿Cómo tiene cada país un catálogo distinto? | Hay o no fila en `product_productchannellisting` | 3, 4 |
| ¿Cómo se limita una promoción a un país? | `discount_promotionrule_channels` | 5 |
| ¿Dónde se precalcula el precio rebajado? | `product_variantchannellistingpromotionrule` | 6 |
| ¿Cómo varía un voucher por país? | `discount_voucherchannellisting` | 7 |
| ¿Dónde aplica nuestra app el precio con Teemis? | `checkout_checkoutline.price_override` | 8 |
| ¿Qué descuentos tiene una línea? | `discount_checkoutlinediscount` | 9 |

## 10. Comandos útiles y problemas conocidos
```bash
cd saleor
docker compose logs -f api worker beat   # ver logs
docker compose stop                      # parar sin borrar datos
docker compose up -d                     # volver a arrancar
docker compose down -v                   # ⚠️ borra todo, incluida la BD. Después: up -d y populatedb
```
- **Las promociones no se aplican:** comprueba que `beat` arranca con `--scheduler saleor.schedulers.schedulers.PersistentScheduler`. En el log tiene que salir `scheduler -> saleor.schedulers.schedulers.PersistentScheduler` (E9).
- **Precio 0 € por despiste:** marcar "Disponible" en el panel sin escribir precio lo guarda a 0 € (E9).
- **Los canales nuevos nacen inactivos**, por API y desde el panel. Hay que activarlos antes de vender (E9).
- **Un webhook síncrono no llega:** a la app le falta el permiso que pide el evento y Saleor no avisa (E7).
- **Envíos en caché:** tras identificar al usuario y antes de cerrar, llama a `deliveryOptionsCalculate` (E8).
- ***PermissionDenied* sin motivo aparente:** revisa el token. Si no es válido, Saleor te trata como anónimo sin avisar (E11).
- **Trazas de Python en los errores:** es el modo depuración. En producción, `DEBUG=False` (E11).
- **Un producto cuesta menos de lo esperado:** `populatedb` crea promociones al azar (E4).

## 11. Qué no está demostrado y qué queda pendiente
- **Pago con Stripe:** no se ha probado (faltan claves de test). Tampoco está confirmado el 3DS.
- **Recálculo automático de los Teemis al cambiar el carrito** (`CHECKOUT_UPDATED`): el webhook existe, pero no se ha probado con una app real.
- **Reintentos de webhooks:** leídos en el código, no provocados.
- **Inicio de sesión con la cuenta Toteemi** (OIDC o BFF): no probado.
- **2FA del staff mediante el proveedor de identidad:** no probado.
- **Que Meta acepte el feed** de productos: no probado.
- **Las estimaciones** de coste y esfuerzo: opinión, a revisar con el equipo.
- **Las dudas de negocio** de la plantilla ("Dudas abiertas").
- Comparar con los spikes de Medusa y Shopify Plus.
