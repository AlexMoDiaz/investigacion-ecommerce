# 0. Situación actual y alcance

> Fuentes: repositorio de la app (`toteemi-app-upgrade`, rama develop) y revisión desde fuera de la tienda pública (`toteemi.com`, `staging-shop.toteemi.com`) el 23/10/2026. **No he tenido acceso al código de WordPress ni del backend**, así que lo que se dice de ellos sale de lo que se ve desde fuera y de lo que consume la app.

## El ecosistema Toteemi hoy
```mermaid
flowchart LR
  APP[App Toteemi<br/>React Native iOS/Android]
  API[Backend Toteemi<br/>api.toteemi.com · REST v2→v3<br/>usuarios, wallet de teemis,<br/>game settings, premium]
  WP[Toteemi Shop<br/>WordPress 7.1 + WooCommerce<br/>toteemi.com]
  STRAVA[Strava / Garmin]
  S3[(S3 eu-west-1<br/>imágenes de la tienda)]
  APP -->|REST| API
  APP -->|abre en el navegador| WP
  WP <-->|plugin propio «toteemi»<br/>saldo y canje de teemis| API
  STRAVA --> API
  WP --> S3
```

- **App** (este repo): gamificación de ciclismo y running. El usuario gana **teemis** con misiones, rankings, encuestas, invitaciones y un canje diario con límite (100 al día en estándar y 200 en Premium; los usuarios Premium ganan el doble).
- **Backend Toteemi** (`api.toteemi.com`): es **el dueño de la wallet**, con el saldo y el historial de transacciones. Entre los tipos de transacción hay tres que vienen de la tienda: `SPENT_STORE` (compra con teemis), `BOUGHT_STORE` (compra *de* teemis) y `REFUND`. En `envs/*.json` aparece como `BACKOFFICE_URL`, así que entiendo que **es el "backoffice propio"** del encargo.
- **Tienda**: `shop.toteemi.com` redirige a `toteemi.com`, que es a la vez **web corporativa y tienda**: WordPress 7.1.3 + WooCommerce sobre Apache, en AWS (detrás de un ELB y con las imágenes en S3).
- La app **no lleva la tienda dentro**: la pestaña *Shop*, los banners y el aviso que aparece después de reclamar teemis abren `STORE_URL` en el navegador. Premium se contrata y se gestiona en la tienda (`/hazte-premium/`, `/mi-cuenta/subscriptions/`).

## Qué hace hoy la tienda (WooCommerce)
| Funcionalidad | Cómo está hecha hoy |
|---|---|
| Catálogo | Equipamiento de ciclismo y running, nutrición, cosmética, **gift cards**, **inscripciones y experiencias**, **packs** y productos Premium |
| **Canje de teemis en el carrito** | **Plugin propio `toteemi`** (web components): un interruptor en el carrito que aplica los teemis ("Estás ahorrando X gracias a tus Teemis") |
| **Precio mínimo** | Componente `toteemi-min-price` en la ficha de producto |
| Precio en teemis | `teemis-price` muestra el precio y los teemis necesarios ("Loguéate para ver tu precio") |
| Productos especiales | Etiquetas `full-teemis-tag` (se puede pagar entero con teemis), `exclusive-teemis-tag` y productos que "solo se pueden pagar en euros" |
| **Precio y productos solo Premium** | `only-premium-price`, `premium-tag` y productos exclusivos para Premium |
| **Suscripción Premium** (mensual y anual) | Plugin **WooCommerce Subscriptions** |
| Códigos | **WC Serial Numbers** (probablemente para gift cards o inscripciones) |
| Packs | Easy Product Bundles |
| Envíos | Plugin APG de envío por peso y código postal; Premium no se vende en Ceuta y Melilla |
| Otros | Wishlist (TI), carrito lateral, WPForms, aviso de cookies |
| Cuenta | Iniciar sesión con la cuenta de Toteemi ("Regístrate y te damos 150 Teemis") |

**Problema que se ve desde fuera:** el carrito dice *"¿Has modificado el carrito? Recalcula tu ahorro aquí"*. El descuento por teemis **no se recalcula solo** cuando cambia el carrito. Es justo el punto débil que hay que resolver en la nueva plataforma (ver 1.6).

## Reparto de la investigación
| Plataforma | Responsable | Estado |
|---|---|---|
| Saleor | Alexander | ✅ Análisis + entorno local + revisión de la BD + pruebas de concepto |
| Medusa | Compañera | En curso |
| Shopify Plus | Sin asignar | Pendiente |

## Requisitos
### Del encargo
| # | Requisito | Detalle |
|---|---|---|
| R1 | Multipaís | 6 países europeos al arrancar (hoy solo España y EUR), con capacidad para crecer |
| R2 | Precio por país | Precio base propio en cada país |
| R3 | Precio mínimo por país | El que resulta de aplicar el **máximo de teemis** al precio base (ver más abajo) |
| R4 | Multitema | Catálogo distinto y tema visual propio en cada país |
| R5 | **Teemis → descuento en el checkout** | **Requisito crítico.** Si no se traduce en un descuento real en el checkout, la plataforma no sirve |
| R6 | Control total del checkout | Poder modificar el flujo y la lógica a fondo |
| R7 | Panel tipo CMS | Que alguien sin conocimientos técnicos gestione descuentos, precios y la operativa diaria |
| R8 | Integraciones | Backoffice/backend Toteemi, Stripe y Microsoft Dynamics 365 Business Central |
| R9 | Madurez | Que funcione desde el primer día, sin soluciones de nicho ni experimentales |

### Que salen de la tienda actual (no estaban en el encargo)
| # | Requisito | Por qué |
|---|---|---|
| R10 | **Suscripción Premium** recurrente (mensual y anual) | Hoy la cubre WooCommerce Subscriptions. Hay que **migrar las suscripciones activas** |
| R11 | **Precio y productos solo para Premium** | `only-premium-price` y productos exclusivos |
| R12 | Productos especiales | Gift cards, códigos (serials), inscripciones sin envío y packs |
| R13 | Movimientos de teemis desde la tienda | Comprar teemis (`BOUGHT_STORE`) y **devolverlos al reembolsar** (`REFUND`) |
| R14 | **Cuenta única Toteemi** | El cliente inicia sesión en la tienda con su cuenta de la app |
| R15 | Contenido web | `toteemi.com` también es la web corporativa (La App, Premium, Alma Toteemi, Empresas…). Si se deja WordPress, ese contenido necesita otro sitio |
| R16 | Envíos por peso y código postal | Incluida la exclusión de Ceuta y Melilla |

### Que salen de abrir varios países (detalle en el apartado 6)
| # | Requisito | Por qué |
|---|---|---|
| R17 | IVA del país del cliente (OSS) y **facturas legales** por país | Vender a particulares de otros países de la UE |
| R18 | Idiomas | Catálogo, tienda, emails y condiciones en el idioma de cada país (la app hoy solo está en español e inglés) |
| R19 | SEO y migración | Mantener el posicionamiento de `toteemi.com` (redirecciones 301) y migrar los datos de WooCommerce |

### Cómo funcionan los teemis (definición acordada)
Los **teemis** son la moneda del juego. Los gana el usuario en la app, viven en la **wallet del backend Toteemi** y se canjean en la tienda como descuento.

- Cada producto tiene, **en cada país**, un **máximo de teemis canjeables**.
- **Precio mínimo = precio base del país − (máximo de teemis × valor del teemi)**. Es lo menos que puede llegar a pagar un cliente por ese producto.
- Casos límite que ya existen hoy: productos que se pueden pagar **100 % con teemis** (precio mínimo 0 €) y productos que **solo se pagan en euros** (máximo de teemis 0).
- La plataforma tiene que poder: (1) consultar el saldo en el backend, (2) aplicar los teemis en el checkout respetando el máximo **y recalculando cuando cambie el carrito**, (3) cobrar en Stripe el total ya rebajado y (4) registrar el gasto en el backend (`SPENT_STORE`) y la devolución si hay reembolso (`REFUND`).

