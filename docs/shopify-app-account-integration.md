# Shopify App Account Integration

Use this flow to integrate a new Shopify shop with a parcelLab account through
the parcelLab Shopify app.

## Flow

1. The merchant installs or opens the parcelLab Shopify app in Shopify Admin.
2. The embedded app hits `/integration/shopify/app/`.
3. Product API creates or refreshes a `ShopifyShopSettings` row for the Shopify
   shop domain.
4. The merchant submits the installation request/contact email in the embedded
   app.
5. Product API moves the shop settings row to `status=requested`.
6. A parcelLab admin assigns the shop settings row to the real parcelLab
   account.
7. The parcelLab admin runs **Install Shop**.

## Admin Steps

1. Open `/admin/integrations/shopifyshopsettings/`.
2. Search for the shop domain, for example `new-shop.myshopify.com`.
3. Open the `ShopifyShopSettings` row.
4. Set `account` to the real parcelLab customer account.
5. Save the row.
6. Reopen the row.
7. Click **Install Shop**.
8. Install or refresh Shopify webhooks and configure Order Status / Returns
   pages as needed.

Do not leave the row on account `1` (`GLOBAL`) or account `3` (`UNASSIGNED`).
The current admin blocks **Install Shop** for both.

## Result

**Install Shop** calls `ShopifyShopSettings.apply_integration()` and creates or
links these records:

```text
ShopifyShopSettings
  -> account = selected parcelLab account
  -> shop = config.Integration
  -> client = config.Client

config.Integration
  -> service = connect-shopify-oms
  -> config.domain = <shop>.myshopify.com
  -> authorization_grant = Shopify access token grant

config.Client
  -> key = <shop>.myshopify.com
```

The key rule is:

```text
Shopify app creates the shop settings and token.
parcelLab admin assigns the shop to the correct account.
Install Shop creates the actual OMS integration.
```
