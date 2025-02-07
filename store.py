import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from reportlab.pdfgen import canvas
import io
import pandas as pd
import json
import os

# Load Firebase credentials from environment variable
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)

# Connect to Firestore
db = firestore.client()


st.title("Billing & Customer Management System")

menu = ["Add Product", "Manage Products", "Add Customer", "Manage Customers", "Generate Bill", "View Orders"]
choice = st.sidebar.selectbox("Menu", menu)

# --------------------- ADD PRODUCT ---------------------
if choice == "Add Product":
    st.subheader("Add New Product")
    name = st.text_input("Product Name")
    price = st.number_input("Price", min_value=0.0, format="%0.2f")
    
    if st.button("Add Product"):
        db.collection("products").add({"name": name, "price": price})
        st.success("Product Added Successfully!")

    # Display existing products in a table
    st.subheader("Available Products")
    products = db.collection("products").stream()
    product_data = [{"ID": p.id, "Name": p.to_dict()["name"], "Price": p.to_dict()["price"]} for p in products]
    
    if product_data:
        df = pd.DataFrame(product_data)
        st.dataframe(df)  # Show products in a table

# --------------------- MANAGE PRODUCTS ---------------------
elif choice == "Manage Products":
    st.subheader("Edit or Delete Products")
    products = db.collection("products").stream()
    product_list = {p.id: p.to_dict()["name"] for p in products}

    if product_list:
        selected_id = st.selectbox("Select Product", list(product_list.keys()), format_func=lambda x: product_list[x])
        selected_product = db.collection("products").document(selected_id).get().to_dict()

        new_name = st.text_input("Edit Name", selected_product["name"])
        new_price = st.number_input("Edit Price", value=selected_product["price"], format="%0.2f")

        if st.button("Update Product"):
            db.collection("products").document(selected_id).update({"name": new_name, "price": new_price})
            st.success("Product Updated Successfully!")

        if st.button("Delete Product"):
            db.collection("products").document(selected_id).delete()
            st.warning("Product Deleted Successfully!")
    else:
        st.warning("No products available!")

# --------------------- ADD CUSTOMER ---------------------
elif choice == "Add Customer":
    st.subheader("Add New Customer")
    name = st.text_input("Customer Name")
    email = st.text_input("Customer Email")
    address = st.text_area("Customer Address")
    location = st.text_input("Location")

    if st.button("Add Customer"):
        db.collection("customers").add({"name": name, "email": email, "address": address, "location": location})
        st.success("Customer Added Successfully!")

    # Display existing customers in a table
    st.subheader("Existing Customers")
    customers = db.collection("customers").stream()
    customer_data = [{"ID": c.id, "Name": c.to_dict()["name"], "Email": c.to_dict()["email"],
                      "Address": c.to_dict()["address"], "Location": c.to_dict()["location"]} for c in customers]

    if customer_data:
        df = pd.DataFrame(customer_data)
        st.dataframe(df)

# --------------------- MANAGE CUSTOMERS ---------------------
elif choice == "Manage Customers":
    st.subheader("Edit or Delete Customers")
    customers = db.collection("customers").stream()
    customer_list = {c.id: c.to_dict()["name"] for c in customers}

    if customer_list:
        selected_id = st.selectbox("Select Customer", list(customer_list.keys()), format_func=lambda x: customer_list[x])
        selected_customer = db.collection("customers").document(selected_id).get().to_dict()

        new_name = st.text_input("Edit Name", selected_customer["name"])
        new_email = st.text_input("Edit Email", selected_customer["email"])
        new_address = st.text_area("Edit Address", selected_customer["address"])
        new_location = st.text_input("Edit Location", selected_customer["location"])

        if st.button("Update Customer"):
            db.collection("customers").document(selected_id).update(
                {"name": new_name, "email": new_email, "address": new_address, "location": new_location}
            )
            st.success("Customer Updated Successfully!")

        if st.button("Delete Customer"):
            db.collection("customers").document(selected_id).delete()
            st.warning("Customer Deleted Successfully!")
    else:
        st.warning("No customers available!")


elif choice == "View Orders":
    st.subheader("View Orders")
    filter_status = st.selectbox("Filter Orders", ["All", "Paid", "Unpaid"])
    orders = db.collection("orders").stream()
    
    for order in orders:
        order_data = order.to_dict()
        if filter_status != "All" and order_data["payment_status"] != filter_status:
            continue
        
        st.markdown(f"""
        <div style='border: 2px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px;'>
            <h4>{order_data['customer_name']}</h4>
            <p>Email: {order_data['customer_email']}</p>
            <p>Total: ₹{order_data['total']}</p>
            <p style='color: {'green' if order_data['payment_status']=='Paid' else 'red'};'>Status: {order_data['payment_status']}</p>
        </div>
        """, unsafe_allow_html=True)


# --------------------- GENERATE BILL ---------------------
elif choice == "Generate Bill":
    st.subheader("Generate & Download Bill")

    # Select Customer
    customers = db.collection("customers").stream()
    customer_dict = {c.id: c.to_dict()["name"] for c in customers}
    
    if customer_dict:
        selected_customer_id = st.selectbox("Select Customer", list(customer_dict.keys()), format_func=lambda x: customer_dict[x])
        selected_customer = db.collection("customers").document(selected_customer_id).get().to_dict()

    # Select Products
    products = db.collection("products").stream()
    product_dict = {p.id: p.to_dict() for p in products}
    
    order = {}
    total = 0
    for product_id, product in product_dict.items():
        qty = st.number_input(f"{product['name']} ({product['price']}/unit)", min_value=0, step=1)
        if qty > 0:
            order[product['name']] = (product['price'], qty)
            total += product['price'] * qty

    # Generate PDF Bill
    if st.button("Generate PDF Bill"):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 800, "Bill Receipt")
        c.drawString(100, 780, f"Customer: {selected_customer['name']}")
        c.drawString(100, 760, f"Email: {selected_customer['email']}")
        c.drawString(100, 740, f"Address: {selected_customer['address']}")
        c.drawString(100, 720, f"Location: {selected_customer['location']}")
        
        y = 700
        for item, (price, qty) in order.items():
            c.drawString(100, y, f"{item}: {qty} x {price} = {qty * price}")
            y -= 20
        
        c.drawString(100, y - 20, f"Total: {total}")
        c.save()
        buffer.seek(0)
        st.download_button(label="Download Bill", data=buffer, file_name="bill.pdf", mime="application/pdf")
