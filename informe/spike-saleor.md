## Description

<aside>
🎯

**Objetivo:** evaluar si **Saleor** es una alternativa viable a WordPress + WooCommerce para la apertura internacional de la tienda (ES → FR → más países), tanto para construirla como para mantenerla. Es uno de tres spikes paralelos (Medusa, Saleor, Shopify Plus) que siguen **la misma plantilla**, para poder comparar los resultados lado a lado.

</aside>

**Cómo rellenar esta plantilla**

- Marca cada checkbox cuando el punto esté investigado, aunque la respuesta sea "no se puede".
- Escribe lo que encuentres en el recuadro ✍️ de cada bloque y enlaza docs, repos, issues o pruebas.
- Cierra cada bloque con una valoración: 🟢 resuelto de serie · 🟡 posible con desarrollo a medida · 🔴 no viable / bloqueante.
- Lo que no se pueda cerrar va a "Dudas abiertas"; no lo des por supuesto.
- Referencia del enfoque WordPress multisite: `US/in_progress/US_apertura_internacional.md`.

<aside>
🧭

**Pistas para arrancar con Saleor:** Python / Django con API GraphQL (el mismo stack que `toteemi-api`). Conceptos a revisar: Channels, Warehouses, Shipping zones, Promotions y Vouchers, Apps (extensiones externas con webhooks síncronos y asíncronos), Dashboard extensions, Metadata, Tax apps. El storefront es headless (starter de Next.js). Usa PostgreSQL. Comprobar qué parte es open source y qué es Saleor Cloud.

</aside>

<aside>
🔬

**Cómo se ha comprobado:** Saleor **3.23.44** (20/10/2026) en local con Docker, instalado desde cero el 23/10/2026. Lo marcado como **(verificado)** se repite con tres scripts del repo de la investigación (`saleor/verificacion/`):
- `verificar.py`: esquema, API y descuento con Teemis (**22/22**).
- `poc_plantilla.py`: PoC de esta plantilla, con ES/FR, club y envío Premium (**14/14**).
- `panel/prueba-panel.mjs`: uso del panel con un navegador automatizado (**5/6**; el fallo es un problema real de Saleor, ver bloque 2).

</aside>

### Casos de Toteemi de referencia

Son los casos reales con los que hay que contrastar cada bloque:

- **Descuento con Teemis:** el usuario paga parte del pedido con su saldo de Teemis. El saldo vive en la API (Django) y es global para todos los países.
- **Cupones por rol:** cupones exclusivos para premium, envío gratis para premium.
- **Suscripción Premium:** alta, renovación y cancelación, con cambio de rol del usuario (hoy WooCommerce Subscriptions).
- **Clubs:** el catálogo que ve un usuario depende del club al que pertenece.
- **Facturación correlativa por país** y sincronización de facturas con Business Central.
- **Gestión de usuarios desde la API Django:** alta, anonimización, reset de contraseña y dirección de facturación.
- **Envíos por peso y código postal**, packs/bundles de productos y wishlist.

## Puntos a evaluar

### 1 · Arquitectura de código

- [x]  Lenguaje, framework y versión; madurez del proyecto (antigüedad, ritmo de releases, breaking changes entre majors)
- [x]  Licencia y modelo (open source / open core / SaaS) y su impacto en nuestro código
- [x]  Dónde vive nuestra lógica a medida (módulos, plugins, apps, extensiones) y cómo se versiona
- [x]  Modelo de extensión (hooks, eventos, workflows, webhooks): ¿se puede extender sin forkear el core?
- [x]  API expuesta (REST / GraphQL, admin / storefront), autenticación y límites
- [x]  Headless o monolito: ¿el storefront va separado? ¿qué starter ofrece?
- [x]  Encaje con nuestra arquitectura por capas (domain / application / infrastructure) y con el stack del equipo
- [x]  Testing de la lógica propia (unit / e2e), entorno local y fixtures
- [x]  Cómo se actualiza el core y cuánto rompe el código propio
- [x]  Observabilidad: Sentry, logs, trazas

<aside>
✍️

**Hallazgos:**
- **Stack:** Python 3.12, Django 5.2 y API GraphQL, ejecutado con uvicorn y Celery para tareas en segundo plano (verificado en el contenedor). El repositorio existe desde 2013, tiene 23,5k ⭐ y saca varias releases por semana. Se mantienen dos líneas a la vez (3.22.x y 3.23.x). La 3.x es estable desde hace años, sin cambio de major, y la API avisa de lo que va a desaparecer (*deprecation*) antes de quitarlo.
- **Licencia:** BSD-3, sin *open core*: el código de Saleor Cloud es el mismo. Cloud es solo el alojamiento gestionado, sin funciones exclusivas. Nuestro código no queda atado a la licencia.
- **Dónde va nuestra lógica:** en **Apps**, que son **servicios aparte** (en cualquier lenguaje; el SDK oficial es TypeScript). Cada app se instala con un token de permisos concretos y recibe webhooks. **No se forkea ni se toca el core**, y cada app se versiona y despliega en su propio repo. Aún existen "plugins" Python dentro del core (OIDC, AvaTax…), pero Saleor los considera *legacy* y no conviene escribir plugins nuevos.
- **Extensión:**
  - Webhooks asíncronos (pedido creado, pagado, reembolsado, checkout actualizado…).
  - Webhooks síncronos: impuestos, pagos, y listar y filtrar métodos de envío (verificado).
  - Precio de línea sobrescrito desde una app.
  - Extensiones del Dashboard: iframes en la ficha de producto, pedido o cliente.
  - ⚠️ No hay webhook síncrono para "calcular descuento" ni para "validar el checkout antes de cerrarlo" (verificado).