## Preguntas abiertas
1. ¿El "backoffice propio" del encargo es el backend Toteemi (`api.toteemi.com`)? Lo he asumido así.
2. ¿Hay acceso al código del plugin `toteemi` de WordPress? Ahí está la lógica actual de teemis, precio mínimo y Premium, y se podría reaprovechar.
3. ¿Con qué pasarela se cobran hoy las suscripciones Premium? Si ya es Stripe, migrarlas a Stripe Billing es mucho más fácil.
4. ¿La web corporativa se queda en WordPress (solo como CMS) o también se muda?
5. ¿Las empresas o clubes (`X-Company-Id` en la app) tienen precios o catálogo propios en la tienda?

---

# 1. Saleor

> Datos revisados el **23/10/2026** sobre **Saleor 3.23** (última versión: 3.23.44, del 20/10/2026). Todo lo que pone *"verificado en local"* se ha comprobado en el entorno Docker de `saleor/`.

## 1.1 Resumen
Saleor es una **plataforma de e-commerce headless y open source** (licencia BSD-3) escrita en **Python/Django** que expone **toda su funcionalidad mediante una API GraphQL**. No trae tienda (frontend): la tienda y el checkout se programan aparte y hablan con la API. Su concepto central para vender en varios países son los **canales** (*channels*).

**Veredicto:** cumple de serie la parte estructural: multipaís, precios y catálogo por país, envíos por peso y código postal, gift cards, Stripe y control total del checkout.

**Los teemis son viables:** una app propia sobrescribe el precio de las líneas del checkout. Está **verificado en local**, incluido el caso de un producto pagado al 100 % con teemis (total 0 €).

Lo que **no trae y hay que cubrir aparte**:
- La **suscripción Premium**: no hay suscripciones en Saleor.
- Los **precios solo para Premium**: no hay grupos de clientes ni listas de precios.
- El conector con **Business Central**.
- El **inicio de sesión con la cuenta Toteemi**.
- La **web de contenidos**.

## 1.2 Licencia y precio
| Modalidad | Coste | Notas |
|---|---|---|
| **Open source (self-hosted)** | 0 € de licencia (BSD-3) | Pagamos la infraestructura (Postgres, Redis/Valkey, contenedores) y la operación. Hoy ya estáis en AWS |
| **Saleor Cloud – Sandboxes** | Gratis | Solo para pruebas |
| **Saleor Cloud – Select** | 1.599 $/mes | Hasta 200.000 $ de GMV al mes; por encima, 0,8 % del GMV |
| **Saleor Cloud – Volume** | 3.999 $/mes | Hasta 1.000.000 $ de GMV al mes; por encima, 0,4 % |
| **Saleor Cloud – Enterprise** | A negociar | Comisión desde el 0,2 % |

Opcionales de Cloud: *Accelerator* (6.000 $ en un pago, que se devuelven como crédito el primer año) y *Forward Deployed Engineering* (12.000 $, un mes de un ingeniero de Saleor). El código es **el mismo** en open source y en Cloud.

## 1.3 Arquitectura

### Externa: headless y "API-first"
```mermaid
flowchart LR
  subgraph Front["Frontends (nuestro código)"]
    SF[Tienda Next.js<br/>un tema por país]
    BFF[BFF / API routes<br/>valida y cierra el checkout]
  end
  APPRN[App Toteemi]
  DASH[Saleor Dashboard]
  subgraph Core["Saleor Core"]
    API[API GraphQL<br/>Django + uvicorn]
    W[Workers Celery]
  end
  PG[(PostgreSQL)]
  R[(Redis / Valkey)]
  subgraph Apps["Apps (servicios aparte)"]
    STRIPE[App Stripe<br/>oficial]
    PRICING[App de precios Toteemi<br/>teemis + Premium · a medida]
    BC[Conector BC<br/>a medida]
  end
  TOT[Backend Toteemi<br/>wallet de teemis, premium]
  D365[Business Central]
  SBILL[Stripe Billing<br/>suscripción Premium]
  APPRN -->|abre| SF
  SF --> BFF -->|GraphQL| API
  DASH -->|GraphQL| API
  API --> PG & R
  W --> PG & R
  API -->|webhooks| Apps
  Apps -->|GraphQL + token de app| API
  PRICING <-->|saldo, SPENT_STORE, REFUND| TOT
  STRIPE <--> StripeAPI[Stripe]
  BC <--> D365
  SBILL -->|webhook: alta o baja de Premium| TOT
```

- **Headless:** la tienda puede ser Next.js, Nuxt o lo que queramos. Saleor mantiene una tienda de referencia en Next.js que sirve de punto de partida. El **tema por país** vive aquí.
- **Extensión mediante "Apps", no plugins:** una app es un **servicio web independiente** (en cualquier lenguaje, aunque el SDK oficial es TypeScript) que se instala en Saleor, recibe un **token con permisos concretos** y se suscribe a **webhooks**. No se toca el core, así que **actualizar Saleor no rompe nuestras extensiones**. Es justo lo contrario que hoy con el plugin `toteemi` dentro de WordPress.
- **Las apps pueden incrustarse en el Dashboard** mediante iframes (páginas, pop-ups o widgets en la ficha de producto, pedido, cliente, voucher…). Así se le puede dar al equipo no técnico una pantalla de "teemis por país".

### Interna: monolito modular
- **Un monolito Django** organizado en módulos: `product`, `channel`, `discount`, `checkout`, `order`, `payment`, `warehouse`, `shipping`, `tax`, `giftcard`, `account`, `webhook`, `app`…
- **Piezas en ejecución** (verificado en local, `docker compose ps`):

| Servicio | Qué hace |
|---|---|
| `api` | Servidor GraphQL (ASGI/uvicorn), puerto 8000 |
| `worker` | Celery: tareas en segundo plano (recalcular precios con descuento, enviar webhooks asíncronos, emails, exportaciones) |
| `beat` | Planificador de Celery: lanza las tareas periódicas (por ejemplo, recalcular las promociones cada 30 s). **Debe haber uno solo** y conviene vigilarlo (ver 1.7) |
| `db` | PostgreSQL |
| `cache` | Valkey/Redis: caché y *broker* de la cola de Celery |
| `dashboard` | Panel de administración (estáticos servidos con nginx), puerto 9000 |
| `jaeger` / `mailpit` | Solo en local: trazas OpenTelemetry y bandeja de emails de prueba |

- **Escalado horizontal:** `api` y `worker` no guardan estado, así que se pueden replicar detrás de un balanceador. Postgres admite **réplica de lectura** (`DATABASE_URL_REPLICA`).

### Webhooks: cómo se extiende la lógica
- **Asíncronos** (avisan de que algo ha pasado): `ORDER_CREATED`, `ORDER_FULLY_PAID`, `ORDER_REFUNDED`, `CHECKOUT_UPDATED`, `PRODUCT_UPDATED`… Son la base para registrar los teemis en el backend y para sincronizar con Business Central.
- **Síncronos** (Saleor espera la respuesta de la app). Verificado en local con introspección, en la 3.23 existen: cálculo de impuestos (`CHECKOUT_CALCULATE_TAXES`), métodos de envío (`SHIPPING_LIST_METHODS_FOR_CHECKOUT`, `CHECKOUT_FILTER_SHIPPING_METHODS`), pagos y transacciones (`TRANSACTION_*`, `PAYMENT_GATEWAY_INITIALIZE_SESSION`) y métodos de pago guardados.
- ⚠️ **No existe un webhook síncrono de "calcular descuentos"** ni de "validar el checkout antes de cerrarlo". Los descuentos propios se aplican por otra vía (ver 1.6).

