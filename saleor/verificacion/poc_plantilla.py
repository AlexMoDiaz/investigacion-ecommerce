"""PoC mínima de la plantilla del spike (Notion): dos países, un producto de club y envío gratis Premium.

Requisitos: los mismos que verificar.py (stack levantado y populatedb). Solo usa la librería estándar.

    cd saleor && python3 verificacion/poc_plantilla.py

Deja creados los canales "poc-es" y "poc-fr", el tipo de cliente del club y tres clientes de prueba,
para poder verlos en el panel y en DBeaver. Si se vuelve a ejecutar, los borra y los crea de nuevo.
Levanta un servidor de webhooks en el puerto 8765 del Mac mientras dura la prueba y borra la app al terminar.
"""

import http.server
import json
import sys
import threading

from verificar import check, gql, results, staff_token

PUERTO_WEBHOOKS = 8765
CLUB = "club-ciclista-x"
PAISES = {
    # canal: país, IVA, precio de la camiseta, precio del envío, idioma
    "poc-es": {"pais": "ES", "iva": 21, "precio": 24.95, "envio": 4.90, "idioma": "ES",
               "direccion": {"city": "Madrid", "postalCode": "28013", "countryArea": "Madrid"}},
    "poc-fr": {"pais": "FR", "iva": 20, "precio": 26.95, "envio": 5.90, "idioma": "FR",
               "direccion": {"city": "Paris", "postalCode": "75001"}},
}
CLIENTES = {"socio": "socio@poc.example.com", "no-socio": "otro@poc.example.com", "premium": "premium@poc.example.com"}


def ok(data, field):
    """Devuelve el resultado de una mutación y falla si trae errores."""
    result = data["data"][field] if "data" in data else None
    if not result or result.get("errors"):
        raise RuntimeError(f"{field}: {data}")
    return result


def node_by_name(query, name, token):
    return next(e["node"] for e in gql(query, token=token)["data"][query.split("(")[0].strip("{ ")]["edges"]
                if e["node"]["name"] == name)


# --- App de prueba: responde a los dos webhooks síncronos de envíos ---

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        checkout = payload["checkout"]
        user = checkout.get("user") or {}
        if self.headers.get("Saleor-Event") == "checkout_filter_shipping_methods":
            # Si el checkout lleva un producto de club y el cliente no es socio, se quitan todos los envíos
            clubs = {m["value"] for line in checkout["lines"] for m in line["variant"]["product"]["metadata"]
                     if m["key"] == "club"}
            socio_de = (user.get("customerType") or {}).get("slug")
            bloquear = clubs and socio_de not in clubs
            body = {"excluded_methods": [{"id": m["id"], "reason": "Producto exclusivo para socios del club"}
                                         for m in payload["shippingMethods"]] if bloquear else []}
        else:
            # Envío gratis solo para Premium: el backend Toteemi marcaría premium=true en el cliente
            premium = any(m["key"] == "premium" and m["value"] == "true" for m in user.get("metadata", []))
            body = [{"id": "premium-gratis", "name": "Envío gratis Premium", "amount": 0,
                     "currency": checkout["channel"]["currencyCode"], "maximum_delivery_days": 5}] if premium else []
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


SUBSCRIPTION = """subscription {
  event {
    ... on CheckoutFilterShippingMethods {
      checkout { user { customerType { slug } } lines { variant { product { metadata { key value } } } } }
      shippingMethods { id }
    }
    ... on ShippingListMethodsForCheckout {
      checkout { channel { currencyCode } user { metadata { key value } } }
    }
  }
}"""


# --- Preparación ---

def limpiar(staff):
    for slug in [*PAISES, "poc-club-inactivo"]:
        channel = gql('{ channel(slug: "%s") { id } }' % slug, token=staff)["data"]["channel"]
        if channel:
            gql("mutation($id: ID!) { channelDelete(id: $id) { errors { message } } }", {"id": channel["id"]}, staff)
    for email in CLIENTES.values():
        user = gql('{ user(email: "%s") { id } }' % email, token=staff)["data"]["user"]
        if user:
            gql("mutation($id: ID!) { customerDelete(id: $id) { errors { message } } }", {"id": user["id"]}, staff)
    types = gql("{ customerTypes(first: 50) { edges { node { id slug } } } }", token=staff)["data"]["customerTypes"]
    for edge in types["edges"]:
        if edge["node"]["slug"] == CLUB:
            gql("mutation($id: ID!) { customerTypeDelete(id: $id) { errors { message } } }", {"id": edge["node"]["id"]}, staff)


