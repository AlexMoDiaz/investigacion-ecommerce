# Investigación de plataformas e-commerce multipaís (ACID TANGO)

Comparativa de **Saleor**, **Medusa** y **Shopify Plus** para sustituir la tienda actual de Toteemi (WordPress + WooCommerce en `toteemi.com`).

## Contenido
| Ruta | Qué es |
|---|---|
| **`informe/spike-saleor.md`** | **Entregable: la plantilla del spike de Notion rellena para Saleor** (se pega tal cual en Notion) |
| `informe/plantilla-notion.md` | La plantilla vacía, común a Saleor, Medusa y Shopify Plus |
| `informe/00-situacion-actual.md` | Contexto, requisitos y definición de los teemis |
| `informe/01-saleor.md` | Análisis completo de Saleor |
| `informe/04-comparativa.md` | Tabla comparativa (Medusa y Shopify Plus pendientes) |
| `informe/05-recomendacion.md` | Conclusión (parcial, solo Saleor) |
| `informe/06-transversales.md` | IVA y facturación, idiomas, SEO, migración desde WooCommerce y coste |
| `informe/informe-final.md` | Todo lo anterior junto, listo para pegar en Notion (se genera, ver abajo) |
| `saleor/` | Saleor en local con Docker Compose y Dev Container, más la guía de DBeaver |
| `saleor/verificacion/verificar.py` | Repite todo lo marcado como "verificado en local" en el informe |
| `saleor/verificacion/poc_plantilla.py` | PoC mínima de la plantilla: ES y FR, producto de club y envío gratis Premium |
| `saleor/verificacion/panel/` | Prueba automatizada del panel (abrir un país, precios, promoción) |

Los ficheros `00`–`06` son el análisis de partida: la plantilla los resume y los cita como fuente.

## Regenerar el informe final
```bash
for f in informe/0*.md; do cat "$f"; printf '\n---\n\n'; done > informe/informe-final.md
```