- **API:** solo GraphQL, la misma para la tienda y para el admin, con los permisos controlados por token. Autenticación con JWT (acceso de 5 min por defecto), tokens de app o un proveedor externo (plugin OIDC). Cada consulta tiene un límite de coste ("query cost", máximo 50.000 en local).
- **Headless:** la tienda va aparte y la hacemos nosotros. El punto de partida es la tienda de referencia en Next.js (`saleor/storefront`).
- **Encaje con el equipo:** el core es Django como `toteemi-api`, pero **no programaríamos dentro del core**. Las apps pueden ser Django y seguir domain / application / infrastructure; Saleor quedaría como un adaptador de infraestructura (cliente GraphQL más receptor de webhooks). Sin SDK en Python hay que implementar nosotros la verificación de firma de los webhooks (JWS) y el *manifest* de la app.
- **Testing:**
  - La lógica de las apps se prueba con tests unitarios sin depender de Saleor.
  - Los e2e van contra el stack local de Docker, como hacen ya `verificar.py` y `poc_plantilla.py`.
  - Datos de prueba: `populatedb` y, para la configuración de canales, Saleor Configurator (YAML).
  - El panel se puede probar con Playwright, aunque es frágil porque la tabla de variantes es un canvas.
- **Actualizar:** se cambia la versión de la imagen Docker y se aplican las migraciones (en local lo hace solo el servicio `migrate`). Como las apps hablan por la API versionada, una actualización solo les afecta si eliminan un campo que ya estaba marcado como obsoleto.
- **Observabilidad:**
  - **Sentry nativo** en el core: basta con la variable `SENTRY_DSN` e integra Django y Celery (verificado en `settings.py`).
  - **Trazas OpenTelemetry** nativas: verificado con Jaeger en local.
  - Logs a la salida estándar.
  - Las apps y la tienda llevan su propio SDK de Sentry.

**Valoración:** 🟢 — Extensión desacoplada del core, actualizaciones que no rompen nuestro código, y Sentry y trazas de serie.

</aside>

### 2 · Infraestructura necesaria y optimizaciones

- [x]  Componentes necesarios: servidor de aplicación, workers, BD, Redis, colas, buscador, almacenamiento de medios
- [x]  Encaje con la infra actual (AWS, EKS, Terraform, GitLab CI)
- [x]  Varios países: ¿una instancia o una por país?
- [x]  Escalado horizontal y gestión del estado (sesiones, caché, jobs)
- [x]  Caché y CDN (storefront, imágenes) y rendimiento esperado
- [x]  Jobs programados (crons) y tareas asíncronas
- [x]  Backups, restore y entornos (local, staging, prod)
- [x]  Coste estimado (licencia / plan + infra + apps de pago), para 1 país y para N países
- [x]  Coste operativo: quién mantiene qué, upgrades, parches de seguridad

<aside>
✍️

**Hallazgos:**
- **Componentes de Saleor:**
  - `api`: GraphQL, sin estado.
  - `worker`: Celery.
  - `beat`: el planificador de tareas periódicas; solo puede haber uno.
  - PostgreSQL.
  - Redis/Valkey: caché y cola de Celery.
  - Almacenamiento de medios en **S3 nativo** (`AWS_MEDIA_BUCKET_NAME`, verificado en `settings.py`).
  - Buscador: sin buscador aparte, porque usa la búsqueda de Postgres. Para algo mejor hay app oficial de Algolia.
- **Componentes nuestros:** la tienda Next.js y 2 o 3 apps (precios/Teemis, conector de Business Central y Stripe).
- **Encaje con la infra actual:** son imágenes Docker, así que encajan en EKS, Terraform y GitLab CI. Las piezas gestionadas serían RDS, ElastiCache y S3 + CloudFront. **No hay chart de Helm oficial**: los que hay son de la comunidad y Saleor no los soporta, así que lo normal es escribir los manifiestos nosotros. Opcionalmente, los webhooks se pueden mandar a **SQS** en vez de por HTTP (soportado en el core).
- **Varios países:** **una sola instancia**, con un canal por país.
- **Escalado:** `api` y `worker` escalan horizontalmente. Sesiones con JWT y estado en Postgres y Redis. Postgres admite réplica de lectura (`DATABASE_URL_REPLICA`).
- **Caché y CDN:** imágenes por CloudFront. El catálogo se cachea en la tienda (ISR de Next.js). Los precios rebajados por promociones se **precalculan**, así que leer el catálogo es barato.
- **Jobs:** Celery para tareas y webhooks asíncronos. `beat` recalcula promociones y precios rebajados cada 30 s. ⚠️ **En local, beat deja de lanzar ese recálculo** después de la primera vez, y una promoción nueva no se aplica hasta reiniciarlo. Se ha reproducido 3 veces, la última **en una instalación nueva** (la prueba del panel espera 2 min y sigue en 24,95 €; tras `docker compose restart beat` baja a 19,96 € en menos de 10 s). No he encontrado la causa ni una incidencia publicada. En producción haría falta una **alerta si los precios rebajados no se recalculan**.
- **Backups:** RDS con recuperación a un punto en el tiempo. Para los entornos, la configuración (canales, impuestos, envíos) se lleva como código con Saleor Configurator, de modo que staging y producción se configuran igual.
- **Coste (orden de magnitud, sin validar con la calculadora de AWS):**
  - **Self-hosted en AWS:** ≈ **450–650 $/mes** para 1 país, **y casi igual para N**, porque un país más es configuración y no infraestructura.
  - **Saleor Cloud:** desde **1.599 $/mes** (hasta 200k $ de GMV al mes y 0,8 % por encima), o 3.999 $/mes hasta 1M $. A eso se suman la tienda y las apps, que se alojan aparte.
  - **Licencia:** 0 €.
  - **Apps de pago:** solo AvaTax si se quisiera (Avalara cobra aparte), además de las comisiones de Stripe.
