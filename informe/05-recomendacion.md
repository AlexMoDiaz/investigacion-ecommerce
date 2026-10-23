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
