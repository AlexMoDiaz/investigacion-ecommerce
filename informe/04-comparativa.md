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