## 1.4 Base de datos
- **Motor:** **PostgreSQL** (relacional). Verificado en local: **148 tablas**. El nombre de cada tabla indica a qué módulo pertenece: `product_*`, `discount_*`, `checkout_*`…
- Usa columnas `jsonb` en `metadata`/`private_metadata` de casi todas las entidades (canal, producto, variante, checkout, línea, usuario…). Ahí se pueden guardar datos propios sin tocar el esquema.

### Modelo multipaís, precios y descuentos (verificado en local)
```mermaid
erDiagram
  channel_channel ||--o{ product_productchannellisting : "publica"
  channel_channel ||--o{ product_productvariantchannellisting : "precio en"
  product_product ||--o{ product_productvariant : tiene
  product_product ||--o{ product_productchannellisting : "visible en"
  product_productvariant ||--o{ product_productvariantchannellisting : "tiene precio en"
  product_productvariantchannellisting ||--o{ product_variantchannellistingpromotionrule : "descuento precalculado"
  discount_promotion ||--o{ discount_promotionrule : contiene
  discount_promotionrule }o--o{ channel_channel : "discount_promotionrule_channels"
  discount_promotionrule }o--o{ product_productvariant : "discount_promotionrule_variants"
  discount_voucher ||--o{ discount_voucherchannellisting : "valor por canal"
  channel_channel ||--o{ checkout_checkout : ""
  checkout_checkout ||--o{ checkout_checkoutline : líneas
  checkout_checkoutline ||--o{ discount_checkoutlinediscount : "descuentos aplicados"
  channel_channel ||--o{ warehouse_channelwarehouse : ""
  channel_channel }o--o{ shipping_shippingzone : "shipping_shippingzone_channels"
```

| Concepto | Tabla(s) | Columnas clave |
|---|---|---|
| **Canal (≈ país o mercado)** | `channel_channel` | `slug`, `currency_code` (**una moneda por canal**), `default_country`, `metadata` |
| **Producto visible en un país** | `product_productchannellisting` | `channel_id`, `product_id`, `is_published`, `published_at`, `visible_in_listings` |
| **Precio por país** | `product_productvariantchannellisting` | `variant_id`, `channel_id`, `price_amount`, `cost_price_amount`, `prior_price_amount`, `discounted_price_amount`, `currency` |
| **Promociones automáticas** | `discount_promotion` → `discount_promotionrule` | `type` (catalogue/order), `catalogue_predicate` y `order_predicate` (**JSON**), `reward_value_type`, `reward_value` |
| **Vouchers (códigos)** | `discount_voucher`, `discount_vouchercode`, `discount_voucherchannellisting` | `discount_value` y `min_spent_amount` **por canal** |
| **Descuento aplicado a una línea** | `discount_checkoutlinediscount`, `discount_orderlinediscount` | `type`, `value`, `amount_value`, `promotion_rule_id`, `voucher_id`, `reason` |
| **Línea de checkout** | `checkout_checkoutline` | `price_override`, `price_override_reason`, `undiscounted_unit_price_amount`, `metadata` |
| **Stock por país** | `warehouse_warehouse`, `warehouse_stock`, `warehouse_channelwarehouse` | almacenes asignados a cada canal |
| **Envíos** | `shipping_shippingzone`, `shipping_shippingmethod`, `shipping_shippingmethodpostalcoderule` | tarifas por peso o por importe y **reglas de código postal** (por ejemplo, excluir Ceuta y Melilla) |
| **Impuestos por país** | `tax_taxconfiguration`, `tax_taxconfigurationpercountry`, `tax_taxclasscountryrate` | IVA por país y por clase de producto |
| **Gift cards** | `giftcard_giftcard` | `current_balance_amount`, `currency` |

**Cómo resuelve el multipaís:** un producto existe **una sola vez** (`product_product`). Su presencia en cada país es una fila en `*_channellisting`: si no hay fila para un canal, el producto no existe en ese país, y así se consigue un **catálogo distinto por país**. El precio también es una fila por variante y canal.

**Cómo resuelve los descuentos:** las promociones de catálogo (por ejemplo, el "¡Oferta!" que se ve hoy en la tienda) se **precalculan** (lo hace el worker) en `product_variantchannellistingpromotionrule` y `discounted_price_amount`. Las reglas se definen con un **predicado JSON** sobre producto, variante, categoría o colección (verificado por introspección), y el panel lo genera sin que nadie tenga que escribir JSON.

⚠️ **Lo que no existe en el esquema:**
- **No hay "precio mínimo" ni "máximo de teemis".** Y `product_productvariantchannellisting` **no tiene `metadata`**, así que el máximo de teemis por variante y país va en `product_productvariant.metadata` con una clave por canal (por ejemplo `teemis_max.es`) o en el backend Toteemi.
- **No hay grupos de clientes ni listas de precios.** Desde la 3.23 existen los *tipos de cliente* (`customerType`), pero solo clasifican al cliente: no los usan promociones, vouchers, canales ni catálogo (verificado). Las promociones no se pueden filtrar por tipo de cliente (verificado: los predicados solo aceptan producto, variante, categoría y colección). La propia documentación de Saleor dice que para precios por cliente hay que implementar "listas de precios" por nuestra cuenta.
- **No hay suscripciones** (el tipo `Subscription` del esquema GraphQL son las suscripciones a eventos de los webhooks, no pagos recurrentes).

### Escalado de 6 a N países
- **Un canal por país**: cada país nuevo es una fila en `channel_channel` más su configuración (almacenes, zonas de envío, impuestos y pasarela de pago para ese canal).
- **Crecimiento de datos:** las filas de precios crecen como `nº de variantes × nº de canales`. Con 5.000 variantes y 20 países salen 100.000 filas, que para Postgres es muy poco.
- **Lo que de verdad pesa** es la operativa: dar de alta precios y máximos de teemis en N canales y recalcular los descuentos precalculados. Saleor recomienda **Saleor Configurator** (configuración en YAML, como código) cuando hay muchos canales.
- ⚠️ **No modelar Premium como canales aparte** (`es` y `es-premium`): doblaría los canales (6 → 12, 20 → 40) y el cliente podría elegir el canal Premium desde la tienda. Premium va en la app de precios (ver 1.6).
- **Limitación:** una moneda por canal y sin conversión automática. Trivial en la eurozona; para PLN, SEK, CHF… hay que mantener sus precios aparte.

## 1.5 Requisitos, uno a uno
| Requisito | ¿Lo cumple? | Cómo |
|---|---|---|
| R1 Multipaís | ✅ De serie | Un canal por país |
| R2 Precio por país | ✅ De serie | `productvariantchannellisting.price_amount` |
| R3 Precio mínimo | 🟡 A medida, **verificado** | El máximo de teemis va en `metadata` y lo hace respetar la app de precios. El caso 100 % teemis (mínimo 0 €) funciona |
| R4a Catálogo por país | ✅ De serie | `productchannellisting` |
| R4b Tema visual por país | ✅ Por diseño (headless) | El tema vive en nuestra tienda; su configuración puede ir en `channel.metadata` |
| R5 Teemis → descuento en checkout | 🟡 A medida, **viable y verificado** | App con `HANDLE_CHECKOUTS` que sobrescribe el precio de la línea (ver 1.6) |
| R6 Control del checkout | ✅ Total | El checkout es una API |
| R7 Panel CMS | 🟡 Bueno, con matices | Ver 1.7 |
| R8 Integraciones | ✅ Stripe / 🟡 Backend Toteemi y BC a medida | Ver 1.8 |
| R9 Madurez | ✅ | 23,5k estrellas, releases semanales, línea 3.x estable |
| R10 Suscripción Premium | ❌ No nativo | **Stripe Billing** fuera de Saleor (ver 1.6) |
| R11 Precio y productos solo Premium | 🟡 A medida | Misma app de precios + atributo `premium_only` + control en el BFF |
| R12 Productos especiales | ✅ Gift cards e inscripciones / 🟡 serials y packs | Gift cards nativas; inscripciones = producto sin envío; serials y packs no son nativos (app o modelado propio) |
| R13 Comprar y devolver teemis | 🟡 A medida | Webhooks `ORDER_FULLY_PAID` y `ORDER_REFUNDED` → backend Toteemi |
| R14 Cuenta única Toteemi | 🟡 A medida | Plugin OpenID Connect de Saleor o BFF que intercambia el token de Toteemi *(por validar)* |
| R15 Contenido web | ❌ Fuera de alcance | Saleor no es un CMS: hace falta un CMS headless o mantener WordPress solo para contenido |
| R16 Envíos por peso y CP | ✅ De serie | Zonas de envío + tarifas por peso + reglas de código postal |