def crear_paises(staff):
    warehouse = node_by_name("{ warehouses(first: 50) { edges { node { id name } } } }", "Europe", staff)["id"]
    zone = node_by_name("{ shippingZones(first: 50) { edges { node { id name shippingMethods { id name } } } } }",
                        "Europe", staff)
    ups = next(m["id"] for m in zone["shippingMethods"] if m["name"] == "UPS")
    channels = {}
    for slug, p in PAISES.items():
        channel = ok(gql("""mutation($i: ChannelCreateInput!) { channelCreate(input: $i) { channel { id } errors { message } } }""",
                         # por API el canal nace inactivo si no se indica isActive
                         {"i": {"name": f"PoC {p['pais']}", "slug": slug, "currencyCode": "EUR", "defaultCountry": p["pais"],
                                "isActive": True,
                                "addWarehouses": [warehouse], "addShippingZones": [zone["id"]]}}, staff),
                     "channelCreate")["channel"]["id"]
        channels[slug] = channel
        # IVA: precios con IVA incluido en el canal y el tipo general del país (los tipos son por país, no por canal)
        tax_config = next(e["node"]["id"] for e in gql(
            "{ taxConfigurations(first: 50) { edges { node { id channel { slug } } } } }", token=staff
        )["data"]["taxConfigurations"]["edges"] if e["node"]["channel"]["slug"] == slug)
        ok(gql("""mutation($id: ID!) { taxConfigurationUpdate(id: $id, input: {chargeTaxes: true, pricesEnteredWithTax: true,
                  displayGrossPrices: true, taxCalculationStrategy: FLAT_RATES}) { errors { message } } }""",
               {"id": tax_config}, staff), "taxConfigurationUpdate")
        ok(gql("""mutation($c: CountryCode!, $r: Float!) { taxCountryConfigurationUpdate(countryCode: $c,
                  updateTaxClassRates: [{rate: $r}]) { errors { message } } }""", {"c": p["pais"], "r": p["iva"]}, staff),
           "taxCountryConfigurationUpdate")
        ok(gql("""mutation($id: ID!, $c: ID!, $p: PositiveDecimal!) { shippingMethodChannelListingUpdate(id: $id,
                  input: {addChannels: [{channelId: $c, price: $p}]}) { errors { message } } }""",
               {"id": ups, "c": channel, "p": p["envio"]}, staff), "shippingMethodChannelListingUpdate")
    return channels


def publicar(staff, product, channels, precios):
    ok(gql("""mutation($id: ID!, $u: [ProductChannelListingAddInput!]) { productChannelListingUpdate(id: $id,
              input: {updateChannels: $u}) { errors { message } } }""",
           {"id": product["id"], "u": [{"channelId": c, "isPublished": True, "visibleInListings": True,
                                        "isAvailableForPurchase": True} for c in channels]}, staff),
       "productChannelListingUpdate")
    for variant in product["variants"]:
        ok(gql("""mutation($id: ID!, $i: [ProductVariantChannelListingAddInput!]!) {
                  productVariantChannelListingUpdate(id: $id, input: $i) { errors { message } } }""",
               {"id": variant["id"], "i": [{"channelId": c, "price": precios[c]} for c in channels]}, staff),
           "productVariantChannelListingUpdate")


def producto(staff, name):
    return gql('{ products(first: 1, where: {name: {eq: "%s"}}) { edges { node { id slug variants { id } } } } }' % name,
               token=staff)["data"]["products"]["edges"][0]["node"]


def crear_checkout(token, slug, variant_id, customer_id=None, staff=None):
    p = PAISES[slug]
    address = {"firstName": "Ana", "lastName": "Prueba", "streetAddress1": "Calle 1", "country": p["pais"], **p["direccion"]}
    checkout = ok(gql("""mutation($c: String!, $v: ID!, $a: AddressInput!) { checkoutCreate(input: {channel: $c,
                         email: "poc@example.com", shippingAddress: $a, billingAddress: $a, lines: [{variantId: $v, quantity: 1}]})
                         { checkout { id } errors { field message } } }""",
                      {"c": slug, "v": variant_id, "a": address}, token), "checkoutCreate")["checkout"]
    if customer_id:
        # Lo haría el BFF con el usuario ya identificado (cuenta Toteemi)
        ok(gql("""mutation($id: ID!, $u: ID!) { checkoutCustomerAttach(id: $id, customerId: $u) { errors { message } } }""",
               {"id": checkout["id"], "u": customer_id}, token), "checkoutCustomerAttach")
    return gql("""query($id: ID!) { checkout(id: $id) { id subtotalPrice { gross { amount } tax { amount } }
                  shippingMethods { id name active message price { amount } } } }""", {"id": checkout["id"]}, token
               )["data"]["checkout"]


# --- Comprobaciones ---