- **Coste operativo:**
  - **Self-hosted:** el equipo aplica las actualizaciones, que salen a diario o casi y suelen incluir seguridad. Ya está automatizado con la imagen y el servicio `migrate`. Las apps propias y la tienda son mantenimiento nuestro en cualquier caso.
  - **Saleor Cloud:** Saleor opera el core y da soporte. Regiones en la UE: Irlanda (eu-west-1) y Francia (eu-west-3) como secundaria.

**Valoración:** 🟡 — La infraestructura es estándar y encaja en AWS. Pero son 4 piezas de Saleor más las nuestras, y el fallo del planificador obliga a monitorizarlo.

</aside>

### 3 · Personalización funcional (lógica de negocio)

- [x]  Descuento con Teemis: saldo externo leído de la API Django, aplicado en carrito/checkout y consumido de forma idempotente
- [x]  Cupones restringidos por rol o segmento (solo premium, envío gratis premium…)
- [x]  Reglas de descuento a medida que se puedan combinar con cupones y promociones
- [x]  Suscripción Premium: alta, renovación, cancelación y cambio de rol
- [x]  Packs/bundles y envíos por peso y código postal
- [x]  Numeración de pedidos y facturas correlativa por país (por ejemplo, prefijo `FR-`)
- [x]  Puntos de extensión del checkout: validaciones, campos extra, pasos
- [x]  Qué se resuelve configurando desde el admin y qué exige código

<aside>
✍️

**Hallazgos:**
- **Descuento con Teemis (verificado):**
  - **Cómo se aplica:** nuestra app, con permiso `HANDLE_CHECKOUTS`, lee el saldo en la API Django y **sobrescribe el precio de cada línea** del checkout (`checkoutLinesUpdate` con `price`), respetando el máximo de Teemis de cada producto y país.
  - **Probado:**
    - Un producto de 45 baja a 40.
    - El cliente o el staff **no pueden** hacerlo; solo la app.
    - **Un producto pagado al 100 % con Teemis** deja el total a 0 y el pedido se crea **sin pasar por el pago**.
  - **Recálculo:** se recalcula con el webhook `CHECKOUT_UPDATED`, lo que arregla el actual "¿Has modificado el carrito? Recalcula tu ahorro".
  - **Idempotencia:** los webhooks asíncronos se reintentan **5 veces con espera exponencial** desde 10 s (verificado en el código), así que pueden llegar duplicados. El `SPENT_STORE` en la API Django tiene que ser idempotente, usando como clave el id del pedido.
  - **Saldo:** entre aplicar y pagar el saldo puede cambiar, así que hay que reservarlo o volver a validarlo al cerrar.
  - **IVA:** el precio sobrescrito se interpreta igual que el resto del canal, por eso los canales tienen que ir con precios con IVA incluido (verificado).
- **Cupones por rol:**
  - **Qué permite el voucher:** **no se puede limitar a un rol o segmento**. Solo admite `onlyForStaff`, un uso por cliente, uso único, países y límite de usos (verificado en el esquema). Los "tipos de cliente" nuevos de la 3.23 **no los usan ni vouchers ni promociones** (verificado).
  - **Envío gratis Premium (verificado):** nuestra app responde al webhook síncrono `SHIPPING_LIST_METHODS_FOR_CHECKOUT` y añade "Envío gratis Premium" a 0 € solo si el cliente es Premium. Un cliente no Premium no lo ve.
  - **Cupones "solo Premium":** códigos de un solo uso que genera la app para cada usuario Premium. La otra opción es que la app los quite si un no Premium los aplica, pero sería asíncrono.
- **Combinar reglas:** de las promociones de catálogo gana la que más descuenta; las de pedido van sobre el precio ya rebajado; un voucher anula las promociones de pedido; voucher y promoción **se aplican después del precio que fija nuestra app**. ⚠️ Para que no se rompa el precio mínimo (precio base − máximo de Teemis), la app tiene que tenerlos en cuenta, o el negocio decide que Teemis y cupones no se combinan.
- **Suscripción Premium:** ❌ **no hay suscripciones en Saleor**. La propuesta es **Stripe Billing** fuera de Saleor (alta en Stripe Checkout y gestión en el *Customer Portal*), y un webhook de Stripe que hace que la API Django cambie el rol. Hay que migrar las suscripciones activas de WooCommerce.
- **Packs y envíos:**
  - **Packs/bundles:** ❌ no existen (verificado: no hay tipos "bundle" en el esquema). Se modelan como producto propio con stock gestionado por una app, o como producto independiente.
  - **Envíos por peso y código postal:** ✅ nativos, con zonas, tarifas por peso o importe y reglas de inclusión o exclusión por CP (por ejemplo, Ceuta y Melilla).
- **Numeración:**
  - **Pedidos:** el número sale de **una secuencia global única** (`order_order_number_seq`, verificado), **sin prefijo ni serie por país**. Un "FR-0001" iría en `metadata` del pedido o lo pondría Business Central.
  - **Facturas:** `invoiceCreate` acepta número y URL externos, así que **la numeración correlativa por país la lleva Business Central** y Saleor guarda la referencia (ver bloque 6).
- **Checkout:**
  - Se pueden guardar campos extra en `metadata` y nota del cliente.
  - Los pasos los define nuestra tienda.
  - **Validaciones que bloquean de verdad:** solo las de envío. Si el webhook síncrono `CHECKOUT_FILTER_SHIPPING_METHODS` quita los métodos de envío, el checkout no se puede cerrar (verificado, ver bloque 7).
  - El resto de validaciones las hace el BFF de la tienda. ⚠️ La API pública permite saltarse el BFF, así que lo que de verdad importa (precio y Teemis) solo puede cambiarlo la app.
- **Admin frente a código:**
  - **Desde el panel:** precios por país, promociones y vouchers por país, envíos, impuestos, traducciones y gift cards.
  - **Con código:** Teemis, precio y envío Premium, clubs, suscripciones, packs, serials y Business Central.

