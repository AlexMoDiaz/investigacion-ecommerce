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

- [ ]  Lenguaje, framework y versión; madurez del proyecto (antigüedad, ritmo de releases, breaking changes entre majors)
- [ ]  Licencia y modelo (open source / open core / SaaS) y su impacto en nuestro código
- [ ]  Dónde vive nuestra lógica a medida (módulos, plugins, apps, extensiones) y cómo se versiona
- [ ]  Modelo de extensión (hooks, eventos, workflows, webhooks): ¿se puede extender sin forkear el core?
- [ ]  API expuesta (REST / GraphQL, admin / storefront), autenticación y límites
- [ ]  Headless o monolito: ¿el storefront va separado? ¿qué starter ofrece?
- [ ]  Encaje con nuestra arquitectura por capas (domain / application / infrastructure) y con el stack del equipo
- [ ]  Testing de la lógica propia (unit / e2e), entorno local y fixtures
- [ ]  Cómo se actualiza el core y cuánto rompe el código propio
- [ ]  Observabilidad: Sentry, logs, trazas

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 2 · Infraestructura necesaria y optimizaciones

- [ ]  Componentes necesarios: servidor de aplicación, workers, BD, Redis, colas, buscador, almacenamiento de medios
- [ ]  Encaje con la infra actual (AWS, EKS, Terraform, GitLab CI)
- [ ]  Varios países: ¿una instancia o una por país?
- [ ]  Escalado horizontal y gestión del estado (sesiones, caché, jobs)
- [ ]  Caché y CDN (storefront, imágenes) y rendimiento esperado
- [ ]  Jobs programados (crons) y tareas asíncronas
- [ ]  Backups, restore y entornos (local, staging, prod)
- [ ]  Coste estimado (licencia / plan + infra + apps de pago), para 1 país y para N países
- [ ]  Coste operativo: quién mantiene qué, upgrades, parches de seguridad

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 3 · Personalización funcional (lógica de negocio)

- [ ]  Descuento con Teemis: saldo externo leído de la API Django, aplicado en carrito/checkout y consumido de forma idempotente
- [ ]  Cupones restringidos por rol o segmento (solo premium, envío gratis premium…)
- [ ]  Reglas de descuento a medida que se puedan combinar con cupones y promociones
- [ ]  Suscripción Premium: alta, renovación, cancelación y cambio de rol
- [ ]  Packs/bundles y envíos por peso y código postal
- [ ]  Numeración de pedidos y facturas correlativa por país (por ejemplo, prefijo `FR-`)
- [ ]  Puntos de extensión del checkout: validaciones, campos extra, pasos
- [ ]  Qué se resuelve configurando desde el admin y qué exige código

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 4 · Personalización de la UI y CMS

- [ ]  Cómo se construye el storefront (tema, framework, starter) y qué parte es código
- [ ]  Qué puede editar una persona no técnica sin deploy: páginas, textos, imágenes, banners, colores/branding, menús
- [ ]  CMS integrado o externo (Strapi, Payload, Sanity, Contentful, Storyblok…) y cómo se conecta al storefront
- [ ]  Contenido por país e idioma desde el CMS
- [ ]  Preview, borradores y publicación programada
- [ ]  Si se pueden reutilizar nuestros web components (Lit) o el diseño actual
- [ ]  SEO: URLs, metadatos, hreflang, sitemaps y redirecciones desde la tienda actual
- [ ]  Rendimiento y accesibilidad del storefront

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 5 · Plugins / apps disponibles

- [ ]  Marketplace: tamaño, calidad y quién mantiene los plugins (oficial / partner / comunidad)
- [ ]  Equivalentes a lo que usamos hoy en WooCommerce (tabla de abajo)
- [ ]  Por cada uno: si existe, si es gratis o de pago, fecha del último release, actividad (estrellas, issues) y soporte
- [ ]  Riesgo de dependencia: qué pasa si un plugin se abandona
- [ ]  Compatibilidad de los plugins con las versiones del core

| Necesidad | Plugin / app | Oficial / comunidad | Coste | Último release | Notas |
| --- | --- | --- | --- | --- | --- |
| Suscripciones |  |  |  |  |  |
| Bundles / packs |  |  |  |  |  |
| Wishlist |  |  |  |  |  |
| Envíos por peso y CP |  |  |  |  |  |
| Cookies / RGPD |  |  |  |  |  |
| Formularios |  |  |  |  |  |
| Emails transaccionales / SMTP |  |  |  |  |  |
| Redirecciones |  |  |  |  |  |
| Import / export |  |  |  |  |  |
| 2FA en el admin |  |  |  |  |  |
| Mailchimp |  |  |  |  |  |
| Catálogo Facebook / Meta |  |  |  |  |  |

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 6 · Integraciones