## 1.6 Checkout, teemis y Premium

### Qué trae de serie
| Mecanismo | Alcance | ¿Por canal? | ¿Sirve para los teemis? |
|---|---|---|---|
| **Promoción de catálogo** | Rebaja automática de productos, categorías o colecciones | ✅ (por regla) | ❌ Es igual para todos los clientes |
| **Promoción de pedido** | Rebaja al subtotal o regalo si se supera un importe | ✅ | ❌ No se combina con vouchers y no depende del cliente |
| **Voucher** | Código en el checkout (pedido, producto, envío) | ✅ (valor, mínimo y países) | 🟡 Solo como apaño: un voucher por cliente y pedido, y ocupa el único hueco de código promocional |
| **Gift card** | Saldo en una moneda que se aplica al total | Por moneda | 🟡 Sirve como monedero, pero **no permite un máximo por producto**, y además el saldo ya vive en el backend Toteemi |
| **Descuento manual** | Lo aplica el staff en pedidos borrador | — | ❌ No es autoservicio |
| **Precio sobrescrito por una app** (`price` en `CheckoutLineInput`) | Cambia el precio unitario de una línea | Implícito (el checkout pertenece a un canal) | ✅ **Este es el mecanismo** |

Reglas de combinación (según la documentación): de las promociones de catálogo solo se aplica la que más descuenta; las de pedido se calculan sobre el precio ya rebajado; un voucher **anula** las promociones de pedido; y el voucher o la promoción **se aplican después** del precio sobrescrito.

### Diseño propuesto: "App de precios Toteemi"
Una sola app que hace lo que hoy hace el plugin `toteemi` de WordPress: **teemis + precio Premium + precio mínimo**.

```mermaid
sequenceDiagram
  participant C as Cliente (tienda)
  participant BFF as BFF de la tienda
  participant P as App de precios Toteemi
  participant S as Saleor API
  participant T as Backend Toteemi (wallet)
  participant ST as Stripe
  C->>BFF: activa "Usar mis teemis"
  BFF->>P: aplicar(checkoutId, usuario)
  P->>T: saldo + ¿es Premium?
  P->>S: lee las líneas, el canal y metadata.teemis_max.<canal>
  P->>P: precio = precio Premium si aplica<br/>reparte teemis por línea<br/>precio final = max(base − teemis×valor, mínimo)
  P->>S: checkoutLinesUpdate(price, priceOverrideReason, metadata)
  S-->>BFF: total recalculado
  Note over S,P: CHECKOUT_UPDATED → la app recalcula sola<br/>(se acabó el "recalcula tu ahorro aquí")
  BFF->>P: validar antes de cerrar (Premium, saldo, mínimo)
  alt total > 0
    BFF->>S: transactionInitialize (app Stripe)
    S->>ST: PaymentIntent por el total ya rebajado
  else total = 0 (100 % teemis)
    BFF->>S: checkoutComplete sin pago
  end
  S-->>P: ORDER_FULLY_PAID / ORDER_CREATED
  P->>T: SPENT_STORE (descuenta teemis)
  S-->>P: ORDER_REFUNDED
  P->>T: REFUND (devuelve teemis)
```

**Pruebas de concepto (verificadas en local):**
1. App con permiso `HANDLE_CHECKOUTS` + checkout con una variante de **45 $** → `checkoutLinesUpdate(price: 40, priceOverrideReason: "teemis: 5 canjeados")` → total **40 $**. ✅
2. La misma llamada con un token de **staff** (que no es app) se **rechaza**. ✅ Solo nuestra app puede cambiar precios, nunca el cliente desde la tienda.
3. **Producto pagado al 100 % con teemis:** precio sobrescrito a **0** → `chargeStatus: FULL` → `checkoutComplete` crea el pedido **sin pasar por el pago**. ✅

> 🔁 Estas pruebas, y el resto de afirmaciones marcadas como "verificado en local", se repiten con `python3 saleor/verificacion/verificar.py` (22 comprobaciones).

**Detalles a tener en cuenta:**
- **IVA:** el precio que fija la app se trata como si se hubiera introducido igual que el resto de precios del canal. En el canal de ejemplo (precios sin IVA), sobrescribir a 40 con una dirección en España da un total de **48,40** (21 % de IVA, verificado). Para Europa hay que configurar los canales con **precios con IVA incluido** (`tax_taxconfiguration.prices_entered_with_tax = true`), igual que muestra hoy la tienda ("IVA incl."). Así el precio mínimo y el ahorro en teemis que ve el cliente coinciden con lo que paga.
- El precio sobrescrito pasa a ser el **precio base** de la línea, así que en el pedido **no aparece como "descuento"**. La trazabilidad hay que llevarla en `price_override_reason` y en la `metadata` de la línea (por ejemplo `teemis_usados=5`).
- **Recalcular cuando cambia el checkout:** con el webhook `CHECKOUT_UPDATED` la app recalcula sola cuando cambian las cantidades, se añaden líneas o se aplica un voucher. Esto **arregla el problema actual** del carrito de WooCommerce. Como el webhook es asíncrono, el **BFF tiene que volver a validar justo antes de cerrar el checkout**.
- **Riesgo de saltarse el precio mínimo:** un voucher o una promoción se aplican **encima** del precio sobrescrito. La app debe descontarlos al calcular, o el negocio tiene que decidir que teemis y vouchers no se combinan.
- **Reservar el saldo:** entre aplicar los teemis y pagar, el saldo puede cambiar (por ejemplo, si caducan: `EXPIRED`). Hace falta reservar en el backend o volver a validar al cerrar.
- **Pedidos de 0 €:** no hay pago, pero hay que registrar igualmente el `SPENT_STORE`. La app debería escuchar `ORDER_CREATED` y comprobar el `chargeStatus`, en lugar de depender solo de `ORDER_FULLY_PAID` *(falta verificar qué eventos se disparan en un pedido de 0 €)*.

### Precio y productos solo para Premium
- **Precio Premium:** la misma app aplica el precio Premium (guardado en `metadata` de la variante por canal, o en el backend) cuando el backend confirma que el usuario es Premium. Así hay un solo punto que decide el precio.
- **Productos exclusivos:** atributo `premium_only`. La tienda los muestra u oculta y **el BFF bloquea el cierre del checkout** si un usuario no Premium los lleva. Saleor no puede limitar la visibilidad de un producto a un tipo de cliente.

### Suscripción Premium (mensual y anual)
Saleor **no tiene suscripciones**. La propuesta es sacar Premium del e-commerce:
- **Stripe Billing** (suscripciones y *Customer Portal* para gestionarlas) → webhook → el backend Toteemi activa o desactiva `is_premium`.
- En la app solo cambian `PREMIUM_UPGRADE_URL` y `PREMIUM_SUBSCRIPTION_DETAILS_URL`, que apuntarían a Stripe Checkout y Customer Portal.
- **Migrar las suscripciones activas de WooCommerce Subscriptions**: si hoy se cobran con Stripe, los métodos de pago ya están allí y la migración es sencilla. Si no, hay que pedir a los clientes que vuelvan a introducir la tarjeta. → **pregunta abierta**.