**Valoración:** 🟡 — Teemis viable con un mecanismo oficial, pero Premium, clubs, cupones por rol y packs son desarrollo propio o servicio externo.

</aside>

### 4 · Personalización de la UI y CMS

- [x]  Cómo se construye el storefront (tema, framework, starter) y qué parte es código
- [x]  Qué puede editar una persona no técnica sin deploy: páginas, textos, imágenes, banners, colores/branding, menús
- [x]  CMS integrado o externo (Strapi, Payload, Sanity, Contentful, Storyblok…) y cómo se conecta al storefront
- [x]  Contenido por país e idioma desde el CMS
- [x]  Preview, borradores y publicación programada
- [x]  Si se pueden reutilizar nuestros web components (Lit) o el diseño actual
- [x]  SEO: URLs, metadatos, hreflang, sitemaps y redirecciones desde la tienda actual
- [x]  Rendimiento y accesibilidad del storefront

<aside>
✍️

**Hallazgos:**
- **Tienda:** **es 100 % código nuestro**. Se parte de la tienda de referencia en Next.js (`saleor/storefront`). No hay temas ni editor visual. El "tema por país" es configuración de nuestra tienda; puede leerse de `channel.metadata`.
- **Sin deploy, desde el panel de Saleor:** productos, imágenes, precios, disponibilidad por país, promociones, **menús** (`menu_*`, traducibles) y **páginas** simples (tipo y atributos, sin maquetación).
  - **Prueba del panel (verificado):**
    - Crear un país son 3 clics: la moneda se rellena sola y el canal sale con IVA incluido.
    - Los precios por país se ponen en una tabla tipo Excel.
    - ⚠️ Si se marca un producto como disponible sin escribir precio, **se guarda a 0 €**.
    - Las promociones van una regla por país, y los desplegables de la condición no tienen etiqueta.
  - Banners, colores y textos de marketing necesitan un CMS.
- **CMS:** externo. Hay una **app oficial "CMS"** que sincroniza productos con Contentful, Strapi, DatoCMS, Builder.io o Payload. La web corporativa (La App, Premium, Empresas…) tendría que vivir en ese CMS, o seguir en WordPress solo como CMS.
- **Por país e idioma:** el catálogo es nativo, con 14 entidades traducibles, incluidos slug y SEO (verificado). La PoC FR devuelve "T-shirt Monospace". El contenido editorial dependería del CMS que se elija.
- **Preview y publicación programada:**
  - **Productos:** publicación programada nativa (`published_at` por canal).
  - **Promociones:** fecha de inicio y de fin.
  - **Contenido editorial:** preview y borradores los da el CMS.
- **Web components:** los custom elements (Lit) funcionan en Next.js en el lado del cliente, así que se pueden reutilizar los del plugin `toteemi` si tenemos su código. Lo más probable es que haya que reescribir su lógica, porque ahora el precio y los Teemis los decide la app.
- **SEO:**
  - **URLs:** como la tienda es nuestra, se puede **mantener `/producto/<slug>/`** con los slugs de WooCommerce.
  - **Metadatos:** `seo_title` y `seo_description` traducibles (verificado).
  - **A cargo de la tienda:** hreflang, sitemap y redirecciones 301 de lo que cambie. Saleor no tiene redirecciones.
- **Rendimiento y accesibilidad:** dependen de nuestra tienda. Next.js con ISR y catálogo precalculado da buen punto de partida, pero no he medido la tienda de referencia.

**Valoración:** 🟡 — Control total, pero todo es desarrollo: tienda, CMS aparte para el contenido y SEO a cargo nuestro.

</aside>

### 5 · Plugins / apps disponibles

- [x]  Marketplace: tamaño, calidad y quién mantiene los plugins (oficial / partner / comunidad)
- [x]  Equivalentes a lo que usamos hoy en WooCommerce (tabla de abajo)
- [x]  Por cada uno: si existe, si es gratis o de pago, fecha del último release, actividad (estrellas, issues) y soporte
- [x]  Riesgo de dependencia: qué pasa si un plugin se abandona
- [x]  Compatibilidad de los plugins con las versiones del core

| Necesidad | Plugin / app | Oficial / comunidad | Coste | Último release | Notas |
| --- | --- | --- | --- | --- | --- |
| Suscripciones | — (Stripe Billing fuera de Saleor) | — | Comisión de Stripe Billing | — | ❌ No existe app. Cambio de rol vía webhook de Stripe → API Django |
| Bundles / packs | — | — | Desarrollo propio | — | ❌ No nativo ni app |
| Wishlist | — | — | Desarrollo propio | — | ❌ No existe en 3.23 (verificado). En la tienda, guardada en `user.metadata` |
| Envíos por peso y CP | Nativo en el core | Oficial | 0 € | Core 3.23.44 (20/10/2026) | ✅ Zonas, tarifas por peso y reglas de CP |
| Cookies / RGPD | — (en la tienda: Cookiebot, CookieYes…) | Terceros | Según proveedor | — | Es cosa del frontend. Para borrar datos: **app Anonymizer** (oficial) |
| Formularios | — (en la tienda o en el CMS) | Terceros | Según proveedor | — | No es función de un e-commerce headless |
| Emails transaccionales / SMTP | **SMTP** | Oficial | 0 € | 19/10/2026 (2.9.6) | Plantillas por evento (pedido, cuenta, gift card…) |
| Redirecciones | — (en Next.js o en la CDN) | — | 0 € | — | Las 301 de la migración van en la tienda |
| Import / export | Export CSV nativo; import por API (`productBulkCreate`, `orderBulkCreate`, `customerBulkUpdate`…) | Oficial | 0 € | Core | ⚠️ El panel **no importa** CSV (verificado). Script propio o Saleor Configurator |
| 2FA en el admin | — (plugin OIDC: el login va al proveedor de identidad, que pone el 2FA) | Oficial (plugin *legacy*) | 0 € + proveedor | Core | ❌ Sin 2FA propio. ⚠️ Que el 2FA del proveedor aplique al staff está **por validar** |
| Mailchimp | — (oficial hay **Klaviyo**, y **Segment** puede reenviar a Mailchimp) | Oficial (Klaviyo, Segment) | 0 € + Segment | 19/10/2026 | ❌ Sin app de Mailchimp. A medida con webhooks o vía Segment |
| Catálogo Facebook / Meta | **Products feed** (feed en formato Google Merchant) | Oficial | 0 € | 19/10/2026 (3.3.6) | 🟡 Meta acepta feeds en ese formato (**por validar** con nuestro catálogo) |

