from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI()

# ══ MODELS ════════════════════════════════════════════════════════

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=100)
    delivery_address: str = Field(..., min_length=10)

class NewProduct(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    in_stock: bool = True

class CheckoutRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    delivery_address: str = Field(..., min_length=10)

# ══ DATA ══════════════════════════════════════════════════════════

products = [
    {'id': 1, 'name': 'Wireless Mouse', 'price': 499, 'category': 'Electronics', 'in_stock': True},
    {'id': 2, 'name': 'Notebook', 'price': 99, 'category': 'Stationery', 'in_stock': True},
    {'id': 3, 'name': 'USB Hub', 'price': 799, 'category': 'Electronics', 'in_stock': False},
    {'id': 4, 'name': 'Pen Set', 'price': 49, 'category': 'Stationery', 'in_stock': True},
]

orders = []
cart = []
order_counter = 1

# ══ HELPERS ═══════════════════════════════════════════════════════

def find_product(product_id: int):
    return next((p for p in products if p['id'] == product_id), None)

def calculate_total(product: dict, quantity: int):
    return product['price'] * quantity

# ══ BASIC ROUTES ══════════════════════════════════════════════════

@app.get('/')
def home():
    return {"message": "Welcome to our E-commerce API"}

@app.get('/products')
def get_products():
    return {"products": products, "total": len(products)}

# ══ SEARCH ════════════════════════════════════════════════════════

@app.get('/products/search')
def search_products(keyword: str = Query(...)):
    result = [p for p in products if keyword.lower() in p['name'].lower()]

    if not result:
        return {"message": f"No products found for: {keyword}", "results": []}

    return {"keyword": keyword, "total_found": len(result), "results": result}

# ══ SORT ══════════════════════════════════════════════════════════

@app.get('/products/sort')
def sort_products(sort_by: str = "price", order: str = "asc"):
    if sort_by not in ["price", "name"]:
        return {"error": "sort_by must be 'price' or 'name'"}

    if order not in ["asc", "desc"]:
        return {"error": "order must be 'asc' or 'desc'"}

    return {
        "sort_by": sort_by,
        "order": order,
        "products": sorted(products, key=lambda p: p[sort_by], reverse=(order=="desc"))
    }

# ══ SORT BY CATEGORY ══════════════════════════════════════════════

@app.get('/products/sort-by-category')
def sort_by_category():
    sorted_data = sorted(products, key=lambda p: (p['category'].lower(), p['price']))
    return {"products": sorted_data}

# ══ PAGINATION ════════════════════════════════════════════════════

@app.get('/products/page')
def paginate_products(page: int = 1, limit: int = 2):
    start = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "total": len(products),
        "total_pages": -(-len(products)//limit),
        "products": products[start:start+limit]
    }

# ══ BROWSE (SEARCH + SORT + PAGINATE) ═════════════════════════════

@app.get('/products/browse')
def browse(
    keyword: str = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = 1,
    limit: int = 4
):
    result = products

    # SEARCH
    if keyword:
        result = [p for p in result if keyword.lower() in p['name'].lower()]

    # VALIDATION
    if sort_by not in ["price", "name"]:
        return {"error": "sort_by must be 'price' or 'name'"}

    if order not in ["asc", "desc"]:
        return {"error": "order must be 'asc' or 'desc'"}

    # SORT
    result = sorted(result, key=lambda p: p[sort_by], reverse=(order=="desc"))

    # PAGINATION
    total = len(result)
    start = (page - 1) * limit

    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_found": total,
        "total_pages": -(-total//limit) if total else 0,
        "products": result[start:start+limit]
    }

# ══ CRUD ══════════════════════════════════════════════════════════

@app.post('/products')
def add_product(data: NewProduct, response: Response):
    if any(p['name'].lower() == data.name.lower() for p in products):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Product already exists"}

    new_id = max(p['id'] for p in products) + 1
    product = {**data.dict(), "id": new_id}

    products.append(product)
    response.status_code = status.HTTP_201_CREATED
    return {"message": "Product added", "product": product}

@app.put('/products/{product_id}')
def update_product(product_id: int, price: int = None, in_stock: bool = None):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}

    if price is not None:
        if price <= 0:
            return {"error": "Price must be > 0"}
        product['price'] = price

    if in_stock is not None:
        product['in_stock'] = in_stock

    return {"message": "Updated", "product": product}

@app.delete('/products/{product_id}')
def delete_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}

    products.remove(product)
    return {"message": "Deleted"}

@app.get('/products/{product_id}')
def get_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}
    return {"product": product}

# ══ ORDERS ════════════════════════════════════════════════════════

@app.post('/orders')
def place_order(data: OrderRequest):
    global order_counter

    product = find_product(data.product_id)
    if not product:
        return {"error": "Product not found"}

    if not product['in_stock']:
        return {"error": "Out of stock"}

    order = {
        "order_id": order_counter,
        "customer_name": data.customer_name,
        "product": product['name'],
        "quantity": data.quantity,
        "delivery_address": data.delivery_address,
        "total_price": calculate_total(product, data.quantity),
        "status": "confirmed"
    }

    orders.append(order)
    order_counter += 1
    return {"message": "Order placed", "order": order}

@app.get('/orders')
def get_orders():
    return {"orders": orders}

# SEARCH ORDERS

@app.get('/orders/search')
def search_orders(customer_name: str):
    result = [o for o in orders if customer_name.lower() in o['customer_name'].lower()]

    if not result:
        return {"message": f"No orders found for: {customer_name}", "orders": []}

    return {"customer_name": customer_name, "total_found": len(result), "orders": result}

# PAGINATE ORDERS

@app.get('/orders/page')
def paginate_orders(page: int = 1, limit: int = 3):
    start = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "total_orders": len(orders),
        "total_pages": -(-len(orders)//limit),
        "orders": orders[start:start+limit]
    }

# ══ CART ══════════════════════════════════════════════════════════

@app.post('/cart/add')
def add_to_cart(product_id: int, quantity: int = 1):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}

    if not product['in_stock']:
        return {"error": "Out of stock"}

    for item in cart:
        if item['product_id'] == product_id:
            item['quantity'] += quantity
            item['subtotal'] = calculate_total(product, item['quantity'])
            return {"message": "Updated", "cart_item": item}

    item = {
        "product_id": product_id,
        "product_name": product['name'],
        "quantity": quantity,
        "subtotal": calculate_total(product, quantity)
    }

    cart.append(item)
    return {"message": "Added", "cart_item": item}

@app.get('/cart')
def view_cart():
    return {
        "items": cart,
        "total": sum(i['subtotal'] for i in cart)
    }

@app.post('/cart/checkout')
def checkout(data: CheckoutRequest):
    global order_counter

    if not cart:
        return {"error": "Cart empty"}

    placed = []

    for item in cart:
        order = {
            "order_id": order_counter,
            "customer_name": data.customer_name,
            "product": item['product_name'],
            "quantity": item['quantity'],
            "delivery_address": data.delivery_address,
            "total_price": item['subtotal'],
            "status": "confirmed"
        }

        orders.append(order)
        placed.append(order)
        order_counter += 1

    cart.clear()
    return {"message": "Checkout successful", "orders": placed}

@app.delete('/cart/{product_id}')
def remove_cart(product_id: int):
    for item in cart:
        if item['product_id'] == product_id:
            cart.remove(item)
            return {"message": "Removed"}

    return {"error": "Not found"}