# Panduan Komunikasi MQTT Order ZenithKitchen

Tanggal: 2026-06-25

Dokumen ini menjelaskan komunikasi MQTT untuk order kitchen, pembacaan status robot,
dan bagaimana status tersebut masuk lagi ke dashboard cashier/customer.

## Ringkasan Arsitektur

ZenithKitchen memakai dua jalur realtime:

1. MQTT dipakai antara aplikasi Django dan device robot kitchen.
2. WebSocket dipakai antara aplikasi Django dan browser cashier/customer.

Alur utamanya:

```text
Customer/Kiosk buat order
  -> Orders + OrdersTime(status=pending)
  -> KitchenOrderAssignment(status=waiting)
  -> dispatch ke chef/robot kosong
  -> jika chef mode robot: publish MQTT order command
  -> robot publish MQTT status feedback
  -> aplikasi update KitchenOrderAssignment
  -> jika done: stok dikonsumsi dan order masuk Ready for Payment
  -> cashier menyelesaikan pembayaran menjadi completed
```

File utama yang menjadi referensi:

| Area | File |
| --- | --- |
| MQTT client, publish, subscribe | `zenithkitchen/integrations/mqtt/client.py` |
| Dispatch order dan feedback robot | `zenithkitchen/services/kitchen_service.py` |
| Pembuatan order dan status pembayaran | `zenithkitchen/services/order_service.py` |
| Model order, chef, assignment | `zenithkitchen/hmi/models.py` |
| WebSocket cashier/customer | `zenithkitchen/integrations/websocket/wschannel.py` |
| URL HTTP dashboard/order | `zenithkitchen/hmi/urls.py` |

## Konfigurasi Environment

Konfigurasi MQTT dibaca dari `projects/settings.py`.

| Variable | Fungsi | Default |
| --- | --- | --- |
| `MQTT_ENABLED` | Mengaktifkan publish dan listener MQTT | `False` |
| `MQTT_HOST` | Host/IP broker MQTT | `localhost` |
| `MQTT_PORT` | Port broker MQTT | `1883` |
| `MQTT_USERNAME` | Username broker, opsional | kosong |
| `MQTT_PASSWORD` | Password broker, opsional | kosong |
| `MQTT_CLIENT_ID` | Prefix client id MQTT | `zenithkitchen-app` |
| `MQTT_TOPIC_ROOT` | Prefix topic MQTT | kosong |

Contoh `.env`:

```env
MQTT_ENABLED=True
MQTT_HOST=192.168.1.20
MQTT_PORT=1883
MQTT_USERNAME=zkitchen
MQTT_PASSWORD=secret
MQTT_CLIENT_ID=zenithkitchen-app
MQTT_TOPIC_ROOT=zenithkitchen
```

Catatan topic root:

- Jika `MQTT_TOPIC_ROOT=zenithkitchen`, topic menjadi `zenithkitchen/order/cmd/raspi1`.
- Jika `MQTT_TOPIC_ROOT` kosong, implementasi sekarang membuat topic seperti `/order/cmd/raspi1`.
- Untuk deployment multi-perusahaan dalam broker yang sama, root topic perlu dibedakan per deployment/per tenant, karena topic saat ini tidak membawa `company_id`.

## Penamaan Device Robot

Device robot berasal dari model `KitchenChef`.

| Field | Nilai |
| --- | --- |
| `mode` | `robot` agar MQTT aktif untuk chef tersebut |
| `device_kind` | `raspi` atau `weintek` |
| `device_number` | angka mulai dari `1` |
| `payload_format` | `json` atau `raw` |

Nama device dibentuk otomatis:

```text
device = device_kind + device_number
```

Contoh:

| device_kind | device_number | device |
| --- | ---: | --- |
| `raspi` | `1` | `raspi1` |
| `raspi` | `2` | `raspi2` |
| `weintek` | `1` | `weintek1` |

Chef dengan `mode=person` tidak menerima MQTT command.

## Topic MQTT

Fungsi topic:

```python
f"{MQTT_TOPIC_ROOT}/{domain}/{arah}/{device}"
```

Topic yang dipakai:

| Arah | Topic | Dipakai oleh |
| --- | --- | --- |
| App -> Robot | `{root}/order/cmd/{device}` | Aplikasi publish order/standby command |
| Robot -> App | `{root}/order/status/{device}` | Robot publish feedback status |
| Listener App | `{root}/order/status/#` | Aplikasi subscribe semua status device |

