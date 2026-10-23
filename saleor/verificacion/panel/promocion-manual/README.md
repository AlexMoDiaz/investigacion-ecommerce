# Paso 3 (manual): crear una promoción −20 % para un solo país

Este paso se hizo a mano en el Dashboard 3.23 y no está automatizado. Los desplegables de la condición no tienen etiqueta y la prueba con Playwright se quedaba colgada. `prueba-panel.mjs` crea la misma promoción por API para poder medir el paso 4, el recálculo del precio rebajado.

| # | Qué se hace | Captura |
|---|---|---|
| 1 | **Discounts → Promotions → Create**. Tipo *Catalog* y nombre de la promoción. | `1-crear-descuento.png` |
| 2 | **Add rule**: nombre, **canal** (uno solo por regla) y valor. ⚠️ Por defecto el valor está en **EUR**, no en %. Hay que pulsar `%` antes de escribir 20. | `2-regla-canal-y-valor.png` |
| 3 | **Add condition**: tres desplegables sin etiqueta (tipo → *Products*, operador → *is*, valor → buscar el producto). | `3-condicion-producto.png` |
| 4 | **Save** en la regla y **Save** en la página. La promoción aparece *Active*, pero el canal sale *(Inactive)* hasta que se publica. | `4-promocion-guardada.png` |

Lo que se observó:
- Para hacer la campaña en 6 países hay que repetir el paso 2 seis veces (una regla por canal).
- El precio rebajado del catálogo no se actualizó hasta reiniciar `beat` (ver informe 1.7 y el paso 4 de la prueba).