def comprobar_paises(staff, app_token):
    print("\n## Dos países con IVA, precio, envío e idioma distintos")
    channels = crear_paises(staff)
    tee = producto(staff, "Monospace Tee")
    publicar(staff, tee, channels.values(), {channels[s]: p["precio"] for s, p in PAISES.items()})
    ok(gql("""mutation($id: ID!) { productTranslate(id: $id, languageCode: FR, input: {name: "T-shirt Monospace"})
              { errors { message } } }""", {"id": tee["id"]}, staff), "productTranslate")

    for slug, p in PAISES.items():
        checkout = crear_checkout(app_token, slug, tee["variants"][0]["id"])
        gross, tax = checkout["subtotalPrice"]["gross"]["amount"], checkout["subtotalPrice"]["tax"]["amount"]
        expected_tax = round(p["precio"] - p["precio"] / (1 + p["iva"] / 100), 2)
        check("7", f"{p['pais']}: precio propio con IVA del {p['iva']} % incluido",
              gross == p["precio"] and abs(tax - expected_tax) < 0.01, f"{gross} € de los que {tax} € son IVA")
        ups = next((m for m in checkout["shippingMethods"] if m["name"] == "UPS"), None)
        check("7", f"{p['pais']}: envío con precio propio del país", bool(ups) and ups["price"]["amount"] == p["envio"],
              f"UPS {ups['price']['amount'] if ups else '—'} €")
        name = gql("""{ product(slug: "%s", channel: "%s") { name translation(languageCode: %s) { name } } }"""
                   % (tee["slug"], slug, p["idioma"]))["data"]["product"]
        shown = (name["translation"] or {}).get("name") or name["name"]
        check("7", f"{p['pais']}: el catálogo se pide en el idioma del país", shown == ("T-shirt Monospace" if p["pais"] == "FR" else "Monospace Tee"),
              shown)
    return channels


def comprobar_clubs(staff, app_token, channels):
    print("\n## Producto solo para los socios de un club")
    club = ok(gql("""mutation { customerTypeCreate(input: {name: "Club Ciclista X", slug: "%s"}) { customerType { id }
                     errors { message } } }""" % CLUB, token=staff), "customerTypeCreate")["customerType"]["id"]
    users = {}
    for key, email in CLIENTES.items():
        extra = {"customerType": club} if key == "socio" else {}
        users[key] = ok(gql("""mutation($i: UserCreateInput!) { customerCreate(input: $i) { user { id } errors { message } } }""",
                            {"i": {"email": email, "firstName": key, **extra}}, staff), "customerCreate")["user"]["id"]
    ok(gql("""mutation($id: ID!) { updateMetadata(id: $id, input: [{key: "premium", value: "true"}]) { errors { message } } }""",
           {"id": users["premium"]}, staff), "updateMetadata")
    slug = gql('{ user(id: "%s") { customerType { slug } } }' % users["socio"], token=staff)["data"]["user"]["customerType"]["slug"]
    check("7", "El club del cliente se puede guardar en Saleor (tipo de cliente, nuevo en 3.23)", slug == CLUB, slug)

    hoodie = producto(staff, "Dash Force")
    publicar(staff, hoodie, [channels["poc-es"]], {channels["poc-es"]: 39.95})
    ok(gql("""mutation($id: ID!) { updateMetadata(id: $id, input: [{key: "club", value: "%s"}]) { errors { message } } }""" % CLUB,
           {"id": hoodie["id"]}, staff), "updateMetadata")
    found = gql("""{ products(first: 10, channel: "poc-es", where: {metadata: [{key: "club", value: "%s"}]})
                   { edges { node { name } } } }""" % CLUB)["data"]["products"]["edges"]
    check("7", "La tienda puede filtrar el catálogo por club (metadata), pero la API pública también lo ve",
          [e["node"]["name"] for e in found] == ["Dash Force"], "consulta anónima: " + ", ".join(e["node"]["name"] for e in found))

    # ¿Se puede esconder de verdad? Despublicado o en un canal inactivo, ni siquiera nuestra app puede venderlo
    ok(gql("""mutation($id: ID!, $c: ID!) { productChannelListingUpdate(id: $id, input: {updateChannels: [{channelId: $c,
              isPublished: false}]}) { errors { message } } }""", {"id": hoodie["id"], "c": channels["poc-es"]}, staff),
       "productChannelListingUpdate")
    r = gql("""mutation($v: ID!) { checkoutCreate(input: {channel: "poc-es", email: "a@example.com", lines: [{variantId: $v,
               quantity: 1}]}) { errors { code } } }""", {"v": hoodie["variants"][0]["id"]}, app_token)["data"]["checkoutCreate"]
    codes = [e["code"] for e in r["errors"]]
    check("7", "Un producto despublicado no se puede comprar ni desde nuestra app", codes == ["PRODUCT_NOT_PUBLISHED"], ", ".join(codes))
    publicar(staff, hoodie, [channels["poc-es"]], {channels["poc-es"]: 39.95})
    inactive = ok(gql("""mutation { channelCreate(input: {name: "PoC club inactivo", slug: "poc-club-inactivo", currencyCode: "EUR",
                         defaultCountry: ES, isActive: false}) { channel { id } errors { message } } }""", token=staff),
                  "channelCreate")["channel"]["id"]
    r = gql("""mutation { checkoutCreate(input: {channel: "poc-club-inactivo", email: "a@example.com", lines: []})
               { errors { code } } }""", token=app_token)["data"]["checkoutCreate"]
    gql("mutation($id: ID!) { channelDelete(id: $id) { errors { message } } }", {"id": inactive}, staff)
    codes = [e["code"] for e in r["errors"]]
    check("7", "Un canal inactivo (\"canal oculto por club\") tampoco sirve: bloquea también a la app",
          codes == ["CHANNEL_INACTIVE"], ", ".join(codes))

    # Lo que sí bloquea la compra: el webhook síncrono quita los envíos si el cliente no es del club
    for key, label in [("no-socio", "no socio"), ("socio", "socio")]:
        checkout = crear_checkout(app_token, "poc-es", hoodie["variants"][0]["id"], users[key])
        active = [m["name"] for m in checkout["shippingMethods"] if m["active"]]
        r = gql("""mutation($id: ID!, $m: ID!) { checkoutDeliveryMethodUpdate(id: $id, deliveryMethodId: $m)
                   { errors { code } } }""", {"id": checkout["id"], "m": checkout["shippingMethods"][0]["id"]}, app_token)
        codes = [e["code"] for e in r["data"]["checkoutDeliveryMethodUpdate"]["errors"]]
        if key == "socio":
            check("7", "Socio del club: tiene envíos y puede elegir uno", bool(active) and not codes, ", ".join(active))
        else:
            reason = checkout["shippingMethods"][0]["message"]
            check("7", "No socio: la app le quita todos los envíos y no puede cerrar la compra", not active and bool(codes),
                  f"{reason} → {', '.join(codes)}")
    return users


