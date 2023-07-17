from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
from flask import jsonify
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson import json_util
# import openai
OPENAI_API_KEY="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"

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# Login and signup

client = MongoClient("mongodb+srv://anji:kommu@cluster0.dxyi0uo.mongodb.net/Zomato?retryWrites=true&w=majority")
db = client["Zomato"]
users_collection = db["users"]
menu_collection = db["menu"]
orders_collection = db["orders"]

@app.route('/orders', methods=['GET'])
def orders():
        data=orders_collection.find()
        return json_util.dumps(data)

@app.route('/menu', methods=['GET'])
def get_menu():
    data=menu_collection.find()
    return json_util.dumps(data)
#     with open('data.json') as file:
#         data = json.load(file)
#         return jsonify(data["menu"])

@app.route("/signup", methods=["POST"])
def signup():
    # Retrieve the data from the request
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    type = data["type"]
    email = data["email"]

    if not username or not password or not email:
        # Set the status code to 400 (Bad Request)
        return jsonify({"message": "Username and password cannot be empty"}), 400

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Create a new user document
    new_user = {"username": username, "password": hashed_password, "email":email, "type":type}
    # Insert the user document into the users collection
    users_collection.insert_one(new_user)

    return jsonify({"message": "User created successfully"})

@app.route("/login", methods=["GET"])
def login():
    # Retrieve the data from the request
    email = request.args.get('email')
    password = request.args.get('password')

    # Find the user document by username
    user = users_collection.find_one({"email": email})
    # print(user)
    if user and bcrypt.check_password_hash(user["password"], password):
        return json_util.dumps(user), 200
    else:
        return jsonify({"Error": "Invalid username or password"}), 201

@app.route("/admin", methods=["GET"])
def adminLogin():
    # Retrieve the data from the request
    email = request.args.get('email')
    password = request.args.get('password')

    # Find the user document by username
    user = users_collection.find_one({"email": email})
    # print(user)
    if user and bcrypt.check_password_hash(user["password"], password):
        return json_util.dumps(user), 200
    else:
        return jsonify({"Error": "Invalid username or password"}), 201


# @app.route('/')
# def home():
#     return render_template('home.html')

@app.route('/menu', methods=['POST'])
def add_dish():
    data = request.json
    new_menu_item = {
        'name': data['name'],
        'id': data['id'],
        'price': data['price'],
        'available': data['available'],
        'stock': data['stock'],
        'reviews': data['reviews'],
        'imageUrl': data['imageUrl'],
    }
    menu_collection.insert_one(new_menu_item)
    return jsonify({'message': 'Dish has been successfully'}), 201

@app.route('/menu/<int:dish_id>', methods=['DELETE'])
def remove_dish(dish_id):
    result = menu_collection.delete_one({"id": int(dish_id)})
    if result.deleted_count > 0:
        return jsonify({"message": "Dish removed successfully."})
    else:
        return jsonify({"message": "Dish not found."}), 404

@app.route('/menu/<int:dish_id>', methods=['PUT'])
def update_availability(dish_id):
    updated_dish = request.json
    result = menu_collection.update_one({"id": dish_id}, {"$set": {"available": updated_dish["available"]}})
    if result.modified_count > 0:
        return jsonify({"message": "Dish availability updated successfully."})
    else:
        return jsonify({"message": "Dish not found."}), 404
    
@app.route('/menu/<int:dish_id>', methods=['PATCH'])
def update_feedback(dish_id):
    updated_dish = request.json
    result = menu_collection.update_one({"id": dish_id}, {"$set": {"reviews": updated_dish["reviews"]}})
    if result.modified_count > 0:
        return jsonify({"message": "Dish feedback updated successfully."})
    else:
        return jsonify({"message": "Dish not found."}), 404
    

