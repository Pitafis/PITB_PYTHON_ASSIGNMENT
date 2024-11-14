from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import folium
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import json
import os
import io
from datetime import datetime
import time
from flask_cors import CORS
from pyngrok import ngrok



port_no = 5001
app = Flask(__name__)
CORS(app)
ngrok.set_auth_token("2n9BEg8hdXXncaW2ELnTfmgOO7x_7HrgoSfNZzAaXugpWiiwP")
public_url = ngrok.connect(port_no)

app.secret_key = 'your_secret_key'


def load_user():
    try:
        with open('save_data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data

def save_data(data):
    with open('save_data.json', 'w') as file:
        json.dump(data, file)

def save_purchase(purchase_data):
    purchase_data['date'] = datetime.now().strftime('%Y-%m-%d')
    df = pd.DataFrame([purchase_data])  
   
    file_exists = os.path.isfile('buying.csv')
    if file_exists and os.path.getsize('buying.csv') > 0:
        df.to_csv('buying.csv', mode='a', index=False, header=False)
    else:
        df.to_csv('buying.csv', mode='a', index=False, header=True)

inventory = {} 

def load_inventory_data():
    global inventory
    try:
        with open('inventory.json', 'r') as file:
            inventory = json.load(file)
        print("Data loaded successfully.") 
    except FileNotFoundError:
        inventory = {}  
        print("No inventory file found. Starting with an empty inventory.")
    except IOError as e:
        print(f"An error occurred while loading data: {e}")


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = load_user()
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        country = request.form["country"]

        if username in data:
            flash(f"{username} already exists. Please go to the sign-in page")
            return redirect(url_for('index'))
        else:
            if len(password) < 8:
                flash("Password must be at least 8 characters long")
                return redirect(url_for('index'))
            if password == confirm:
                data[username] = {"Password": password, "Country": country}
                save_data(data)
                flash("Signup successful! Please sign in.")
                return redirect(url_for('signin'))
            else:
                flash("Passwords do not match")
                return redirect(url_for('index'))

    return render_template('signup.html')

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        data = load_user()
        username = request.form["username"]
        password = request.form["password"]
        
        if username in data and data[username]["Password"] == password:
            session['username'] = username
            session['country'] = data[username].get("Country", "Unknown") 
            flash("Sign-in successful!")
            return redirect(url_for('show_inventory'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('signin'))

    return render_template('signin.html')

load_inventory_data()
products = {}

########################################################## DashBoard Section #######################################################################################

# Function to create sales bar chart using Seaborn and save as PNG
# Function to create a horizontal bar chart for sales
@app.route('/plot/sales_chart')
def sales_chart():
    df = pd.read_csv(r'E:\pitb_project\buying.csv')
    sales_data = df.groupby('product')['quantity'].sum().reset_index()
    
   
    sales_data = sales_data.sort_values(by='quantity', ascending=True)
    
    # Plotting with Seaborn
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    bar_plot = sns.barplot(data=sales_data, y='product', x='quantity', color='skyblue') 
    bar_plot.set(title="Total Sales per Product", xlabel="Total Quantity Sold", ylabel="Product")
   
    plt.tight_layout()

    
    buf = io.BytesIO()
    fig = bar_plot.get_figure()
    fig.savefig(buf, format="png")
    buf.seek(0)
    fig.clf()  
    
    return send_file(buf, mimetype='image/png')


@app.route('/plot/category_sales_chart')
def category_sales_chart():
   
    df = pd.read_csv(r'E:\pitb_project\buying.csv')
    category_data = df.groupby('category')['quantity'].sum().reset_index()
    
    
    sns.set(style="whitegrid")
    fig, ax = plt.subplots()
    ax.pie(
        category_data['quantity'], 
        labels=category_data['category'], 
        autopct='%1.1f%%', 
        startangle=140,
        colors=sns.color_palette('pastel')
    )
    ax.set_title("Category Wise Sales Distribution")

    
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)  
    
    return send_file(buf, mimetype='image/png')

@app.route('/plot/sales_by_month')
def sales_by_month():
    df = pd.read_csv(r'E:\pitb_project\buying.csv')
    
   
    df['date'] = pd.to_datetime(df['date'])
    
  
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.strftime('%Y-%m')  
    
    sales_data = df.groupby('month')['total_price'].sum().reset_index()
    
   
    sns.set(style="whitegrid")
    plt.figure(figsize=(12, 6))
    colors = sns.color_palette("husl", len(sales_data))  # Using 'husl' palette for distinct colors
    bar_plot = sns.barplot(data=sales_data, x='month', y='total_price', palette=colors)
    bar_plot.set(title="Monthly Sales", xlabel="Month", ylabel="Total Sales ($)")
  
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()  
    
    return send_file(buf, mimetype='image/png')

@app.route('/purchase_details')
def purchase_details():
    try:
        csv_path = r"E:\pitb_project\buying.csv"
        df = pd.read_csv(csv_path)
        df_reversed = df.iloc[::-1]
        purchase_data = df_reversed.to_dict(orient='records')
        print("Data loaded into purchase_data:", purchase_data)
    except Exception as e:
        print("Error loading CSV:", e)
        purchase_data = []

    return jsonify(purchase_data=purchase_data)



@app.route('/display_data')
def display_data():
    try:
        data = pd.read_csv(r'E:\pitb_project\buying.csv')

    
        total_sales = int(data['quantity'].sum())   
        total_products = int(data['product'].nunique())   
        total_orders = int(len(data))   
        revenue = f"{(data['total_price'].sum() / 1000):.1f}k"

    except Exception as e:
        print(f"Error reading CSV: {e}")
        total_sales = total_products = total_orders = revenue = 0

   
    return jsonify({
        'total_products': total_products,
        'total_sales': total_sales,
        'total_orders': total_orders,
        'revenue': revenue
    })


def get_coordinates(country):
    geolocator = Nominatim(user_agent="myCustomAppName")
    retry_count = 3
    for _ in range(retry_count):
        try:
            location = geolocator.geocode(country)
            if location:
                return location.latitude, location.longitude
            else:
                print(f"Could not find coordinates for {country}")
                return None, None
        except GeocoderTimedOut:
            print(f"Timeout error for {country}, retrying...")
            time.sleep(1) 
        except Exception as e:
            print(f"Error geocoding {country}: {e}")
            return None, None
    return None, None  

@app.route('/map')
def map():
    try:
        csv_path = r"E:\pitb_project\buying.csv"
        data = pd.read_csv(csv_path)
    except Exception as e:
        print("Error loading CSV:", e)


    df = data.groupby('country', as_index=False).agg({'total_price': 'sum'})
    print(df)  
   
    aus_map = folium.Map(location=[-25, 134], zoom_start=2)

   
    for index, row in df.iterrows():
        country = row['country']
        total_price = row['total_price']
        lat, lon = get_coordinates(country)
        
        
        if lat and lon:
            folium.Marker(location=[lat, lon], 
            popup=f"{country}: Total Sales : ${total_price}",
            tooltip=country
            ).add_to(aus_map)

    
    static_folder = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_folder):
        os.makedirs(static_folder)

    map_path = os.path.join(static_folder, 'aus_map.html')
    aus_map.save(map_path)

    return render_template('map.html')