### Descuentos por país sin teemis
Para campañas normales por país (por ejemplo "Navidad FR −20 %"), las **promociones** y los **vouchers** son por canal y se gestionan desde el panel sin programar.

## 1.7 Panel de administración (Dashboard)
Qué ofrece: productos, variantes y atributos; precios y disponibilidad por país; promociones; vouchers; gift cards; pedidos, devoluciones y reembolsos (con Stripe); clientes; traducciones; y permisos por grupo **y por canal** (por ejemplo, que el equipo de Francia solo vea pedidos de Francia).

### Prueba real: la operativa de abrir un país nuevo (verificado en local)
He hecho desde el panel, con un navegador automatizado y sin usar la API, lo que haría alguien de operaciones al abrir España. Después he comprobado el resultado en la base de datos.

| Tarea | Cómo se hace | Valoración |
|---|---|---|
| **1. Crear el canal "España"** | *Configuration → Channels → Create*: nombre, slug y país. **Al elegir el país, rellena solo la moneda (EUR)** | ✅ Muy fácil (3 clics). Después aparece una **lista guiada** ("Finish setting up this channel"): almacén, envíos, pasarela de pago, productos e impuestos, con lo que falta para poder vender |
| **2. Poner un producto a la venta en España con su precio** | Ficha del producto → *Availability → Manage* → marcar España. Después, en *Variants → Bulk edit*, una **tabla tipo Excel con una columna por país** (Disponible y Precio): doble clic en la celda, escribir el precio e Intro | ✅ Cómodo para pocos productos; con cientos se hace largo (no hay importación CSV) |
| **3. Promoción "−20 % en camisetas" solo en España** | *Discounts → Promotions → Create* → *Add rule*: canal, porcentaje y condición "Products is Monospace Tee" | 🟡 Se entiende, pero **cada regla vale para un solo canal** (6 países = 6 reglas), los desplegables de la condición no tienen etiqueta y el valor por defecto es importe fijo (EUR), no porcentaje |

**Problemas encontrados en la prueba:**
- ⚠️ **Precio 0 € por defecto:** al marcar una variante como disponible en un país **sin escribir precio**, el panel la guarda **a 0,00 €** (verificado en la BD). Si además el producto está publicado, se vendería gratis. Hace falta una validación propia (por ejemplo, la app de precios avisa o bloquea los precios a 0 €) o una revisión antes de publicar.
- ⚠️ **La promoción tardó en aplicarse:** se guardó al momento, pero el precio rebajado del catálogo no cambió hasta **reiniciar el planificador de tareas** (Celery beat). Después de reiniciar se aplicó en menos de un minuto (24,95 € → 19,96 €). Lo he reproducido con una segunda promoción: beat lanza el recálculo una vez y luego deja de lanzarlo, aunque está programado cada 30 s. **No he podido determinar la causa** (puede ser propio de este entorno local) y no he encontrado ninguna incidencia publicada. En producción hay que **monitorizar que el recálculo se ejecuta**, o usar Saleor Cloud, que lo opera Saleor.
- ✅ **IVA:** los canales nuevos creados desde el panel se crean con **precios con IVA incluido** (`prices_entered_with_tax = true`, verificado), que es lo que necesitamos en Europa.
- ✅ **Idioma del panel:** viene en inglés, pero trae traducciones a español, francés, alemán, italiano, polaco y portugués (verificado en los ficheros del panel).
- La página de inicio sale vacía: las métricas de ventas necesitan instalar una app aparte ("Pulse").

**Valoración:** apto para que personal no técnico gestione el día a día (precios, disponibilidad por país, pedidos, campañas sencillas). Las cargas masivas y la configuración de un país nuevo de principio a fin (almacén, envíos, pagos, impuestos) piden algo de formación o de soporte técnico la primera vez.

**Carencias para nuestro caso:**
  - **No hay importación masiva de productos ni precios desde CSV** (solo exportación; verificado en local: solo existen `csv_exportfile`/`csv_exportevent`). Para la migración desde WooCommerce y la carga de 6 países hará falta un script, Configurator o una app.
  - **Los teemis y el precio Premium no aparecen en el panel** si no hacemos una extensión. Recomendación: un widget en la ficha de producto ("máximo de teemis y precio Premium por país") dentro de la app de precios.
  - No es un CMS de contenidos (páginas, banners, la web corporativa). Hay app oficial para conectar un CMS headless.

## 1.8 Integraciones
| Sistema | Tipo | Mecanismo | Notas |
|---|---|---|---|
| **Stripe (pagos)** | ✅ **Oficial** (repositorio `saleor/apps`) | App + Transactions API + webhooks de Stripe | Pago con captura diferida o inmediata; captura, cancelación y reembolso desde el panel; configuración por canal. Requiere Saleor 3.23. Limitaciones: no soporta Stripe Checkout (página alojada), solo una captura por autorización y la configuración no se puede editar (hay que recrearla) |
| **Stripe Billing (Premium)** | 🔧 Fuera de Saleor | Stripe Checkout + Customer Portal + webhooks → backend Toteemi | Sustituye a WooCommerce Subscriptions |
| **Backend Toteemi** (wallet, Premium) | 🔧 A medida | La app de precios llama a su REST (v3) y le envía `SPENT_STORE`, `BOUGHT_STORE` y `REFUND` a partir de los webhooks de Saleor | Hoy lo hace el plugin `toteemi` de WordPress: la lógica se puede portar |
| **Business Central** | 🔧 **A medida** | Webhooks de Saleor (pedidos, clientes) → conector → API REST/OData v2.0 de BC; en sentido contrario (stock, precios), webhooks o sondeo de BC → GraphQL de Saleor | **No existe conector oficial ni de la comunidad.** (BC sí trae conector nativo para Shopify, un dato relevante para la comparativa) |
| **Inicio de sesión Toteemi** | 🔧 A medida *(por validar)* | Plugin OpenID Connect de Saleor, o BFF que valida el token de Toteemi y opera con un token de app | Necesario para "Loguéate para ver tu precio" |

Otras apps oficiales mantenidas en `saleor/apps`: AvaTax (impuestos), CMS, Klaviyo, Search (Algolia), Segment, SMTP, Products feed.

## 1.9 Ecosistema y comunidad
| Indicador | Dato (23/10/2026) |
|---|---|
| Estrellas / forks en GitHub (core) | **23.466 / 6.156** |
| Último commit en `main` | 23/10/2026 (hoy) |
| Cadencia de releases | Varias por semana (parches y seguridad). Se mantienen **dos líneas** a la vez (3.22.x y 3.23.x) |
| Issues abiertos | ~300 |
| Dashboard | ~1.000 estrellas, activo |
| Apps oficiales | 9 en el monorepo `saleor/apps` (163 estrellas) |
| Empresa detrás | Saleor Commerce (vive de Saleor Cloud), con red de partners |

**Empresas que lo usan** (página oficial de casos de éxito): **Lush** (toda su tienda online global), **Breitling** (relojería, Suiza), **PCDIGA** (mayor tienda online de electrónica de Portugal), Kencove (B2B), Rough Trade, Pretty Green, myenergi… Del sector deportivo hay **Ale Bikewear** (ropa de ciclismo) y **Bikebiz**. Algunas (Butterfly Network, Seven Cells, TBD Health, Yuno) aparecen en la categoría "Subscriptions", lo que confirma que las suscripciones se montan con piezas externas encima de Saleor.

**Dónde está la comunidad:**
- **Discord** (saleor.io/discord): canal principal para preguntas y propuestas, con un *Community Update* mensual.
- **GitHub Issues:** solo para bugs; la documentación pide expresamente no usarlo para preguntas.
- **Stack Overflow:** etiqueta `saleor`.
- No hay un foro clásico. El soporte "con contrato" (canal de Slack dedicado y arquitecto asignado) solo viene con Saleor Cloud.