def comprobar_envio_premium(staff, app_token, users):
    print("\n## Envío gratis solo para Premium (cupón por rol)")
    tee = producto(staff, "Monospace Tee")
    for key, label in [("premium", "Premium"), ("no-socio", "no Premium")]:
        checkout = crear_checkout(app_token, "poc-es", tee["variants"][0]["id"], users[key])
        free = [m for m in checkout["shippingMethods"] if m["name"] == "Envío gratis Premium"]
        if key == "premium":
            check("3", "Premium: la app añade un envío gratis", bool(free) and free[0]["price"]["amount"] == 0,
                  ", ".join(f"{m['name']} {m['price']['amount']} €" for m in checkout["shippingMethods"]))
        else:
            check("3", "No Premium: no ve el envío gratis", not free,
                  ", ".join(m["name"] for m in checkout["shippingMethods"]))


def main():
    staff = staff_token()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PUERTO_WEBHOOKS), WebhookHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    limpiar(staff)
    app = ok(gql("""mutation { appCreate(input: {name: "poc-plantilla",
                    permissions: [HANDLE_CHECKOUTS, IMPERSONATE_USER, MANAGE_USERS, MANAGE_CHECKOUTS, MANAGE_SHIPPING]}) { authToken app { id } errors { message } } }""",
                 token=staff), "appCreate")
    app_token, app_id = app["authToken"], app["app"]["id"]
    try:
        channels = comprobar_paises(staff, app_token)
        ok(gql("""mutation($i: WebhookCreateInput!) { webhookCreate(input: $i) { errors { message } } }""",
               {"i": {"app": app_id, "name": "envios", "targetUrl": f"http://host.docker.internal:{PUERTO_WEBHOOKS}/",
                      "syncEvents": ["CHECKOUT_FILTER_SHIPPING_METHODS", "SHIPPING_LIST_METHODS_FOR_CHECKOUT"],
                      "query": SUBSCRIPTION}}, staff), "webhookCreate")
        users = comprobar_clubs(staff, app_token, channels)
        comprobar_envio_premium(staff, app_token, users)
    finally:
        gql("mutation($id: ID!) { appDelete(id: $id) { errors { message } } }", {"id": app_id}, staff)
        server.shutdown()
    print(f"\n{sum(results)}/{len(results)} comprobaciones correctas")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