<aside>
✍️

**Hallazgos:**
- **Marketplace:** **pequeño**. Las apps oficiales están en el monorepo `saleor/apps` (163 ⭐, 82 issues abiertos, todas publicadas el 19/10/2026): Stripe, AvaTax, CMS, Klaviyo, Search (Algolia), Segment, SMTP, Products feed, **Anonymizer** y NP Atobarai (pagos en Japón). De terceros apenas hay. Comparado con WooCommerce, casi todo lo que hoy es un plugin aquí es **desarrollo propio o un servicio externo**.
- **Calidad y compatibilidad:** las oficiales las mantiene Saleor, se publican a la vez y declaran qué versión del core necesitan (Stripe pide la 3.23). Se instalan desde el panel con un manifiesto.
- **Riesgo de dependencia:** **bajo**. Una app es un servicio aparte que habla por la API pública: si se abandona, se puede forkear o rehacer sin tocar el core. Con Saleor Cloud las oficiales vienen alojadas; en self-hosted hay que desplegarlas nosotros (son Next.js).

**Valoración:** 🟡 — Lo básico está cubierto (pagos, email, feed, anonimizar), pero suscripciones, packs, wishlist, Mailchimp y 2FA no tienen app y hay que hacerlos o comprarlos fuera.

</aside>

### 6 · Integraciones

- [x]  Mecanismo de integración: webhooks, eventos, colas; reintentos e idempotencia
- [x]  Rellenar la tabla de abajo indicando cómo se haría cada integración

| Integración | Cómo (plugin oficial / comunidad / a medida) | Esfuerzo aprox. | Notas |
| --- | --- | --- | --- |
| Stripe: pago único, recurrente, 3DS y métodos locales por país | **App oficial Stripe** (pago único con Payment Element: 3DS y los métodos activados en Stripe por país). Recurrente: **Stripe Billing fuera de Saleor** | Bajo (pago único) + medio (Billing) | Configuración por canal. Limitaciones: no usa Stripe Checkout, una sola captura por autorización y la configuración no se edita (se recrea). ⏳ Pago de prueba **pendiente** (faltan claves de test) |
| Business Central (sincronización de facturas) | **A medida**: webhooks de pedido → conector → API de BC. BC emite la factura con su serie por país y el conector la enlaza en Saleor (`invoiceCreate` con número y URL) | Alto (4–6 semanas-persona con pedidos, clientes, stock y facturas) | No hay conector oficial ni de la comunidad. BC sí tiene conector nativo con Shopify |
| API Toteemi (Django): alta, anonimización, reset password, dirección de facturación | **A medida**, todo por GraphQL con un token de app: `customerCreate`/`customerUpdate`/`customerDelete`, `requestPasswordReset`, `addressCreate`/`addressUpdate`, y anonimizar con la **app Anonymizer** o su misma lógica | Medio | Verificado en el esquema. Si el login va con la cuenta Toteemi, el reset de contraseña de Saleor sobra |
| API Toteemi (Django): saldo y consumo de Teemis | **A medida**: app de precios (lee el saldo y sobrescribe precios) más webhooks `ORDER_CREATED`/`ORDER_FULLY_PAID`/`ORDER_REFUNDED` → `SPENT_STORE` / `REFUND` | Alto (4–6 semanas-persona con precio Premium y la extensión del panel) | PoC verificada. Idempotente por pedido |
| Identidad de usuario compartida con la app | **Plugin OIDC** (si la API Django actúa como proveedor OpenID) o un BFF que valida el token de Toteemi y opera con un token de app | Medio (1–2 semanas-persona) | ⏳ Por validar con el equipo de la API |
| Emails transaccionales y Mailchimp | **App SMTP** (oficial) para los transaccionales. Mailchimp a medida o vía **Segment** | Bajo + medio | Oficial hay Klaviyo |
| Sentry | **Nativo** (`SENTRY_DSN`) en core y worker, más el SDK en la tienda y las apps | Bajo | Verificado en `settings.py` |
| Mixpanel / Meta pixel | En la tienda (scripts del cliente). Del lado del servidor, la **app Segment** reenvía los eventos de pedido | Bajo | — |
| Medios en S3 / CDN | **Nativo** (`AWS_MEDIA_BUCKET_NAME`) + CloudFront | Bajo | Hoy las imágenes ya están en S3 eu-west-1 |

<aside>
✍️

**Hallazgos:**
- **Mecanismo:** webhooks firmados (JWS) de dos tipos:
  - **Asíncronos:** salen por Celery a HTTP o **SQS**. Se reintentan **5 veces con espera exponencial** desde 10 s y quedan registrados en `core_eventdelivery` (verificado en el código).
  - **Síncronos:** timeout de 18 s.
- **Idempotencia:** la entrega es *al menos una vez*, así que el receptor (API Django, conector de BC) tiene que ser idempotente.
- ⚠️ **Hallazgo de la PoC:** un webhook síncrono **se ignora sin avisar** si la app no tiene el permiso que pide ese evento (por ejemplo, `MANAGE_SHIPPING` para listar envíos). Hay que documentarlo en cada app.
- **Desde la API Django:** todo se puede hacer por GraphQL con un token de app con permisos concretos, sin acceso a la BD de Saleor.