@app.route('/inventory')
def show_inventory():
    return render_template('inventory.html', inventory=inventory)

@app.route('/buy', methods=['POST'])
def buy_product():
    try:
        invent_index = int(request.form["product_index"]) - 1
        quantity = int(request.form['quantity'])
        
        if quantity <= 0:
            flash("Please enter a positive number")
            return redirect(url_for('show_inventory'))
        
        invent_list = list(inventory.keys())
        if 0 <= invent_index < len(inventory):
            pro = invent_list[invent_index]
            
            if inventory[pro]['stock'] >= quantity:
                inventory[pro]['stock'] -= quantity  
                
            
                if pro in products:
                    products[pro] += quantity
                else:
                    products[pro] = quantity
                flash(f'{quantity} of {pro} added to your basket')
            else:
                flash(f'Sorry, only {inventory[pro]["stock"]} of {pro} available in stock')
        else:
            flash("Invalid product number")
    except ValueError:
        flash("Please enter a valid number")

    return redirect(url_for('show_inventory'))


@app.route('/update', methods=['POST'])
def update_product():
    try:
        invent_index = int(request.form["product_index"]) - 1
        new_pro_index = int(request.form["new_index"]) - 1

        products_list = list(products.keys())
        if 0 <= invent_index < len(products_list):
            old_product = products_list[invent_index]
            if 0 <= new_pro_index < len(inventory):
                new_product = list(inventory.keys())[new_pro_index]
                products[new_product] = products.pop(old_product)
                flash(f"{old_product} updated to {new_product} in your basket")
            else:
                flash("Invalid new product number")
        else:
            flash("Invalid product number in your basket")
    except ValueError:
        flash("Please enter a valid number")

    return redirect(url_for('show_inventory'))
        
# @app.route('/remove', methods=['POST'])
# def remove_product():
#     try:
#         invent_index = int(request.form["product_index"]) - 1
#         product_list = list(products.keys())
#         if 0 <= invent_index < len(product_list):
#             product_name = product_list[invent_index]
#             quantity = products.pop(product_name)
#             if product_name in inventory:
#                 inventory[product_name]['stock'] += quantity
#                 flash(f'{product_name} removed from your basket')
#             else:
#                 flash("This product is not listed in the inventory")
#         else:
#             flash("Invalid product number")
#     except ValueError:
#         flash("Please enter a valid number")
    
