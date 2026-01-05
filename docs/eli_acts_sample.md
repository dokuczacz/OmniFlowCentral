# ELI acts (inForce=1) - sample data (Azurite)

This file shows real examples of how the ELI dataset is stored in blob storage (Azurite) under:

`users/public/datasets/eli_acts/`

## 1) Run metadata (`runs/*.json`)

Example blob:

`users/public/datasets/eli_acts/runs/20260104T012816Z.json`

```json
{
  "run_id": "20260104T012816Z",
  "source": {
    "base_url": "https://api.sejm.gov.pl/eli",
    "endpoint": "/acts/search"
  },
  "query": {
    "inForce": "1",
    "limit": 500,
    "offset": 0
  },
  "checksum": {
    "pages_fetched": 118,
    "last_offset": 59000,
    "items_jsonl": {
      "enabled": true,
      "blob_name": "datasets/eli_acts/index/acts_inforce_1.jsonl",
      "count": 59000,
      "size_bytes": 72367441,
      "sha256": "3764f7c2819db49ac0969d3008e028b8761b7a1a7e80e00a117cb5c45deb2948"
    }
  }
}
```

## 2) Page payload (`pages/*.json`)

Example blob:

`users/public/datasets/eli_acts/pages/acts_offset_000000000.json`

Top-level fields:

- `offset`, `count`, `totalCount`
- `items`: array of `ActInfo`
- `searchQuery`: query echo/details (may be present)

Example header:

```json
{
  "offset": 0,
  "count": 500,
  "totalCount": 78692
}
```

## 3) Single record example (`ActInfo`)

Example item (from `items[0]`):

```json
{
  "ELI": "DU/2025/1900",
  "address": "WDU20250001900",
  "publisher": "DU",
  "year": 2025,
  "pos": 1900,
  "title": "Obwieszczenie Marszałka Sejmu Rzeczypospolitej Polskiej z dnia 19 grudnia 2025 r. w sprawie ogłoszenia jednolitego tekstu ustawy o finansowaniu społecznościowym dla przedsięwzięć gospodarczych i pomocy kredytobiorcom",
  "status": "obowiązujący",
  "inForce": "IN_FORCE",
  "changeDate": "2026-01-02T11:20:03",
  "promulgation": "2025-12-31",
  "announcementDate": "2025-12-19"
}
```

## 4) JSONL index (`index/*.jsonl`)

Example blob:

`users/public/datasets/eli_acts/index/acts_inforce_1.jsonl`

Each line is a full JSON object (one `ActInfo` per line). Example first line:

```json
{"ELI":"DU/2025/1900","address":"WDU20250001900","announcementDate":"2025-12-19","changeDate":"2026-01-02T11:20:03","displayAddress":"Dz.U. 2025 poz. 1900","pos":1900,"promulgation":"2025-12-31","publisher":"DU","status":"obowiązujący","textHTML":false,"textPDF":true,"title":"Obwieszczenie Marszałka Sejmu Rzeczypospolitej Polskiej z dnia 19 grudnia 2025 r. w sprawie ogłoszenia jednolitego tekstu ustawy o finansowaniu społecznościowym dla przedsięwzięć gospodarczych i pomocy kredytobiorcom","type":"Obwieszczenie","volume":0,"year":2025,"authorizedBody":[],"directives":[{"address":"32021L1269","date":"2021-04-21","title":"Dyrektywa delegowana Komisji (UE) 2021/1269 z dnia 21 kwietnia 2021 r. zmieniająca dyrektywę delegowaną (UE) 2017/593 w odniesieniu do uwzględniania czynników zrównoważonego rozwoju w zobowiązaniach w zakresie zarządzania produktami (Tekst mający znaczenie dla EOG)"}]}
```