Dengan `MQTT_TOPIC_ROOT=zenithkitchen`:

```text
zenithkitchen/order/cmd/raspi1
zenithkitchen/order/status/raspi1
zenithkitchen/order/status/#
```

Publish memakai QoS 1 dan retain `False`.

## Payload Order Command JSON

Jika `payload_format=json`, aplikasi mengirim payload seperti ini:

```json
{
  "order_id": "ORD-0007",
  "items": [
    {
      "menu": "nasi_goreng",
      "option": 0,
      "qty": 2
    },
    {
      "menu": "es_teh",
      "option": 1,
      "qty": 1
    }
  ]
}
```

Aturan field:

| Field | Tipe | Keterangan |
| --- | --- | --- |
| `order_id` | string | Format `ORD-0007`, angka berasal dari `Orders.id` |
| `items[].menu` | string | Nama menu dinormalisasi: lowercase, spasi/simbol menjadi `_` |
| `items[].option` | number | Opsi menu, default `0` |
| `items[].qty` | number | Jumlah item |

Contoh menu token:

| Nama menu | Token |
| --- | --- |
| `Nasi Goreng` | `nasi_goreng` |
| `Es Teh Manis` | `es_teh_manis` |
| `Chicken & Rice` | `chicken_rice` |

## Payload Order Command RAW

Jika `payload_format=raw`, aplikasi mengirim string:

```text
ORD-0007|12,0,2|9,1,1
```

Format:

```text
ORDER_CODE|menu_id,option,quantity|menu_id,option,quantity
```

Contoh arti payload:

| Bagian | Arti |
| --- | --- |
| `ORD-0007` | Order id database `7` |
| `12,0,2` | Menu id `12`, option `0`, qty `2` |
| `9,1,1` | Menu id `9`, option `1`, qty `1` |

## Payload Standby Command

Saat robot selesai dan tidak punya assignment aktif lain, aplikasi mengirim standby.

JSON:

```json
{
  "status": "stand by"
}
```

RAW:

```text
STANDBY|3
```

## Payload Feedback Robot JSON

Robot mengirim feedback ke:

```text
{root}/order/status/{device}
```

Format yang direkomendasikan:

```json
{
  "order_id": "ORD-0007",
  "status": "processing"
}
```

Status yang diproses aplikasi:

| status | Efek di aplikasi |
| --- | --- |
| `received` | `KitchenOrderAssignment.status` menjadi `received` |
| `processing` | `KitchenOrderAssignment.status` menjadi `processing`, `started_at` diisi |
| `done` | Assignment selesai, order masuk Ready for Payment, stok dikonsumsi |
| `error` | Assignment menjadi `error`, `error_message` berisi payload feedback |

Contoh lengkap:

```json
{"order_id":"ORD-0007","status":"received"}
{"order_id":"ORD-0007","status":"processing"}
{"order_id":"ORD-0007","status":"done"}
{"order_id":"ORD-0007","status":"error"}
```

Catatan:

- `order_id` sebaiknya selalu dikirim.
- Jika `order_id` tidak ada, aplikasi mencoba mencari assignment aktif berdasarkan device.
- Status `standby`, `stand_by`, dan `stand by` bisa diparse sebagai nama status, tetapi handler saat ini tidak mengubah state aplikasi untuk status tersebut.

## Payload Feedback Robot RAW

Format RAW feedback:

```text
ORD-0007|1
```

Format:

```text
ORDER_CODE|STATUS_CODE
```

Mapping kode status:

| Kode | Status | Efek |
| ---: | --- | --- |
| `0` | `received` | Robot menerima order |
| `1` | `processing` | Robot mulai memproses |
| `2` | `done` | Robot selesai, order siap bayar |
| `3` | `stand by` | Terbaca, tetapi belum mengubah state assignment |
| `9` | `error` | Assignment masuk error |

Contoh:

```text
ORD-0007|0
ORD-0007|1
ORD-0007|2
ORD-0007|9
```

## Lifecycle Status

Ada dua status yang berbeda dan perlu dibedakan:

1. Status order bisnis: ada di `OrdersTime`.
2. Status kitchen/robot: ada di `KitchenOrderAssignment`.

Status order bisnis:

| Status | Arti |
| --- | --- |
| `pending` | Order masih berjalan atau menunggu pembayaran |
| `completed` | Pembayaran selesai |
| `cancelled` | Order dibatalkan |