#     return redirect(url_for('show_inventory'))

@app.route('/basket')
def view_basket():
    total_basket_price = sum(quantity * inventory[product]['price'] for product, quantity in products.items())
    return render_template('basket.html', basket=products, inventory=inventory, total_basket_price=total_basket_price)

@app.route('/remove_from_basket/<product_name>', methods=['POST', 'GET'])
def remove_from_basket(product_name):
    if product_name in products:
        quantity = products.pop(product_name)
        inventory[product_name]['stock'] += quantity
        flash(f'{product_name} removed from your basket')
    else:
        flash("This product is not in your basket")
    
    return redirect(url_for('view_basket'))

@app.route('/buy_basket', methods=['POST'])
def buy_basket():
    if 'username' not in session:
        flash("Please sign in to make a purchase.")
        return redirect(url_for('signin'))

    if not products:
        flash("Your basket is empty.")
        return redirect(url_for('view_basket'))

    
    for product, quantity in products.items():
        category = inventory[product]["category"]
        purchase_data = {
            "username": session['username'],
            "country": session['country'],
            "product": product,
            "quantity": quantity,
            "category": category,
            "total_price": quantity * inventory[product]["price"]
        }
        save_purchase(purchase_data)
        save_inventory_data()

    
    products.clear()
    flash("Purchase successful! Your order has been placed.")

    return redirect(url_for('show_inventory'))



@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == 'POST':
        key = 1234
        try:
            pin = int(request.form["pin"])
            if pin == key:
                return render_template('dashboard.html')
            else:
                flash("Enter correct PIN")
        except ValueError:
            flash("PIN should be numeric")
    
    return render_template('admin.html')


@app.route('/manage_stock', methods=['GET', 'POST'])
def manage_stock():
    if request.method == 'POST':
        choice = request.form['choice']

        if choice == '1': 
            new_product = request.form['new_product']
            category = request.form['category']
            if new_product in inventory:
                flash(f'{new_product} already exists in the inventory.')
            else:
                try:
                    new_price = float(request.form['new_price'])
                    new_stock = int(request.form['new_stock'])
                    inventory[new_product] = {"price": new_price, "stock": new_stock}
                    flash(f'{new_product} added to the inventory with price ${new_price} and stock {new_stock}')
                    save_inventory_data()
                except ValueError:
                    flash("Please enter valid price and stock")

        elif choice == '2': 
            product_name = request.form['product_name']
            if product_name in inventory:
                try:
                    new_price = float(request.form['new_price'])
                    new_stock = int(request.form['new_stock'])
                    inventory[product_name]["stock"] += new_stock
                    inventory[product_name]["price"] = new_price
                    flash(f'{product_name} updated with new price ${new_price} and new stock {new_stock}')
                    save_inventory_data()
                except ValueError:
                    flash("Please enter valid price and stock")
            else:
                flash("Product not found in inventory.")

        elif choice == '3':  
            product_name = request.form['product_name']
            if product_name in inventory:
                inventory.pop(product_name)
                flash(f'{product_name} removed from your inventory')
                save_inventory_data()
            else:
                flash("Product not found in inventory.")

    return render_template('manage_stock.html', inventory=inventory)


@app.route('/save_data', methods=["POST"])
def save_inventory_data():
    try:
        with open('inventory.json', 'w') as file:
            json.dump(inventory, file)
        # with open('basket.json', 'w') as file:
        #     json.dump(products, file)
        # flash("Data saved successfully")
    except IOError as e:
        flash(f"An error occurred while saving data: {e}")

    return redirect(url_for('show_inventory'))

@app.route('/load_data', methods=["POST"])
def load_inventory_data():
    global inventory, products
    try:
        with open('inventory.json', 'r') as file:
            inventory = json.load(file)
        # with open('basket.json', 'r') as file:
        #     products = json.load(file)
        flash("Data loaded successfully.")
    except IOError as e:
        flash(f'An error occurred while loading data: {e}')
        return None

    return {'inventory': inventory, 'products': products}

@app.route("/signout")
def signout():
    session.pop("username", None)
    session.pop("country", None)
    flash("You have been signed out.")
    return redirect(url_for('index'))


# def purchase_details(purchase_details):
#     df = pd.read_csv(r"E:\pitb_project\buying.csv")
#     purchase_details = df
#     return purchase_details



if __name__ == '__main__':
    print(f"Public URL : {public_url}")
    app.run(port=port_no)
