"""Repite las comprobaciones marcadas como "verificado en local" en informe/01-saleor.md.

Requisitos: el stack de saleor/ levantado y `populatedb --createsuperuser` ejecutado
(ver README.md en la raíz). Solo usa la librería estándar de Python.

    cd saleor && python3 verificacion/verificar.py

Crea una app temporal con permiso HANDLE_CHECKOUTS y la borra al terminar.
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

API = "http://localhost:8000/graphql/"
SALEOR_DIR = Path(__file__).resolve().parent.parent
ADMIN = ("admin@example.com", "admin")
CHANNEL = "default-channel"
ADDRESS = {
    "firstName": "Ana", "lastName": "Prueba", "streetAddress1": "Gran Via 1",
    "city": "Madrid", "postalCode": "28013", "country": "ES", "countryArea": "Madrid",
}

results = []


def check(section, claim, ok, detail=""):
    results.append(ok)
    print(f"{'✅' if ok else '❌'} [{section}] {claim}" + (f"\n     → {detail}" if detail else ""))


def gql(query, variables=None, token=None):
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    with urllib.request.urlopen(urllib.request.Request(API, body, headers)) as r:
        return json.load(r)


def sql(query):
    # psql dentro del contenedor db: así no hace falta tener psql ni drivers en el host
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "saleor", "-d", "saleor", "-At", "-c", query],
        cwd=SALEOR_DIR, capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def columns(table):
    return set(sql(f"select column_name from information_schema.columns where table_name = '{table}'"))


def type_fields(name, kind="inputFields"):
    t = gql('{ __type(name: "%s") { %s { name } } }' % (name, kind))["data"]["__type"]
    return {f["name"] for f in (t or {}).get(kind) or []}


def enum_values(name):
    return type_fields(name, "enumValues")


def check_schema():
    print("\n## Base de datos (1.4)")
    n = int(sql("select count(*) from information_schema.tables where table_schema = 'public'")[0])
    check("1.4", "Postgres con ~148 tablas", 140 <= n <= 160, f"{n} tablas")

    key_tables = [
        "channel_channel", "product_productchannellisting", "product_productvariantchannellisting",
        "product_variantchannellistingpromotionrule", "discount_promotionrule_channels",
        "discount_voucherchannellisting", "discount_checkoutlinediscount",
        "shipping_shippingmethodpostalcoderule", "tax_taxconfigurationpercountry", "giftcard_giftcard",
    ]
    existing = set(sql("select table_name from information_schema.tables where table_schema = 'public'"))
    missing = [t for t in key_tables if t not in existing]
    check("1.4", "Existen las tablas de canal, precio por canal, descuentos, CP e impuestos", not missing,
          f"faltan: {missing}" if missing else "")

    check("1.4", "Una moneda por canal (channel_channel.currency_code)", "currency_code" in columns("channel_channel"))
    check("1.4", "Precio por variante y canal (price_amount)",
          {"price_amount", "channel_id", "variant_id"} <= columns("product_productvariantchannellisting"))
    check("1.4", "La línea de checkout tiene price_override y price_override_reason",
          {"price_override", "price_override_reason"} <= columns("checkout_checkoutline"))
    check("1.4", "productvariantchannellisting NO tiene metadata (el máximo de teemis va en la variante)",
          "metadata" not in columns("product_productvariantchannellisting")
          and "metadata" in columns("product_productvariant"))
    check("1.4", "Configuración de impuestos por canal con 'precios con IVA incluido'",
          {"channel_id", "prices_entered_with_tax"} <= columns("tax_taxconfiguration"))

    print("\n## Idiomas, SEO y facturas (6.2–6.4)")
    translations = sql("select table_name from information_schema.tables where table_name like '%translation'")
    check("6.3", "Traducciones nativas de catálogo, descuentos, páginas y menús", len(translations) >= 14,
          f"{len(translations)} tablas *translation")
    check("6.3/6.4", "Slug y campos SEO traducibles por idioma",
          {"slug", "seo_title", "seo_description", "language_code"} <= columns("product_producttranslation"))
    check("6.4", "El producto tiene slug, campos SEO y referencia externa (para migrar desde WooCommerce)",
          {"slug", "seo_title", "seo_description", "external_reference"} <= columns("product_product"))
    check("6.2", "La factura de un pedido puede apuntar a un documento externo (Business Central)",
          "external_url" in columns("invoice_invoice"))
    csv = set(sql("select table_name from information_schema.tables where table_name like 'csv_%'"))
    check("1.7", "Solo hay exportación CSV (no tablas de importación)", csv == {"csv_exportfile", "csv_exportevent"},
          ", ".join(sorted(csv)))


def check_api_schema():
    print("\n## API GraphQL (1.3, 1.4, 1.6)")
    sync = enum_values("WebhookEventTypeSyncEnum")
    check("1.3", "No hay webhook síncrono de descuentos ni de validar el checkout",
          not any("DISCOUNT" in e or "VALIDATE" in e for e in sync), f"{len(sync)} eventos síncronos")
    used = {"ORDER_CREATED", "ORDER_FULLY_PAID", "ORDER_REFUNDED", "CHECKOUT_UPDATED"}
    missing = used - enum_values("WebhookEventTypeAsyncEnum")
    check("1.3", "Existen los webhooks asíncronos que usa el diseño", not missing,
          f"faltan: {missing}" if missing else ", ".join(sorted(used)))
    check("1.6", "CheckoutLineInput acepta price y priceOverrideReason",
          {"price", "priceOverrideReason"} <= type_fields("CheckoutLineInput"))
    predicates = type_fields("CataloguePredicateInput")
    check("1.4", "Las promociones no se pueden filtrar por cliente o grupo",
          predicates <= {"variantPredicate", "productPredicate", "categoryPredicate", "collectionPredicate", "AND", "OR"},
          ", ".join(sorted(predicates)))
    names = {t["name"].lower() for t in gql("{ __schema { types { name } } }")["data"]["__schema"]["types"]}
    check("1.4", "No hay listas de precios ni grupos de clientes en el esquema",
          not any(w in n for n in names for w in ("pricelist", "customergroup", "pricebook")))
    # Desde 3.23 hay tipos de cliente, pero solo para clasificar: ni promociones, ni vouchers, ni canales los usan
    uses = [t for t in ("PromotionRuleCreateInput", "VoucherInput", "ChannelCreateInput", "CataloguePredicateInput",
                        "CheckoutCreateInput") if "customerType" in type_fields(t)]
    check("1.4", "Los tipos de cliente (3.23) existen pero no afectan a precios, descuentos ni catálogo",
          "customertype" in names and not uses, f"lo usan: {uses}" if uses else "solo User.customerType y el filtro de clientes")


def first_variant(staff, shippable):
    edges = gql('{ productVariants(first: 100, channel: "%s") { edges { node { id name '
                'pricing { onSale price { gross { amount } } } product { name productType { isShippingRequired } } } } } }'
                % CHANNEL, token=staff)["data"]["productVariants"]["edges"]
    # Sin promoción: populatedb crea promociones al azar y se aplicarían encima del precio que fija la app
    return next(e["node"] for e in edges
                if e["node"]["product"]["productType"]["isShippingRequired"] == shippable
                and e["node"]["pricing"] and not e["node"]["pricing"]["onSale"])


def create_checkout(token, variant_id):
    data = gql("""mutation($v: ID!, $a: AddressInput!) {
      checkoutCreate(input: {channel: "%s", email: "ana@example.com", billingAddress: $a,
                             lines: [{variantId: $v, quantity: 1}]}) {
        checkout { id lines { id undiscountedUnitPrice { amount } } } errors { field message } } }""" % CHANNEL,
               {"v": variant_id, "a": ADDRESS}, token)["data"]["checkoutCreate"]
    if data["errors"]:
        raise RuntimeError(data["errors"])
    return data["checkout"]


def override_price(token, checkout, price, reason):
    return gql("""mutation($id: ID!, $l: ID!, $p: PositiveDecimal!, $r: String) {
      checkoutLinesUpdate(id: $id, lines: [{lineId: $l, price: $p, priceOverrideReason: $r}]) {
        checkout { chargeStatus totalPrice { net { amount } gross { amount } } } errors { message } } }""",
               {"id": checkout["id"], "l": checkout["lines"][0]["id"], "p": price, "r": reason}, token)


def staff_token():
    """Comprueba que el stack responde y que hay datos de ejemplo; devuelve el token del admin."""
    try:
        token = gql('mutation { tokenCreate(email: "%s", password: "%s") { token } }' % ADMIN)["data"]["tokenCreate"]["token"]
    except OSError:
        sys.exit("No se puede conectar a http://localhost:8000. ¿Está levantado el stack? (cd saleor && docker compose up -d)")
    if not token:
        sys.exit("No existe el usuario admin@example.com: faltan los datos de ejemplo.\n"
                 "  cd saleor && docker compose exec api python3 manage.py populatedb --createsuperuser")
    return token


def check_teemis_poc(staff):
    print("\n## Prueba de concepto de teemis (1.6)")
    created = gql('mutation { appCreate(input: {name: "verificacion-teemis", permissions: [HANDLE_CHECKOUTS]}) '
                  '{ authToken app { id } } }', token=staff)["data"]["appCreate"]
    app_token, app_id = created["authToken"], created["app"]["id"]
    try:
        # 1. La app rebaja el precio de una línea (5 unidades de moneda = teemis canjeados)
        variant = first_variant(staff, shippable=True)
        checkout = create_checkout(app_token, variant["id"])
        base = checkout["lines"][0]["undiscountedUnitPrice"]["amount"]
        r = override_price(app_token, checkout, round(base - 5, 2), "teemis: 5 canjeados")
        # Se compara el neto: con dirección en España Saleor suma el IVA al bruto
        # (el canal de ejemplo tiene los precios sin impuestos)
        total = r["data"]["checkoutLinesUpdate"]["checkout"]["totalPrice"]
        net, gross = total["net"]["amount"], total["gross"]["amount"]
        check("1.6", "Una app con HANDLE_CHECKOUTS sobrescribe el precio de la línea",
              abs(net - (base - 5)) < 0.01, f"{base} → {net} sin IVA ({gross} con IVA)")

        # 2. Un usuario de staff no puede hacerlo
        r = override_price(staff, checkout, 1, None)
        check("1.6", "Un token de staff (no app) no puede cambiar el precio", bool(r.get("errors")),
              (r.get("errors") or [{}])[0].get("message", ""))

        # 3. Producto pagado al 100 % con teemis: total 0 y pedido sin pago
        variant = first_variant(staff, shippable=False)
        checkout = create_checkout(app_token, variant["id"])
        r = override_price(app_token, checkout, 0, "pagado 100% con teemis")["data"]["checkoutLinesUpdate"]["checkout"]
        check("1.6", "Con precio 0 el checkout queda pagado (chargeStatus FULL)",
              r["chargeStatus"] == "FULL" and r["totalPrice"]["gross"]["amount"] == 0, r["chargeStatus"])
        order = gql('mutation($id: ID!) { checkoutComplete(id: $id) { order { number chargeStatus } '
                    'errors { message } } }', {"id": checkout["id"]}, app_token)["data"]["checkoutComplete"]
        check("1.6", "checkoutComplete crea el pedido sin pasar por el pago", bool(order["order"]),
              f"pedido nº {order['order']['number']}" if order["order"] else str(order["errors"]))
    finally:
        gql('mutation($id: ID!) { appDelete(id: $id) { errors { message } } }', {"id": app_id}, staff)


def main():
    staff = staff_token()
    check_schema()
    check_api_schema()
    check_teemis_poc(staff)
    ok = sum(results)
    print(f"\n{ok}/{len(results)} comprobaciones correctas")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
