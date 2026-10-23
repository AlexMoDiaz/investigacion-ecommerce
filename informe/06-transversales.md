# 6. Aspectos transversales: IVA, facturación, idiomas, SEO, migración y coste

> Estos puntos **no estaban en el encargo**, pero afectan a la decisión sea cual sea la plataforma. En cada uno se indica qué haría falta con Saleor, para que Medusa y Shopify Plus se puedan comparar con el mismo criterio.
> ⚖️ Lo fiscal es orientativo: hay que validarlo con la asesoría.

## 6.1 IVA en varios países
- **Qué cambia:** al vender a particulares de otros países de la UE, por encima de 10.000 € anuales de ventas transfronterizas se aplica el **IVA del país del cliente**, y se declara en España mediante la **ventanilla única (OSS)**.
- **Qué necesita la plataforma:** el tipo de IVA de cada país y de cada tipo de producto (no es igual para ropa, nutrición, inscripciones o productos digitales), precios con IVA incluido por país y un informe de ventas por país para la declaración.
- **En Saleor:** ✅ **tipos fijos por país y por clase de producto** (`tax_taxclasscountryrate`), configuración de impuestos por canal y precios con IVA incluido por canal (verificado: los canales nuevos ya vienen así). Para no mantener los tipos a mano hay app de AvaTax (de pago). El informe OSS saldría de los pedidos (export o Business Central).

## 6.2 Facturación
- **Qué hace falta:** factura legal por pedido, con numeración, datos fiscales y el idioma y los requisitos de cada país. En España, además, la normativa **VeriFactu** sobre el software de facturación (comprobar plazos y alcance con la asesoría).
- **En Saleor:** 🟡 Saleor guarda facturas en el pedido (`invoiceCreate`/`invoiceRequest`), pero **no las genera**: la app oficial de facturas, que era muy básica, **se eliminó del repositorio en agosto de 2024** (commit *Remove Invoices app from monorepo*). **No hay nada que sirva como factura legal multipaís.**
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
- [Saleor: cálculo de precios e impuestos](https://docs.saleor.io/developer/price-calculation) · [Eliminación de la app de facturas (saleor/apps #1496)](https://github.com/saleor/apps/pull/1496)
- [Cart2Cart: migración a Saleor](https://www.shopping-cart-migration.com/planned-shopping-carts/saleor)
- [Precios de Saleor Cloud](https://saleor.io/pricing)
- Esquema de la BD local de Saleor 3.23 (tablas `*translation`, `invoice_invoice`, `tax_*`)