**Valoración:** 🟡 — Stripe, emails, Sentry y S3 vienen resueltos; Business Central, Teemis e identidad son a medida (lo más caro del proyecto).

</aside>

### 7 · Multitenant: país y club

<aside>
💡

Hay **dos dimensiones de multitenant** que tienen que funcionar a la vez: **país** (impuestos, precios, moneda, idioma, pagos, envíos, facturación) y **club** (el catálogo y los precios que ve un usuario dependen de su club). Ejemplo: un usuario de un club que compra en FR debe ver el catálogo de FR filtrado por su club.

</aside>

**País**

- [x]  Concepto nativo para país o mercado y cómo se da de alta uno nuevo
- [x]  Impuestos por país (IVA ES/FR, precios con o sin IVA incluido, OSS)
- [x]  Precios y moneda por país (el mismo producto con precios distintos)
- [x]  Idioma: traducción de catálogo, UI y emails
- [x]  Métodos de pago y de envío por país
- [x]  Catálogo por país (productos disponibles solo en algunos países)
- [x]  Usuarios: ¿una cuenta única para todos los países? ¿saldo de Teemis global?
- [x]  Pedidos y facturación separados por país
- [x]  Admin: ¿un panel único o uno por país? Permisos por país

**Club**

- [x]  Mecanismo para mostrar catálogos distintos según el club del usuario (grupos de clientes, listas de precios, canales, catálogos, segmentos…)
- [x]  Precios o descuentos específicos por club
- [x]  Combinación país × club
- [x]  Asignar el club a un usuario desde la API Django
- [x]  Límites (número de canales, mercados o catálogos) y coste asociado

<aside>
✍️

**Hallazgos — País** (PoC `poc_plantilla.py`, verificado):
- **Concepto:** el **canal**; un canal por país.
  - **Desde el panel:** 3 clics, con la moneda rellenada sola y una lista guiada de lo que falta (almacén, envíos, pagos, impuestos).
  - ⚠️ **Por API:** el canal nace **inactivo** si no se indica `isActive`.
- **Impuestos:**
  - La configuración es por canal: precios con IVA incluido, cálculo con tipos fijos o con app.
  - Los **tipos son por país y por clase de producto**.
  - PoC: ES 24,95 € con 4,33 € de IVA (21 %); FR 26,95 € con 4,49 € de IVA (20 %).
  - OSS: el informe sale de los pedidos por país (exportación o BC). Hay que validarlo con la asesoría.
- **Precio y moneda:** un precio por variante y canal, y **una moneda por canal**, sin conversión. En la eurozona no es problema.
- **Idioma:**
  - **Catálogo:** 14 entidades traducibles (verificado; la PoC FR devuelve "T-shirt Monospace").
  - **Interfaz de la tienda:** es nuestra (i18n de Next.js).
  - **Emails:** plantillas de la app SMTP.
  - **Panel:** en español, francés, alemán, italiano, polaco y portugués.
- **Pagos y envíos:**
  - **Pagos:** la configuración de Stripe es por canal.
  - **Envíos:** zonas asignadas a cada canal con precio propio (PoC: UPS a 4,90 € en ES y a 5,90 € en FR).
- **Catálogo:** un producto está en un país solo si tiene ficha en ese canal (`productchannellisting`).
- **Usuarios:** **cuenta única** para todos los países, porque el usuario no pertenece a un canal. El saldo de Teemis sigue en la API Django, así que es global.
- **Pedidos:** cada pedido lleva su canal, así que se filtran y exportan por país. La numeración de pedidos es global (ver bloque 3) y las facturas por país, de BC.
- **Admin:** **un panel único**, con **permisos por canal** (por ejemplo, que el equipo de FR solo vea pedidos de FR).

**Hallazgos — Club** (PoC `poc_plantilla.py`, verificado):
- **Guardar el club:** ✅ en Saleor, con los **tipos de cliente** (nuevos en 3.23; uno por usuario). La API Django lo asigna con `customerCreate`/`customerUpdate`, o en `metadata` si un usuario puede estar en varios clubs.
- **Ponerle límites al catálogo:** ❌ **Saleor no puede ocultar un producto a quien no es del club**:
  - Los tipos de cliente **no afectan** a promociones, vouchers, canales ni catálogo (verificado).
  - Un producto **despublicado no se puede comprar ni desde nuestra app** (`PRODUCT_NOT_PUBLISHED`), así que los productos de club tienen que estar publicados.
  - Un **canal inactivo** ("canal oculto por club") **bloquea también a la app** (`CHANNEL_INACTIVE`).
- **Lo que sí funciona:**
  1. **Mostrar:** la tienda filtra el catálogo por club con `metadata` (filtro con índice GIN). La API pública también lo ve, así que esto solo decide lo que se enseña.
  2. **Bloquear la compra (verificado):** nuestra app responde al webhook síncrono `CHECKOUT_FILTER_SHIPPING_METHODS` y **quita todos los envíos** si el checkout lleva un producto de club y el cliente no es socio. No puede elegir envío (`DELIVERY_METHOD_NOT_APPLICABLE`) y por tanto no puede cerrar la compra. Un socio compra con normalidad.
     - ⚠️ Solo sirve para productos **con envío**. Para inscripciones o productos digitales haría falta revisar el pedido al crearse (`ORDER_CREATED`) y cancelarlo.
- **Precio por club:** la misma app de precios (precio sobrescrito, como con Teemis o Premium).
- **País × club:** el país es el canal y el club es una regla de nuestra app dentro de cada canal, así que no se multiplican los canales. ⚠️ Un canal por país y club se descarta: no esconde nada (ver arriba) y 6 países × N clubs se vuelve inmanejable.
- **Límites:** no hay límite documentado de canales. En Cloud el precio va por GMV, no por canal.

