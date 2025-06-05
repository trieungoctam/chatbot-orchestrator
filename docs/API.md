### 1. Request
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "index": int,
  "messages": [
    {
      "role": "",
      "content": ""
    }
  ],
  "resources": {}
}
```

### 2. Gửi tin nhắn

**Response Body:**
```json
{
  "conversation_id": "string",
  "action": "CHAT",
  "data": {
    "answers": ["string"],
    "images": ["string"],
    "sub_answers": ["string"]
  }
}
```

### 3. Tạo đơn hàng trên Nhanh.vn

**Endpoint:** `POST /api/v1/create-nhanh-order`

**Mô tả:** Tạo đơn hàng mới trên hệ thống Nhanh.vn và gửi thông báo

**Response Body:**
```json
{
  "conversation_id": "string",
  "action": "CREATE_ORDER",
  "data": {
    "customer_info": {
        "name": "string",
        "phone": "string",
        "weight": "string",
        "height": "string",
        "full_address": "string",
        "district_name": "string",
        "province_name": "string",
        "ward_name": "string"
    },
    "products": [
        {
        "product_code": "string",
        "product_id_mapping": "integer",
        "product_name": "string",
        "quantity": "integer",
        "price": "float"
        }
    ],
    "shipping_fee": "float",
    "traffic_source": "string",
    "note": "string"
  }
}
```

### 4. Thông báo cho Sale

**Endpoint:** `POST /api/v1/notify-sale`

**Mô tả:** Gửi thông báo cho đội ngũ Sale để hỗ trợ khách hàng

**Response Body:**
```json
{
    "conversation_id": "string",
    "action": "NOTIFY",
    "data": {
        "phone": "string",
        "intent": "string"
    }
}
```