- [ ]  Mecanismo de integración: webhooks, eventos, colas; reintentos e idempotencia
- [ ]  Rellenar la tabla de abajo indicando cómo se haría cada integración

| Integración | Cómo (plugin oficial / comunidad / a medida) | Esfuerzo aprox. | Notas |
| --- | --- | --- | --- |
| Stripe: pago único, recurrente, 3DS y métodos locales por país |  |  |  |
| Business Central (sincronización de facturas) |  |  |  |
| API Toteemi (Django): alta, anonimización, reset password, dirección de facturación |  |  |  |
| API Toteemi (Django): saldo y consumo de Teemis |  |  |  |
| Identidad de usuario compartida con la app |  |  |  |
| Emails transaccionales y Mailchimp |  |  |  |
| Sentry |  |  |  |
| Mixpanel / Meta pixel |  |  |  |
| Medios en S3 / CDN |  |  |  |

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 7 · Multitenant: país y club

<aside>
💡

Hay **dos dimensiones de multitenant** que tienen que funcionar a la vez: **país** (impuestos, precios, moneda, idioma, pagos, envíos, facturación) y **club** (el catálogo y los precios que ve un usuario dependen de su club). Ejemplo: un usuario de un club que compra en FR debe ver el catálogo de FR filtrado por su club.

</aside>

**País**

- [ ]  Concepto nativo para país o mercado y cómo se da de alta uno nuevo
- [ ]  Impuestos por país (IVA ES/FR, precios con o sin IVA incluido, OSS)
- [ ]  Precios y moneda por país (el mismo producto con precios distintos)
- [ ]  Idioma: traducción de catálogo, UI y emails
- [ ]  Métodos de pago y de envío por país
- [ ]  Catálogo por país (productos disponibles solo en algunos países)
- [ ]  Usuarios: ¿una cuenta única para todos los países? ¿saldo de Teemis global?
- [ ]  Pedidos y facturación separados por país
- [ ]  Admin: ¿un panel único o uno por país? Permisos por país

**Club**

- [ ]  Mecanismo para mostrar catálogos distintos según el club del usuario (grupos de clientes, listas de precios, canales, catálogos, segmentos…)
- [ ]  Precios o descuentos específicos por club
- [ ]  Combinación país × club
- [ ]  Asignar el club a un usuario desde la API Django
- [ ]  Límites (número de canales, mercados o catálogos) y coste asociado

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

### 8 · Base de datos

- [ ]  Motor y modelo de datos principal (productos, variantes, precios, pedidos, clientes)
- [ ]  Cómo se modela el multitenant: columnas de tenant, esquemas separados o BD por país
- [ ]  Crecimiento: qué tablas crecen con cada país, club y pedido (por ejemplo, precios por canal × variante, traducciones)
- [ ]  Índices en las consultas críticas (catálogo filtrado por país + club, pedidos por cliente)
- [ ]  Cómo se añaden datos propios (campos custom, metadatos, tablas propias, migraciones)
- [ ]  Reporting, exportación y acceso a los datos para BI
- [ ]  Migración desde WooCommerce: productos, clientes, pedidos históricos y numeración
- [ ]  Backups, recuperación a un punto en el tiempo y residencia de datos (RGPD)

<aside>
✍️

**Hallazgos:** *(pendiente)*

**Valoración:** 🟢 / 🟡 / 🔴 — *(elige una y justifícala en una línea)*

</aside>

## PoC mínima (recomendada)

- [ ]  Levantar la plataforma en local
- [ ]  Crear 2 países (ES y FR) con IVA, precio e idioma distintos
- [ ]  Un producto visible solo para los usuarios de un club
- [ ]  Prototipo de descuento con Teemis o de cupón por rol
- [ ]  Pago de prueba con Stripe
- Repo / rama de la PoC:

## Resumen y recomendación

| Bloque | Valoración | Comentario corto |
| --- | --- | --- |
| 1 · Arquitectura de código |  |  |
| 2 · Infraestructura |  |  |
| 3 · Personalización funcional |  |  |
| 4 · UI y CMS |  |  |
| 5 · Plugins / apps |  |  |
| 6 · Integraciones |  |  |
| 7 · Multitenant (país y club) |  |  |
| 8 · Base de datos |  |  |
- **Esfuerzo estimado de la migración (días):**
- **Coste mensual estimado:**
- **Riesgos principales:**
- **Recomendación:** ✅ seguir · ⚠️ seguir con reservas · ❌ descartar

## Dudas abiertas