**Valoración:** 🟢 país / 🟡 club — El país está resuelto de serie. El club solo se puede hacer con nuestra app (mostrar en la tienda y bloquear por envíos), y deja un hueco en productos sin envío.

</aside>

### 8 · Base de datos

- [x]  Motor y modelo de datos principal (productos, variantes, precios, pedidos, clientes)
- [x]  Cómo se modela el multitenant: columnas de tenant, esquemas separados o BD por país
- [x]  Crecimiento: qué tablas crecen con cada país, club y pedido (por ejemplo, precios por canal × variante, traducciones)
- [x]  Índices en las consultas críticas (catálogo filtrado por país + club, pedidos por cliente)
- [x]  Cómo se añaden datos propios (campos custom, metadatos, tablas propias, migraciones)
- [x]  Reporting, exportación y acceso a los datos para BI
- [x]  Migración desde WooCommerce: productos, clientes, pedidos históricos y numeración
- [x]  Backups, recuperación a un punto en el tiempo y residencia de datos (RGPD)

<aside>
✍️

**Hallazgos:**
- **Motor:** **PostgreSQL** (15 en local), con **148 tablas** (verificado). Las principales:
  - `product_product` → `product_productvariant`
  - `product_productvariantchannellisting` (precio por variante y país)
  - `order_order` / `order_orderline`
  - `account_user`
  - `checkout_checkout`
  - `discount_*` (promociones y vouchers)
- **Multitenant:** **columna `channel_id`** en las tablas `*_channellisting`, pedidos, checkouts, vouchers y promociones. Una sola BD y un solo esquema. El club no tiene modelo propio: va en `account_user.customer_type_id` o en `metadata`.
- **Crecimiento:**
  - Por cada país: `variantes × canales` filas de precio y `productos × canales` filas de publicación (5.000 variantes × 20 países = 100.000 filas, poco para Postgres), más traducciones `entidades × idiomas`.
  - El club no añade filas (solo metadata).
  - Lo que crece de verdad son pedidos, checkouts y `core_eventdelivery` (los webhooks enviados).
- **Índices (verificado):**
  - Únicos por `(variant_id, channel_id)` y `(product_id, channel_id)`, más índices por `channel_id`.
  - **GIN en `metadata`** de producto y pedido, con lo que el filtro por club tiene índice.
  - `order_order` tiene índice por `user_id`, `user_email` (también trigram) y `channel_id`.
- **Datos propios:**
  - **Sin tocar el esquema:** `metadata` / `private_metadata` (jsonb) en casi todas las entidades, más atributos en productos y, desde la 3.23, en clientes.
  - **Tablas propias:** van en **la BD de nuestras apps**, no en la de Saleor, porque tocar sus migraciones complicaría las actualizaciones.
- **BI:** exportación CSV desde el panel; para BI lo normal es leer una **réplica de lectura** de Postgres (o volcarla a un almacén de datos). El esquema es legible (ver `saleor/sql/consultas-dbeaver.sql`, 10 consultas probadas en DBeaver).
- **Migración desde WooCommerce:**
  - **Herramienta:** no hay oficial; hace falta un **script** que lea la API REST de WooCommerce y escriba con las mutaciones *bulk* (`productBulkCreate`, `orderBulkCreate`…).
  - **Referencias:** `externalReference` guarda el id de WooCommerce.
  - **Contraseñas:** no se migran.
  - **Numeración:** los pedidos históricos se pueden importar, pero la numeración nueva sale de la secuencia de Saleor. Si hay que continuar la de WooCommerce, se ajusta la secuencia (`order_order_number_seq`) antes del corte.
  - **Suscripciones Premium:** van a Stripe Billing.
- **Backups y RGPD:**
  - **Self-hosted:** RDS con *snapshots* y recuperación a un punto en el tiempo, en eu-west-1.
  - **Saleor Cloud:** UE en Irlanda, con réplica en Francia para recuperación ante desastres; la región de la UE no comparte datos con la de EE. UU.
  - **Derecho al olvido:** la app **Anonymizer** oficial borra el cliente y anonimiza sus pedidos y checkouts.

**Valoración:** 🟢 — Modelo relacional claro y bien indexado; el multipaís es una columna; los datos propios van en metadata o en nuestras apps.

</aside>

## PoC mínima (recomendada)

- [x]  Levantar la plataforma en local — `saleor/docker-compose.yml` (9 servicios, migraciones automáticas) o Dev Container. Probado desde cero: unos 80 s para arrancar y unos 17 s para cargar los datos de ejemplo
- [x]  Crear 2 países (ES y FR) con IVA, precio e idioma distintos — `poc_plantilla.py`: IVA 21 % / 20 %, 24,95 € / 26,95 €, envío 4,90 € / 5,90 €, nombre del producto en francés
- [x]  Un producto visible solo para los usuarios de un club — `poc_plantilla.py`: la tienda filtra con metadata y la app bloquea la compra a quien no es socio. ⚠️ No se puede ocultar a nivel de Saleor (ver bloque 7)
- [x]  Prototipo de descuento con Teemis o de cupón por rol — **los dos**: Teemis en `verificar.py` (precio sobrescrito y pedido 100 % Teemis sin pago) y envío gratis Premium en `poc_plantilla.py`
- [ ]  Pago de prueba con Stripe — ⏳ **pendiente**: hacen falta claves de test de Stripe y una URL pública para sus webhooks
- Repo / rama de la PoC: `investigacion-ecommerce/saleor/` (de momento en local, sin repo remoto)

## Resumen y recomendación