- **Comunidad más pequeña** que la de Shopify o WooCommerce: hay **pocas apps de terceros**. Cosas que hoy resuelve un plugin de WooCommerce (suscripciones, packs, serials, wishlist) aquí son **desarrollo propio o servicio externo**.
- A cambio, **hacer una app es sencillo** y está documentado (SDK de TypeScript, plantilla de app, App Bridge para el panel).
- No es de nicho ni experimental: la 3.x es estable desde hace años y la API está versionada, con avisos de *deprecation*.

## 1.10 De WooCommerce a Saleor: qué pasa con cada pieza
| Hoy (WooCommerce) | En Saleor | Esfuerzo |
|---|---|---|
| Catálogo, variantes, ofertas | Nativo (productos, variantes, promociones de catálogo) | Migración de datos |
| Plugin `toteemi`: canje en el carrito, precio mínimo, 100 % teemis, solo euros | **App de precios Toteemi** (precio sobrescrito + `metadata`) | Alto |
| `only-premium-price`, productos Premium | App de precios + atributo + BFF | Medio |
| WooCommerce Subscriptions (Premium) | **Stripe Billing** | Medio + migración |
| Gift cards | Nativo | Bajo |
| WC Serial Numbers | App propia (pool de códigos) o producto digital | Medio |
| Inscripciones y experiencias | Producto sin envío | Bajo |
| Easy Product Bundles (packs) | Producto propio con stock gestionado por una app, o pack como producto independiente | Medio |
| Wishlist, carrito lateral | En la tienda propia (wishlist en `user.metadata`) | Bajo |
| Envío por peso y CP (APG) | Nativo (zonas, tarifas por peso, reglas de CP) | Bajo |
| Web corporativa, WPForms, cookies | CMS headless, o WordPress solo como CMS | Medio |
| Inicio de sesión con la cuenta Toteemi | OIDC o BFF | Medio |

## 1.11 Puntos fuertes, débiles y riesgos
**Puntos fuertes**
- Multipaís, precio por país y catálogo por país **nativos y bien modelados** en la base de datos.
- **Control total del checkout** y mecanismo oficial para precios a medida desde una app. Permite arreglar el "recalcula tu ahorro" actual.
- Extensión mediante apps desacopladas: **actualizar no rompe nada**, al contrario que con los plugins de WordPress.
- Open source BSD-3: sin dependencia del proveedor y con la opción de Cloud gestionado.
- Stripe oficial; gift cards y envíos por código postal nativos; permisos por canal en el panel.

**Puntos débiles**
- **Hay que construir la tienda y el checkout** (es headless): mucho más trabajo inicial que con una plataforma con temas.
- **No tiene suscripciones, grupos de clientes ni listas de precios**: Premium hay que resolverlo fuera.
- **Teemis, precio mínimo, Premium, Business Central e inicio de sesión: desarrollo a medida.**
- Ecosistema de apps pequeño: muchas cosas que hoy son un plugin aquí son desarrollo propio.
- No importa CSV en el panel. No hay webhook síncrono de descuentos ni de validación.

**Riesgos**
| Riesgo | Impacto | Mitigación |
|---|---|---|
| El precio mínimo se rompe al combinar teemis con vouchers o promociones | Alto | La app los descuenta al calcular y el BFF valida al cerrar, o se prohíbe por negocio combinarlos |
| Migración de las suscripciones Premium activas | Alto | Si hoy se cobran con Stripe, se migran a Stripe Billing con los mismos métodos de pago |
| Coste de desarrollar la tienda, el checkout, la app de precios, el conector de BC y el inicio de sesión | Alto | Partir de la tienda de referencia y del SDK de apps; portar la lógica del plugin `toteemi`; valorar el *Forward Deployed Engineering* de Saleor |
| Saldo de teemis inconsistente entre aplicar y pagar | Medio | Reservar en el backend Toteemi y volver a validar al cerrar |
| La web corporativa se queda sin sitio al dejar WordPress | Medio | Decidir CMS (WordPress headless o un CMS headless) |
| Operación propia (self-hosted) | Medio | Saleor Cloud, o infraestructura gestionada en AWS (RDS y ElastiCache) |
| El recálculo de promociones se queda parado (observado en local) | Medio | Planificador (beat) como servicio aparte, alerta si los precios rebajados no se recalculan; Saleor Cloud |
| Productos publicados a 0 € por despiste en el panel | Medio | Validación en la app de precios y revisión antes de publicar |
| Facturas legales por país | Medio | Que las emita Business Central y se enlacen al pedido en Saleor (`invoice.external_url`); ver el apartado 6 |

