-- Consultas para entender el esquema de Saleor desde DBeaver.
-- Ejecutar con Ctrl+Enter (consulta bajo el cursor) en el editor SQL de DBeaver.

-- 1. Canales (≈ países o mercados): una moneda por canal
select id, slug, name, currency_code, default_country, is_active
from channel_channel;

-- 2. Precio de cada variante en cada canal (multipaís + precio por país)
select p.name as producto, v.sku, c.slug as canal,
       l.price_amount, l.discounted_price_amount, l.cost_price_amount, l.currency
from product_productvariantchannellisting l
join product_productvariant v on v.id = l.variant_id
join product_product p on p.id = v.product_id
join channel_channel c on c.id = l.channel_id
order by p.name, v.sku, c.slug
limit 50;

-- 3. Catálogo por país: en qué canales está publicado cada producto
select p.name, c.slug, pcl.is_published, pcl.published_at, pcl.visible_in_listings
from product_productchannellisting pcl
join product_product p on p.id = pcl.product_id
join channel_channel c on c.id = pcl.channel_id
order by p.name, c.slug;

-- 4. Productos que existen en un canal pero no en otro (catálogo distinto por país)
select p.name
from product_product p
where exists (select 1 from product_productchannellisting x join channel_channel c on c.id = x.channel_id
              where x.product_id = p.id and c.slug = 'default-channel')
  and not exists (select 1 from product_productchannellisting x join channel_channel c on c.id = x.channel_id
                  where x.product_id = p.id and c.slug = 'channel-pln');

-- 5. Promociones → reglas → canales (descuentos por país)
select pr.name as promocion, pr.type, r.name as regla, c.slug as canal,
       r.reward_value_type, r.reward_value, r.catalogue_predicate, r.order_predicate
from discount_promotion pr
join discount_promotionrule r on r.promotion_id = pr.id
left join discount_promotionrule_channels rc on rc.promotionrule_id = r.id
left join channel_channel c on c.id = rc.channel_id
order by pr.name, r.name;

-- 6. Descuento precalculado por variante y canal (lo rellena el worker de Celery)
select v.sku, c.slug, l.price_amount, d.discount_amount, l.discounted_price_amount
from product_variantchannellistingpromotionrule d
join product_productvariantchannellisting l on l.id = d.variant_channel_listing_id
join product_productvariant v on v.id = l.variant_id
join channel_channel c on c.id = l.channel_id
limit 50;

-- 7. Vouchers: valor e importe mínimo por canal
select v.name, v.type, vc.discount_value, vc.min_spent_amount, vc.currency, c.slug
from discount_voucher v
join discount_voucherchannellisting vc on vc.voucher_id = v.id
join channel_channel c on c.id = vc.channel_id;

-- 8. Checkouts y líneas: price_override es donde la app de precios Toteemi deja el precio rebajado
select ch.token, c.slug as canal, l.quantity, v.sku,
       l.undiscounted_unit_price_amount, l.price_override, l.price_override_reason, l.metadata
from checkout_checkoutline l
join checkout_checkout ch on ch.token = l.checkout_id
join channel_channel c on c.id = ch.channel_id
join product_productvariant v on v.id = l.variant_id
order by ch.created_at desc;

-- 9. Descuentos aplicados a líneas de checkout y su origen (promoción, voucher o manual)
select l.id as linea, d.type, d.value_type, d.value, d.amount_value, d.reason,
       d.promotion_rule_id, d.voucher_id
from discount_checkoutlinediscount d
join checkout_checkoutline l on l.id = d.line_id;

-- 10. Foreign keys de las tablas clave (útil para entender relaciones)
select conrelid::regclass as tabla, confrelid::regclass as referencia, conname
from pg_constraint
where contype = 'f'
  and split_part(conrelid::regclass::text, '_', 1) in ('channel', 'product', 'discount', 'checkout')
order by 1, 2;