| Bloque | Valoración | Comentario corto |
| --- | --- | --- |
| 1 · Arquitectura de código | 🟢 | Apps desacopladas del core; actualizar no rompe nuestro código; Sentry y OpenTelemetry nativos |
| 2 · Infraestructura | 🟡 | Estándar y encaja en AWS, pero son 4 piezas de Saleor más las nuestras; el recálculo de promociones se paró en local y hay que vigilarlo |
| 3 · Personalización funcional | 🟡 | Teemis viable y verificado; Premium (Stripe Billing), cupones por rol y packs son desarrollo propio |
| 4 · UI y CMS | 🟡 | Tienda 100 % nuestra (control total, más trabajo); hace falta un CMS aparte para el contenido |
| 5 · Plugins / apps | 🟡 | Pocas apps (unas 10 oficiales); suscripciones, packs, wishlist, Mailchimp y 2FA no tienen app |
| 6 · Integraciones | 🟡 | Stripe, SMTP, Sentry y S3 de serie; Business Central, Teemis e identidad a medida |
| 7 · Multitenant (país y club) | 🟢 / 🟡 | País de serie (canales); club solo con nuestra app y con un hueco en productos sin envío |
| 8 · Base de datos | 🟢 | PostgreSQL, multipaís por columna, índices adecuados, metadata para datos propios |
- **Esfuerzo estimado de la migración (días):** ≈ **145–220 días-persona** (29–44 semanas-persona), es decir, unos 3–4 meses con 3 personas. Lo más caro: tienda y checkout (40–60), Business Central (20–30), app de precios con Teemis, Premium y club (20–30), CMS (15–25). Es una estimación orientativa que no incluye traducir el catálogo ni el diseño.
- **Coste mensual estimado:** self-hosted en AWS ≈ **450–650 $/mes**, casi igual para 1 país que para N. Saleor Cloud desde **1.599 $/mes** (hasta 200k $ de GMV), más la tienda y las apps. Licencia 0 €.
- **Riesgos principales:**
  1. El coste de construir la tienda, el checkout y las integraciones a medida (BC, Teemis, identidad).
  2. Los clubs y los productos solo Premium no se pueden ocultar en Saleor: la compra solo se bloquea por envíos, y los productos sin envío requieren cancelar después.
  3. El precio mínimo se puede romper al combinar Teemis con cupones o promociones.
  4. Migrar las suscripciones Premium a Stripe Billing.
  5. El recálculo de promociones se paró en local.
  6. Productos publicados a 0 € por un despiste en el panel.
- **Recomendación:** ⚠️ **seguir con reservas**. Técnicamente cubre el país de serie y el caso crítico (Teemis en el checkout) con un mecanismo oficial, y no ata al proveedor. Pero casi todo lo propio de Toteemi (Premium, clubs, cupones por rol, packs, BC) es desarrollo propio, y el esfuerzo es alto. Compensa si se valora tener el control total y si el equipo puede mantener la tienda y 2 o 3 servicios propios. Hay que compararlo con Medusa y Shopify Plus antes de decidir.

## Dudas abiertas

1. **Clubs:** ¿un usuario puede pertenecer a varios clubs? ¿Hay productos de club **sin envío** (inscripciones, digitales)? En ese caso la compra no se puede bloquear por envíos.
2. **Teemis y cupones:** ¿se pueden combinar? Si se pueden, la app tiene que garantizar el precio mínimo después de aplicar cupones y promociones.
3. **Suscripción Premium:** ¿con qué pasarela se cobra hoy? Si ya es Stripe, la migración a Stripe Billing conserva las tarjetas.
4. **Identidad:** ¿la API Django puede actuar como proveedor OpenID Connect? Si no, hace falta un BFF que valide su token.
5. **Facturación:** ¿quién emite hoy las facturas, WooCommerce o Business Central? ¿Hay que continuar la numeración de pedidos de WooCommerce? ¿Se tributa ya por OSS? (validar con la asesoría, también VeriFactu)
6. **Plugin `toteemi` de WordPress:** ¿hay acceso a su código? Su lógica de Teemis, precio mínimo y Premium es la que hay que portar, y sus web components quizá se puedan reutilizar.
7. **Web corporativa:** ¿se muda a un CMS headless o se queda WordPress solo como CMS?
8. **Países:** ¿los 6 son de la eurozona? Saleor usa una moneda por canal. ¿En qué idiomas?
9. **Alojamiento:** ¿self-hosted en EKS (más operación) o Saleor Cloud (desde 1.599 $/mes, UE en Irlanda)?
10. **Stripe:** hacen falta claves de test para la PoC de pago.
11. **2FA del staff:** ¿el 2FA del proveedor de identidad aplica al panel con el plugin OIDC? Hay que probarlo.
12. **Planificador de Saleor:** ¿el parón del recálculo de promociones ocurre también fuera de local? Probar en staging o preguntar en el Discord de Saleor.
13. **Referencia multisite:** no he encontrado `US/in_progress/US_apertura_internacional.md` en los repos a los que tengo acceso. ¿Dónde está?

**Fuentes:** [Saleor (GitHub)](https://github.com/saleor/saleor) · [Apps oficiales](https://github.com/saleor/apps) · [Precios de Saleor Cloud](https://saleor.io/pricing) · [Regiones de Saleor Cloud](https://docs.saleor.io/cloud/regions) · [Despliegue en Kubernetes](https://docs.saleor.io/setup/deploy-kubernetes) · [Plugin OpenID Connect](https://docs.saleor.io/developer/app-store/plugins/oidc) · [Canales](https://docs.saleor.io/developer/channels/overview) · [Descuentos](https://docs.saleor.io/developer/discounts/overview) · [Precio de línea a medida](https://docs.saleor.io/docs/3.x/developer/checkout/lines) · [Webhooks síncronos](https://docs.saleor.io/developer/extending/webhooks/synchronous-events/overview) · [App de Stripe](https://docs.saleor.io/developer/app-store/apps/stripe/overview) · [App de facturas](https://docs.saleor.io/developer/app-store/apps/invoices) · [Integraciones de Business Central](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/developer/integration-overview)