Status kitchen/robot:

| Status | Arti |
| --- | --- |
| `waiting` | Order menunggu chef/robot kosong |
| `assigned` | Order sudah diberikan ke chef/robot |
| `received` | Robot mengkonfirmasi order diterima |
| `processing` | Robot sedang memasak/proses |
| `done` | Kitchen selesai |
| `cancelled` | Assignment dibatalkan |
| `error` | Robot/device mengirim error |

`ready_for_payment` adalah flag penting di model `Orders`.

| ready_for_payment | Arti UI |
| --- | --- |
| `False` | Order masih di antrean pending/kitchen |
| `True` | Order masuk area payment dan bisa diselesaikan cashier |

## Alur Detail Order ke Robot

1. Customer order dibuat lewat HTTP `POST /ZenithKitchen/create-order/` atau WebSocket `/ZenithKitchen/ws/customer/order/`.
2. Service membuat `Orders`, `OrdersList`, dan `OrdersTime(status=pending)`.
3. `kitchen_service.enqueue_order(order)` membuat `KitchenOrderAssignment(status=waiting)`.
4. `dispatch_waiting_orders(company)` mencari chef/robot aktif yang kosong.
5. Jika chef kosong ditemukan, assignment menjadi `assigned`.
6. Jika chef tersebut `mode=robot`, aplikasi publish MQTT ke `{root}/order/cmd/{device}`.
7. Payload yang dikirim disimpan ke `KitchenOrderAssignment.last_payload`.
8. Jika publish gagal atau MQTT disabled, `error_message` berisi `MQTT publish gagal atau MQTT disabled.`

## Alur Feedback Robot ke Dashboard

1. Saat Django app ready dan `MQTT_ENABLED=True`, listener MQTT berjalan di background thread.
2. Listener subscribe ke `{root}/order/status/#`.
3. Saat feedback masuk, `handle_robot_feedback(topic, payload)` membaca device dari topic.
4. Aplikasi mencari assignment berdasarkan `order_id` dan device.
5. Assignment diperbarui sesuai status.
6. Untuk `received` dan `processing`, aplikasi broadcast `kitchen_update` ke group cashier.
7. Untuk `done`, aplikasi:
   - menyelesaikan assignment menjadi `done`;
   - mengkonsumsi stok sekali;
   - mengubah `Orders.ready_for_payment=True`;
   - broadcast `ready_for_payment` dan `kitchen_update` ke cashier.
8. Cashier menyelesaikan payment dengan status order `completed`.

## Event WebSocket yang Diterima Browser

Cashier browser terhubung ke:

```text
/ZenithKitchen/ws/order/channel/
/ZenithKitchen/ws/cashier/update/
```

Customer browser terhubung ke:

```text
/ZenithKitchen/ws/customer/order/
```

Event utama untuk cashier:

### `new_order`

```json
{
  "action": "new_order",
  "order": {
    "id": 7,
    "customer_name": "Meja 1",
    "total_price": 45000,
    "ready_for_payment": false,
    "kitchen": {
      "action": "kitchen_update",
      "order_id": 7,
      "order_code": "ORD-0007",
      "status": "assigned",
      "chef_mode": "robot",
      "device": "raspi1"
    }
  }
}
```

### `kitchen_update`

```json
{
  "action": "kitchen_update",
  "id": 3,
  "order_id": 7,
  "order_code": "ORD-0007",
  "status": "processing",
  "chef_id": 2,
  "chef_name": "Robot A",
  "chef_mode": "robot",
  "device": "raspi1",
  "error_message": ""
}
```

### `ready_for_payment`

```json
{
  "action": "ready_for_payment",
  "order_id": 7,
  "ready_for_payment": true,
  "status": "pending",
  "customer_name": "Meja 1",
  "kitchen": {
    "status": "done",
    "device": "raspi1"
  }
}
```

### `status_update`

```json
{
  "action": "status_update",
  "order_id": 7,
  "status": "completed",
  "customer_name": "Meja 1",
  "kitchen": {
    "status": "done"
  }
}
```

## Cara Membaca Status Order

### Dari MQTT

Untuk monitoring semua feedback robot:

```bash
mosquitto_sub -h 192.168.1.20 -t "zenithkitchen/order/status/#" -v
```

Untuk monitoring command yang dikirim aplikasi:

