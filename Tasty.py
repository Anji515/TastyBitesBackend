from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/menu', methods=['GET'])
def get_menu():
    with open('data.json') as file:
        data = json.load(file)
        return jsonify(data["menu"])

@app.route('/menu', methods=['POST'])
def add_dish():
    new_dish = request.json
    with open('data.json', 'r+') as file:
        data = json.load(file)
        menu = data["menu"]
        menu.append(new_dish)
        file.seek(0)
        json.dump(data, file, indent=4)
        file.truncate()
    return jsonify({"message": "Dish added successfully."})

@app.route('/menu/<int:dish_id>', methods=['DELETE'])
def remove_dish(dish_id):
    with open('data.json', 'r+') as file:
        data = json.load(file)
        menu = data["menu"]
        for dish in menu:
            if dish["id"] == dish_id:
                menu.remove(dish)
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return jsonify({"message": "Dish removed successfully."})
    return jsonify({"message": "Dish not found."}), 404

@app.route('/menu/<int:dish_id>', methods=['PUT'])
def update_availability(dish_id):
    updated_dish = request.json
    with open('data.json', 'r+') as file:
        data = json.load(file)
        menu = data["menu"]
        for dish in menu:
            if dish["id"] == dish_id:
                dish["available"] = updated_dish["available"]
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return jsonify({"message": "Dish availability updated successfully."})
    return jsonify({"message": "Dish not found."}), 404

@app.route('/orders/<dish_ids>', methods=['POST'])
def take_order(dish_ids):
    order_data = request.json
    dish_ids = dish_ids.split(',')
    customer_name = order_data.get("customer_name")
    with open('data.json', 'r+') as file:
        data = json.load(file)
        menu = data["menu"]
        orders = data["orders"]
        total_price = 0
        for dish_id in dish_ids:
            dish_id = int(dish_id)
            dish = next((d for d in menu if d["id"] == dish_id and d["available"]), None)
            if not dish:
                return jsonify({"error": f"Dish with ID {dish_id} not found or not available."}), 404
            if dish["stock"] <= 0:
                return jsonify({"error": f"Dish with ID {dish_id} is out of stock."}), 400
            existing_order = next((o for o in orders if any(item["dish_id"] == dish_id for item in o["items"])), None)
            if existing_order:
                existing_item = next(item for item in existing_order["items"] if item["dish_id"] == dish_id)
                existing_item["quantity"] += 1
                existing_order["total_price"] += dish["price"]
                total_price += dish["price"]
                dish["stock"] -= 1  # Reduce the stock count by 1
            else:
                order_item = {"dish_id": dish_id, "quantity": 1}
                order_items = [order_item]
                total_price += dish["price"]
                dish["stock"] -= 1  # Reduce the stock count by 1
                order = {
                    "order_id": len(orders) + 1,
                    "customer_name": customer_name,
                    "items": order_items,
                    "status": "received",
                    "total_price": dish["price"]
                }
                orders.append(order)
        file.seek(0)
        json.dump(data, file, indent=4)
        file.truncate()
    return jsonify({"message": "Order received successfully.", "total_price": total_price})

@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    updated_order = request.json
    with open('data.json', 'r+') as file:
        data = json.load(file)
        orders = data["orders"]
        for order in orders:
            if order["order_id"] == order_id:
                order["status"] = updated_order["status"]
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
                return jsonify({"message": "Order status updated successfully."})
    return jsonify({"message": "Order not found."}), 404


@app.route('/orders/<status>', methods=['GET'])
def get_orders_by_status(status):
    with open('data.json') as file:
        data = json.load(file)
        orders = data["orders"]
        filtered_orders = [order for order in orders if order["status"] == status]
        return jsonify(filtered_orders)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Invalid route."}), 404

if __name__ == '__main__':
    app.run(port=8080)