@app.route('/orders/<dish_ids>', methods=['POST'])
def take_order(dish_ids):
    order_data = request.json
    dish_ids = dish_ids.split(',')
    customer_name = order_data.get("customer_name")

    total_price = 0
    for dish_id in dish_ids:
        dish_id=int(dish_id)
        dish = menu_collection.find_one({"id": dish_id,"stock": {"$gt": 0}})
        if not dish:
            return jsonify({"error": f"Dish with ID {dish_id} not found or not available."}), 404

        dish_price = dish["price"]
        dish_stock = dish["stock"]
        dish_item = dish["name"]

        existing_order = orders_collection.find_one({"items.dish_id": dish_id})
        if existing_order:
            existing_item = next(item for item in existing_order["items"] if item["dish_id"] == dish_id)
            existing_item["quantity"] += 1
            existing_order["total_price"] += dish_price
            total_price += dish_price
            dish_stock -= 1  # Reduce the stock count by 1
            orders_collection.update_one({"order_id": existing_order["order_id"]}, {"$set": existing_order})
        else:
            order_item = {"dish_id": dish_id, "quantity": 1}
            order_items = [order_item]
            total_price += dish_price
            dish_stock -= 1  # Reduce the stock count by 1
            # print(dish_stock)
            new_order = {
                "order_id":dish_id,
                "customer_name": customer_name,
                "items": order_items,
                "status": "received",
                "item":dish_item,
                "total_price": dish_price
            }
            orders_collection.insert_one(new_order)

        # Update dish stock and availability in the menu collection
        menu_collection.update_one({"_id": dish_id}, {"$set": {"stock": dish_stock}})
        if dish_stock == 0:
            menu_collection.update_one({"_id": dish_id}, {"$set": {"available": False}})

    return jsonify({"message": "Order received successfully.", "total_price": total_price})

@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    updated_order = request.json
    order = orders_collection.find_one({"order_id": order_id})
    if order:
        order["status"] = updated_order["status"]
        orders_collection.update_one({"order_id": order["order_id"]}, {"$set": order})
        return jsonify({"message": "Order status updated successfully."})
    else:
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














































# with open('data.json', 'r+') as file:
    #     data = json.load(file)
    #     menu = data["menu"]
    #     menu.append(new_dish)
    #     file.seek(0)
    #     json.dump(data, file, indent=4)
    #     file.truncate()
    # return jsonify({"message": "Dish added successfully."})


    # with open('data.json', 'r+') as file:
    #     data = json.load(file)
    #     menu = data["menu"]
    #     for dish in menu:
    #         if dish["id"] == dish_id:
    #             menu.remove(dish)
    #             file.seek(0)
    #             json.dump(data, file, indent=4)
    #             file.truncate()
    #             return jsonify({"message": "Dish removed successfully."})
    # return jsonify({"message": "Dish not found."}), 404

# with open('data.json', 'r+') as file:
    #     data = json.load(file)
    #     menu = data["menu"]
    #     for dish in menu:
    #         if dish["id"] == dish_id:
    #             dish["available"] = updated_dish["available"]
    #             file.seek(0)
    #             json.dump(data, file, indent=4)
    #             file.truncate()
    #             return jsonify({"message": "Dish availability updated successfully."})
    # return jsonify({"message": "Dish not found."}), 404


# def take_order(dish_ids):
#     order_data = request.json
#     dish_ids = dish_ids.split(',')
#     customer_name = order_data.get("customer_name")
#     with open('data.json', 'r+') as file:
#         data = json.load(file)
#         menu = data["menu"]
#         orders = data["orders"]
#         total_price = 0
#         for dish_id in dish_ids:
#             dish_id = int(dish_id)
#             dish = next((d for d in menu if d["id"] == dish_id and d["available"]), None)
#             if not dish:
#                 return jsonify({"error": f"Dish with ID {dish_id} not found or not available."}), 404
#             if dish["stock"] <= 0:
#                 return jsonify({"error": f"Dish with ID {dish_id} is out of stock."}), 400
#             existing_order = next((o for o in orders if any(item["dish_id"] == dish_id for item in o["items"])), None)
#             if existing_order:
#                 existing_item = next(item for item in existing_order["items"] if item["dish_id"] == dish_id)
#                 existing_item["quantity"] += 1
#                 existing_order["total_price"] += dish["price"]
#                 total_price += dish["price"]
#                 dish["stock"] -= 1  # Reduce the stock count by 1
#             else:
#                 order_item = {"dish_id": dish_id, "quantity": 1}
#                 order_items = [order_item]
#                 total_price += dish["price"]
#                 dish["stock"] -= 1  # Reduce the stock count by 1
#                 order = {
#                     "order_id": len(orders) + 1,
#                     "customer_name": customer_name,
#                     "items": order_items,
#                     "status": "received",
#                     "total_price": dish["price"]
#                 }
#                 orders.append(order)
#         file.seek(0)
#         json.dump(data, file, indent=4)
#         file.truncate()
#     return jsonify({"message": "Order received successfully.", "total_price": total_price})

# def update_order_status(order_id):
#     updated_order = request.json
#     with open('data.json', 'r+') as file:
#         data = json.load(file)
#         orders = data["orders"]
#         for order in orders:
#             if order["order_id"] == order_id:
#                 order["status"] = updated_order["status"]
#                 file.seek(0)
#                 json.dump(data, file, indent=4)
#                 file.truncate()
#                 return jsonify({"message": "Order status updated successfully."})
#     return jsonify({"message": "Order not found."}), 404