## Fuentes
- [Saleor – GitHub](https://github.com/saleor/saleor) · [Releases](https://github.com/saleor/saleor/releases) · [saleor-platform (Docker)](https://github.com/saleor/saleor-platform) · [Apps oficiales](https://github.com/saleor/apps)
- [Precios de Saleor Cloud](https://saleor.io/pricing)
- [Docs: Canales](https://docs.saleor.io/developer/channels/overview) · [Descuentos](https://docs.saleor.io/developer/discounts/overview) · [Promociones](https://docs.saleor.io/developer/discounts/promotions) · [Gift cards](https://docs.saleor.io/developer/gift-cards)
- [Docs: Líneas de checkout y precio a medida](https://docs.saleor.io/docs/3.x/developer/checkout/lines) · [CheckoutLineInput](https://docs.saleor.io/api-reference/checkout/inputs/checkout-line-input)
- [Docs: Webhooks síncronos](https://docs.saleor.io/developer/extending/webhooks/synchronous-events/overview) · [Extender el Dashboard con apps](https://docs.saleor.io/developer/extending/apps/extending-dashboard-with-apps)
- [Docs: App de Stripe](https://docs.saleor.io/developer/app-store/apps/stripe/overview)
- [Saleor limitations (Swell, competidor: tomarlo con cautela)](https://www.swell.is/content/saleor-limitations)
- [Casos de éxito de Saleor](https://saleor.io/case-study) · [Soporte y comunidad](https://docs.saleor.io/developer/community/support) · [App de facturas](https://docs.saleor.io/developer/app-store/apps/invoices) · [Cálculo de precios e impuestos](https://docs.saleor.io/developer/price-calculation)
- [Business Central – visión general de integraciones](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/developer/integration-overview)
- Repositorio de la app Toteemi (`docs/teemis.md`, `docs/modules/wallet.md`, `envs/*.json`) y tienda pública `toteemi.com`

---

# 4. Tabla comparativa

Leyenda: ✅ de serie · 🟡 posible con desarrollo o con matices · ❌ no cumple · ⏳ pendiente de investigar

| Criterio | Saleor | Medusa | Shopify Plus |
|---|---|---|---|
| **Licencia** | Open source BSD-3 | ⏳ | ⏳ |
| **Precio** | Self-hosted: 0 € más infraestructura · Cloud: desde 1.599 $/mes (≤200k $ de GMV al mes, 0,8 % por encima) | ⏳ | ⏳ |
| **Arquitectura** | Headless, API GraphQL, monolito modular en Django, extensión con apps externas | ⏳ | ⏳ |
| **Base de datos** | PostgreSQL (relacional) | ⏳ | ⏳ |
| **Multipaís (R1)** | ✅ Canales (uno por país, sin límite documentado) | ⏳ | ⏳ |
| **Precio por país (R2)** | ✅ Precio por variante y canal | ⏳ | ⏳ |
| **Precio mínimo por país (R3)** | 🟡 Lo aplica una app propia (**PoC verificada**, incluido el 100 % teemis) | ⏳ | ⏳ |
| **Catálogo por país (R4)** | ✅ Publicación por canal | ⏳ | ⏳ |
| **Tema visual por país (R4)** | ✅ Por diseño: la tienda es nuestra | ⏳ | ⏳ |
| **Teemis → descuento en checkout (R5)** | 🟡 App con `HANDLE_CHECKOUTS` que sobrescribe el precio de la línea (**PoC verificada**) | ⏳ | ⏳ |
| **Control del checkout (R6)** | ✅ Total (checkout por API y frontend propio) | ⏳ | ⏳ |
| **Panel no técnico (R7)** | 🟡 Bueno; sin importación CSV; los teemis necesitan una extensión | ⏳ | ⏳ |
| **Stripe** | ✅ App oficial | ⏳ | ⏳ |
| **Business Central** | 🟡 A medida (webhooks + API de BC) | ⏳ | ⏳ |
| **Backend Toteemi (wallet)** | 🟡 A medida (webhooks → REST del backend) | ⏳ | ⏳ |
| **Suscripción Premium (R10)** | ❌ No nativo → Stripe Billing | ⏳ | ⏳ |
| **Precio y productos solo Premium (R11)** | 🟡 Sin grupos de clientes; app de precios + BFF | ⏳ | ⏳ |
| **Gift cards, serials, packs (R12)** | ✅ Gift cards / 🟡 serials y packs | ⏳ | ⏳ |
| **Inicio de sesión con la cuenta Toteemi (R14)** | 🟡 OIDC o BFF (por validar) | ⏳ | ⏳ |
| **Contenido web (R15)** | ❌ Necesita un CMS aparte | ⏳ | ⏳ |
| **Envíos por peso y CP (R16)** | ✅ Nativo | ⏳ | ⏳ |
| **Comunidad** | 23,5k ⭐, releases semanales | ⏳ | ⏳ |
| **Ecosistema de plugins o apps** | Pequeño (9 apps oficiales); fácil hacer apps propias | ⏳ | ⏳ |
| **Escalado a más países** | Lineal en filas (variantes × canales); el coste está en la operativa | ⏳ | ⏳ |
| **Esfuerzo inicial** | Alto (tienda, checkout, app de precios, Premium, BC) | ⏳ | ⏳ |
| **IVA por país (R17)** | ✅ Tipos por país y por clase de producto; precios con IVA por canal | ⏳ | ⏳ |
| **Facturas legales (R17)** | 🟡 La app oficial es básica (solo en inglés) → que facture Business Central | ⏳ | ⏳ |
| **Idiomas (R18)** | ✅ Traducciones nativas (14 entidades); panel en español | ⏳ | ⏳ |
| **SEO (R19)** | ✅ Slug y SEO traducibles; las URLs y las 301 las controla la tienda propia | ⏳ | ⏳ |
| **Migración desde WooCommerce (R19)** | 🟡 Sin herramienta oficial → script propio | ⏳ | ⏳ |
| **Usabilidad del panel (probado)** | 🟡 Abrir un país y fijar precios es fácil; las promociones van regla a regla por país; ⚠️ guarda precio 0 € si no se rellena | ⏳ | ⏳ |
| **Coste de infraestructura** | Self-hosted ≈ 450–650 $/mes · Cloud desde 1.599 $/mes (más tienda y apps) | ⏳ | ⏳ |
| **Esfuerzo de desarrollo** | ≈ 29–44 semanas-persona (orientativo) | ⏳ | ⏳ |
| **Riesgo principal** | Coste de desarrollo, precio mínimo frente a vouchers, migración de suscripciones | ⏳ | ⏳ |

---

# 5. Recomendación

> ⏳ **Recomendación final pendiente**: falta el análisis de Medusa (en curso) y el de Shopify Plus (sin asignar). Aquí va la conclusión parcial sobre Saleor.

## Conclusión sobre Saleor
**Saleor es candidata viable.** Cubre de serie la parte estructural: multipaís, precios y catálogo por país, envíos, gift cards, Stripe y control total del checkout. El requisito crítico, que los teemis se conviertan en descuento en el checkout, **se puede implementar con un mecanismo oficial de la API** (precio sobrescrito desde una app). Lo he comprobado en local, incluido el caso de un producto pagado al 100 % con teemis. Además resolvería un fallo actual: el descuento se recalcularía solo cuando cambia el carrito.

Pero la tienda actual hace más de lo que decía el encargo, y **Saleor no cubre todo eso de serie**: la suscripción Premium, el precio solo para Premium, el inicio de sesión con la cuenta Toteemi y la web de contenidos.

**Lo que habría que construir o contratar:**
1. Tienda y checkout (Next.js, partiendo de la tienda de referencia de Saleor) con un BFF que valide antes de cerrar.
2. **App de precios Toteemi**: teemis, precio mínimo y precio Premium, integrada con la wallet del backend Toteemi y con una extensión del panel. En buena parte es **portar la lógica del plugin `toteemi`** de WordPress.
3. **Premium con Stripe Billing**, más la migración de las suscripciones activas.
4. **Conector con Business Central**.
5. Inicio de sesión con la cuenta Toteemi.
6. Un sitio para la web corporativa (CMS headless o WordPress solo como CMS).
7. Migración de datos desde WooCommerce (productos, clientes, pedidos) y redirecciones 301 para no perder SEO.
8. Facturación legal multipaís desde Business Central (la app de facturas de Saleor no basta) y la configuración del IVA por país.

**Orden de magnitud** (apartado 6.6, orientativo): **≈ 29–44 semanas-persona** de desarrollo (unos 3–4 meses con 3 personas) e infraestructura de **≈ 450–650 $/mes** si es self-hosted en AWS, o desde 1.599 $/mes con Saleor Cloud más la tienda y las apps.

**Lo que dice la prueba del panel:** sirve para el día a día de un equipo no técnico (crear un país, poner precios, lanzar campañas). Pero hay dos cosas que vigilar: que no se publiquen productos a 0 € y que el recálculo de promociones se ejecute.

**Cuándo elegiría Saleor:** si el equipo tiene capacidad para construir la tienda y mantener 2 o 3 servicios propios, y se valora no depender de un proveedor y tener control total del checkout y de la lógica de teemis.

**Cuándo no:** si se necesita salir muy rápido con poco desarrollo, o si el negocio quiere seguir resolviendo suscripciones, packs, serials, etc. con plugins ya hechos.

## Preguntas abiertas para el negocio
1. ¿Los teemis se pueden **combinar** con vouchers o promociones? Si se pueden, hay que garantizar el precio mínimo después de aplicarlos.
2. ¿El "backoffice propio" es el backend Toteemi (`api.toteemi.com`)? ¿Puede exponer un endpoint para reservar y confirmar teemis?
3. ¿Con qué pasarela se cobran hoy las suscripciones Premium? ¿Se pueden sacar del e-commerce y pasar a Stripe Billing?
4. ¿Tenemos acceso al código del plugin `toteemi` de WordPress?
5. ¿Los 6 países son todos de la **eurozona**? Saleor usa una moneda por canal. ¿Y en qué idiomas hay que vender?
6. ¿Quién emite hoy las facturas, WooCommerce o Business Central? ¿Ya se tributa por OSS?
7. ¿La web corporativa se muda también o se queda en WordPress solo como CMS?
8. ¿Preferimos **self-hosted** en AWS (más trabajo de operación) o **Saleor Cloud** (desde 1.599 $/mes)?

---

# 6. Aspectos transversales: IVA, facturación, idiomas, SEO, migración y coste

> Estos puntos **no estaban en el encargo**, pero afectan a la decisión sea cual sea la plataforma. En cada uno se indica qué haría falta con Saleor, para que Medusa y Shopify Plus se puedan comparar con el mismo criterio.
> ⚖️ Lo fiscal es orientativo: hay que validarlo con la asesoría.

## 6.1 IVA en varios países
- **Qué cambia:** al vender a particulares de otros países de la UE, por encima de 10.000 € anuales de ventas transfronterizas se aplica el **IVA del país del cliente**, y se declara en España mediante la **ventanilla única (OSS)**.
- **Qué necesita la plataforma:** el tipo de IVA de cada país y de cada tipo de producto (no es igual para ropa, nutrición, inscripciones o productos digitales), precios con IVA incluido por país y un informe de ventas por país para la declaración.
- **En Saleor:** ✅ **tipos fijos por país y por clase de producto** (`tax_taxclasscountryrate`), configuración de impuestos por canal y precios con IVA incluido por canal (verificado: los canales nuevos ya vienen así). Para no mantener los tipos a mano hay app de AvaTax (de pago). El informe OSS saldría de los pedidos (export o Business Central).

## 6.2 Facturación
- **Qué hace falta:** factura legal por pedido, con numeración, datos fiscales y el idioma y los requisitos de cada país. En España, además, la normativa **VeriFactu** sobre el software de facturación (comprobar plazos y alcance con la asesoría).
- **En Saleor:** 🟡 la **app oficial de facturas** es muy básica: PDF con plantilla fija, **solo en inglés**. **No sirve como factura legal multipaís.**
- **Recomendación:** que **facture Business Central**, que es el ERP y ya tiene la localización española y la contabilidad. Saleor guarda la referencia: la tabla `invoice_invoice` tiene `external_url` (verificado), así que el conector de BC puede enlazar la factura al pedido y el cliente la ve desde su cuenta. → **Esto añade alcance al conector de BC.**

## 6.3 Idiomas
- **Qué cambia:** 6 países son varios idiomas en el catálogo, la tienda, los emails y las condiciones legales. La app de Toteemi hoy solo está en **español e inglés**.
- **En Saleor:** ✅ traducciones nativas de productos, variantes, categorías, colecciones, atributos, promociones, vouchers, páginas, menús y métodos de envío. Son **14 tablas `*translation`**, con `slug`, `seo_title` y `seo_description` traducibles (verificado). El panel tiene una sección *Translations*. El idioma lo elige la tienda en cada consulta (`languageCode`), sin depender del canal.
- **Lo que no cubre:** los textos de la propia tienda (botones, checkout) y los emails, que son responsabilidad del frontend o de la app de emails.
- **Coste oculto:** traducir el catálogo (descripciones de cientos de productos) es trabajo de contenido, no técnico. Conviene presupuestarlo aparte.

## 6.4 SEO
- **Riesgo:** al cambiar de plataforma cambian las URLs (hoy `toteemi.com/producto/<slug>/`). Sin **redirecciones 301** se pierde el posicionamiento ganado.
- **En Saleor:** ✅ cada producto, categoría y colección tiene `slug`, `seo_title` y `seo_description` (también traducibles, verificado). Como la tienda es nuestra, **se puede mantener exactamente la misma estructura de URL** (`/producto/<slug>/`) reutilizando los slugs de WooCommerce, y así la mayoría de URLs no cambian.
- **A cargo de la tienda (Next.js), no de Saleor:** las redirecciones de las URLs que cambien, el sitemap, `hreflang` entre países e idiomas, los datos estructurados de producto y el rendimiento.
- **Checklist de migración:** listar todas las URLs indexadas actuales → mapear cada una a su URL nueva → 301 → enviar el sitemap nuevo a Search Console → vigilar los errores 404 las primeras semanas.

## 6.5 Migración de datos desde WooCommerce
| Dato | Cómo | Dificultad |
|---|---|---|
| Productos, variantes, categorías, imágenes | Script: API REST de WooCommerce → GraphQL de Saleor (con `externalReference`, que ya admiten productos, promociones, vouchers y colecciones) | Media. Las variaciones y los atributos de WooCommerce no encajan 1:1 con los tipos de producto de Saleor |
| Clientes | Script. **Las contraseñas no se migran**; si el inicio de sesión va con la cuenta Toteemi, no hace falta | Baja |
| Historial de pedidos | Script (como pedidos importados) o dejarlo consultable en Business Central | Media; decidir si de verdad hace falta en la tienda |
| **Suscripciones Premium activas** | A Stripe Billing (ver 1.6) | **Alta** si no se cobran hoy con Stripe |
| Saldos de teemis | No se migran: ya viven en el backend Toteemi | — |
| Gift cards emitidas y códigos pendientes | Script a gift cards de Saleor y a la app de códigos | Media |
| Contenido web (páginas, blog) | Según la decisión de CMS | Media |

- **No hay herramienta oficial** de migración de WooCommerce a Saleor. Existen servicios de pago (Cart2Cart) basados en CSV, pero para este volumen y con lo propio de Toteemi (teemis, Premium) compensa un **script propio**, que además sirve para cargar los 6 países.
- **Corte:** congelar los cambios de catálogo unos días, hacer una migración de prueba, validar y luego hacer el corte definitivo con las redirecciones activadas.

## 6.6 Coste total (orden de magnitud)
> ⚠️ **Estimación orientativa** para comparar plataformas, **no un presupuesto**. Los precios de AWS son aproximados (región eu-west-1) y hay que validarlos con la calculadora de AWS. El esfuerzo hay que revisarlo con el equipo que lo vaya a hacer.

### Infraestructura (self-hosted en AWS, al mes)
| Pieza | Dimensionado inicial | ≈ USD/mes |
|---|---|---|
| API de Saleor | 2 contenedores (1 vCPU, 2 GB) en ECS Fargate | 70–80 |
| Worker + beat | 1 + 1 contenedores pequeños | 40–50 |
| Tienda Next.js | 2 contenedores, o Vercel | 70–150 |
| Apps propias (precios, conector BC, Stripe) | 3 contenedores pequeños | 50–60 |
| PostgreSQL | RDS db.t4g.medium Multi-AZ | 130–150 |
| Redis / Valkey | ElastiCache, nodo pequeño | 25–50 |
| Balanceador, S3 + CloudFront, logs y monitorización | — | 60–120 |
| **Total** | | **≈ 450–650 $/mes** |

Comparativa: **Saleor Cloud Select** cuesta 1.599 $/mes (hasta 200.000 $ de GMV al mes) **sin incluir** la tienda, las apps propias ni el CMS, que se alojarían igualmente aparte. Lo que se paga es no tener que operar Saleor y el soporte.

### Desarrollo (semanas-persona)
| Bloque | Rango |
|---|---|
| Tienda + checkout + BFF (temas por país, i18n, SEO) | 8–12 |
| App de precios Toteemi (teemis, precio mínimo, Premium, extensión del panel) | 4–6 |
| Premium con Stripe Billing + migración de suscripciones | 2–3 |
| Conector con Business Central (pedidos, clientes, stock, facturas) | 4–6 |
| Inicio de sesión con la cuenta Toteemi | 1–2 |
| Migración de datos + redirecciones SEO | 2–3 |
| Web corporativa / CMS | 3–5 |
| Infraestructura, CI/CD y observabilidad | 2–3 |
| QA, pruebas de carga y salida a producción | 3–4 |
| **Total** | **≈ 29–44 semanas-persona** |

Con un equipo de 3 personas, unos **3–4 meses** hasta la salida. No incluye la traducción del catálogo, la configuración fiscal con la asesoría ni el trabajo de diseño de los temas.

## Fuentes
- [Saleor: cálculo de precios e impuestos](https://docs.saleor.io/developer/price-calculation) · [App de facturas](https://docs.saleor.io/developer/app-store/apps/invoices)
- [Cart2Cart: migración a Saleor](https://www.shopping-cart-migration.com/planned-shopping-carts/saleor)
- [Precios de Saleor Cloud](https://saleor.io/pricing)
- Esquema de la BD local de Saleor 3.23 (tablas `*translation`, `invoice_invoice`, `tax_*`)

---