```bash
mosquitto_sub -h 192.168.1.20 -t "zenithkitchen/order/cmd/#" -v
```

### Dari HTTP Dashboard

Endpoint dashboard utama:

```text
POST /ZenithKitchen/change-page
```

Body contoh:

```json
{
  "page": 1,
  "limit": 10,
  "status": "pending",
  "ready_scope": "payment",
  "search": "",
  "date_from": "",
  "date_to": ""
}
```

Response berisi:

```json
{
  "orders": [
    {
      "id": 7,
      "ready_for_payment": true,
      "time": [
        {
          "status": "pending"
        }
      ],
      "kitchen": {
        "status": "done",
        "device": "raspi1"
      }
    }
  ],
  "pagination": {},
  "stats": {},
  "report": {}
}
```

Endpoint lama yang masih tersedia:

| Endpoint | Keterangan |
| --- | --- |
| `POST /ZenithKitchen/allorder-page` | Semua order |
| `POST /ZenithKitchen/pending-page` | Order status pending |
| `POST /ZenithKitchen/complete-page` | Order status completed |
| `POST /ZenithKitchen/cancel-page` | Order status cancelled |

### Dari Database/Service

Service yang dipakai UI:

```python
order_service.orders_payload(company=company)
order_service.serialize_order(order)
kitchen_service.assignment_for_order_payload(order)
```

Field status kitchen ada di:

```python
payload["orders"][0]["kitchen"]["status"]
```

Field status order bisnis ada di:

```python
payload["orders"][0]["time"][0]["status"]
```

Flag payment ada di:

```python
payload["orders"][0]["ready_for_payment"]
```

## Contoh Simulasi Manual MQTT

Subscribe command dari aplikasi:

```bash
mosquitto_sub -h 192.168.1.20 -t "zenithkitchen/order/cmd/#" -v
```

Kirim feedback JSON bahwa robot mulai proses:

```bash
mosquitto_pub -h 192.168.1.20 \
  -t "zenithkitchen/order/status/raspi1" \
  -m '{"order_id":"ORD-0007","status":"processing"}'
```

Kirim feedback JSON selesai:

```bash
mosquitto_pub -h 192.168.1.20 \
  -t "zenithkitchen/order/status/raspi1" \
  -m '{"order_id":"ORD-0007","status":"done"}'
```

Kirim feedback RAW:

```bash
mosquitto_pub -h 192.168.1.20 \
  -t "zenithkitchen/order/status/weintek1" \
  -m 'ORD-0007|2'
```

## Checklist Integrasi Robot

1. Set `.env` MQTT dan restart aplikasi.
2. Di Management -> Kitchen, buat chef `mode=robot`.
3. Pilih `device_kind`, `device_number`, dan `payload_format` yang sesuai robot.
4. Pastikan robot subscribe ke `{root}/order/cmd/{device}`.
5. Pastikan robot publish status ke `{root}/order/status/{device}`.
6. Robot wajib mengirim `order_id` dalam feedback agar assignment tepat.
7. Gunakan QoS 1 agar cocok dengan publish/subscribe aplikasi.
8. Setelah robot selesai, kirim `done`; aplikasi akan memindahkan order ke Ready for Payment.

## Catatan Operasional

- Listener MQTT tidak berjalan saat command management seperti `migrate`, `test`, `shell`, dan `collectstatic`.
- Listener retry otomatis 5 detik jika koneksi crash.
- Publish order memakai client baru per publish, lalu disconnect.
- Jika MQTT disabled, aplikasi tetap bisa berjalan, tetapi assignment robot mencatat error publish.
- Untuk chef person, cashier bisa menandai order siap bayar manual.
- Untuk chef robot, cashier tidak bisa menandai siap bayar manual; aplikasi menunggu feedback MQTT `done`.

## Rekomendasi Payload Robot

Gunakan JSON untuk Raspberry Pi atau device yang mudah parse JSON:

```json
{
  "order_id": "ORD-0007",
  "status": "processing"
}
```

Gunakan RAW untuk PLC/HMI sederhana:

```text
ORD-0007|1
```

Urutan feedback ideal:

```text
received -> processing -> done
```

Jika robot gagal:

```json
{
  "order_id": "ORD-0007",
  "status": "error",
  "message": "Motor timeout"
}
```

Saat ini handler menyimpan seluruh payload error ke `error_message`, sehingga pesan detail boleh disertakan di payload.

