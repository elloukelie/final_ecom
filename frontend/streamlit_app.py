# frontend/streamlit_app.py

import streamlit as st
import requests
import pandas as pd
import json
import time
import re
import os
from openai import OpenAI

# Import ML dashboard module
try:
    from admin_ml_dashboard import show_ml_dashboard
    ML_DASHBOARD_AVAILABLE = True
except ImportError:
    ML_DASHBOARD_AVAILABLE = False
    print("ML Dashboard module not available. ML features will be disabled.")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # This loads .env file from the current directory
except ImportError:
    # dotenv not installed, try to load from parent directory manually
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value

# Import constants
from constants import API_BASE_URL, get_image_url

st.set_page_config(layout="wide", page_title="E-Commerce Platform")

# --- URL Routing Setup ---
def get_url_params():
    """Extract URL parameters for routing"""
    query_params = st.query_params
    return query_params

# --- Admin Helper Functions ---
def is_admin_user():
    """Check if current user is admin"""
    if 'current_user' in st.session_state and st.session_state.current_user:
        return st.session_state.current_user.get('is_admin', False)
    return False

def auto_login_admin():
    """Auto-login admin user if not already logged in"""
    # Don't auto-login if user is already logged in or has intentionally logged out
    if st.session_state.logged_in or st.session_state.get('user_logged_out', False):
        return
        
    # Check URL parameters to see if we're on a page that specifically requested auto-admin
    url_params = get_url_params()
    auto_admin = url_params.get("auto_admin")
    current_page_param = url_params.get("page", "shop")
    
    # Auto-login for admin-only pages like ML, admin, etc.
    admin_pages = ["ml", "admin", "dashboard", "customers", "products", "admin-orders", "users"]
    should_auto_login = (auto_admin == "true" or current_page_param in admin_pages) and not st.session_state.get('admin_login_attempted', False)
    
    # Only auto-login if explicitly requested via URL parameter OR accessing admin pages
    if should_auto_login:
        try:
            # Get admin credentials from environment variables
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin")
            
            # Try to login as admin
            response = requests.post(
                f"{API_BASE_URL}/token",
                data={"username": admin_username, "password": admin_password}
            )
            if response.status_code == 200:
                token_data = response.json()
                st.session_state.access_token = token_data["access_token"]
                st.session_state.logged_in = True
                
                # Get user info
                user_info = make_authenticated_request("GET", "/users/me")
                if user_info and user_info.get('username') == 'admin':
                    st.session_state.current_user = user_info
                    # Redirect to admin dashboard
                    navigate_to("admin")
                    st.rerun()
            else:
                st.session_state.admin_login_attempted = True
        except:
            st.session_state.admin_login_attempted = True

def get_all_users():
    """Fetch all users for admin management"""
    return make_authenticated_request("GET", "/admin/users")

def update_user_admin_status(user_id, is_admin):
    """Update admin status for a user"""
    return make_authenticated_request("PUT", f"/admin/users/{user_id}/admin-status", 
                                    params={"is_admin": is_admin})

def update_user_active_status(user_id, is_active):
    """Update active status for a user"""
    return make_authenticated_request("PUT", f"/admin/users/{user_id}/active-status", 
                                    params={"is_active": is_active})

def set_url_params(**params):
    """Set URL parameters for routing"""
    st.query_params.update(params)

# --- Cart and Favorites Management Functions ---
def initialize_cart_and_favorites():
    """Initialize cart and favorites from backend if logged in, otherwise use session state"""
    if 'cart' not in st.session_state:
        st.session_state.cart = {}
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()
    
    # Load from backend if logged in
    if st.session_state.logged_in:
        load_cart_from_backend()
        load_favorites_from_backend()

def load_cart_from_backend():
    """Load cart from backend"""
    try:
        response = make_authenticated_request("GET", "/cart")
        if response and response.get("success"):
            # Convert backend cart format to session state format
            st.session_state.cart = {}
            for item in response.get("items", []):
                product_id = str(item["product_id"])
                st.session_state.cart[product_id] = {
                    'product': {
                        'id': item["product_id"],
                        'name': item["name"],
                        'description': item["description"],
                        'price': item["price"],
                        'stock_quantity': item["stock_quantity"],
                        'image_url': item["image_url"],
                        'category': item["category"],
                        'brand': item["brand"]
                    },
                    'quantity': item["quantity"]
                }
    except Exception as e:
        print(f"Error loading cart from backend: {e}")

def load_favorites_from_backend():
    """Load favorites from backend"""
    try:
        response = make_authenticated_request("GET", "/favorites")
        if response and response.get("success"):
            st.session_state.favorites = set(str(item["product_id"]) for item in response.get("favorites", []))
    except Exception as e:
        print(f"Error loading favorites from backend: {e}")

def sync_cart_to_backend():
    """Sync current session cart to backend"""
    if not st.session_state.logged_in:
        return
    
    try:
        for product_id, item in st.session_state.cart.items():
            make_authenticated_request("POST", "/cart/add", json_data={
                "product_id": int(product_id),
                "quantity": item["quantity"]
            })
    except Exception as e:
        print(f"Error syncing cart to backend: {e}")

def sync_favorites_to_backend():
    """Sync current session favorites to backend"""
    if not st.session_state.logged_in:
        return
    
    try:
        for product_id in st.session_state.favorites:
            make_authenticated_request("POST", f"/favorites/add/{product_id}")
    except Exception as e:
        print(f"Error syncing favorites to backend: {e}")

def add_to_cart(product):
    """Add product to cart"""
    initialize_cart_and_favorites()
    product_id = product.get('id')
    
    if product_id is None:
        st.error("Cannot add product to cart: Invalid product ID")
        return
        
    product_id = str(product_id)
    
    if product_id in st.session_state.cart:
        new_quantity = st.session_state.cart[product_id]['quantity'] + 1
        st.session_state.cart[product_id]['quantity'] = new_quantity
    else:
        st.session_state.cart[product_id] = {
            'product': product,
            'quantity': 1
        }
        new_quantity = 1
    
    # Sync to backend if logged in
    if st.session_state.logged_in:
        try:
            # Sync to cart
            make_authenticated_request("POST", "/cart/add", json_data={
                "product_id": int(product_id),
                "quantity": new_quantity
            })
            # Also sync to temp order for immediate order tracking
            make_authenticated_request("POST", "/orders/temp/add_item", json_data={
                "product_id": int(product_id),
                "quantity": new_quantity
            })
        except Exception as e:
            print(f"Error syncing cart to backend: {e}")

def remove_from_cart(product_id):
    """Remove product from cart"""
    product_id = str(product_id)
    if product_id in st.session_state.cart:
        del st.session_state.cart[product_id]
        
        # Sync to backend if logged in
        if st.session_state.logged_in:
            try:
                # Remove from cart
                make_authenticated_request("DELETE", f"/cart/remove/{product_id}")
                # Also remove from temp order
                make_authenticated_request("POST", "/orders/temp/remove_item", json_data={
                    "product_id": int(product_id)
                })
            except Exception as e:
                print(f"Error removing from cart in backend: {e}")

def update_cart_quantity(product_id, quantity):
    """Update quantity of product in cart"""
    product_id = str(product_id)
    if quantity <= 0:
        remove_from_cart(product_id)
    elif product_id in st.session_state.cart:
        st.session_state.cart[product_id]['quantity'] = quantity
        
        # Sync to backend if logged in
        if st.session_state.logged_in:
            try:
                # Update cart
                make_authenticated_request("POST", "/cart/update", json_data={
                    "product_id": int(product_id),
                    "quantity": quantity
                })
                # Also update temp order
                make_authenticated_request("POST", "/orders/temp/add_item", json_data={
                    "product_id": int(product_id),
                    "quantity": quantity
                })
            except Exception as e:
                print(f"Error updating cart in backend: {e}")

def add_to_favorites(product_id):
    """Add product to favorites"""
    initialize_cart_and_favorites()
    product_id = str(product_id)
    st.session_state.favorites.add(product_id)
    
    # Sync to backend if logged in
    if st.session_state.logged_in:
        try:
            make_authenticated_request("POST", f"/favorites/add/{product_id}")
        except Exception as e:
            print(f"Error syncing favorites to backend: {e}")

def remove_from_favorites(product_id):
    """Remove product from favorites"""
    initialize_cart_and_favorites()
    product_id = str(product_id)
    st.session_state.favorites.discard(product_id)
    
    # Sync to backend if logged in
    if st.session_state.logged_in:
        try:
            make_authenticated_request("DELETE", f"/favorites/remove/{product_id}")
        except Exception as e:
            print(f"Error removing from favorites in backend: {e}")

def toggle_favorite(product_id):
    """Toggle product in favorites"""
    if product_id is None:
        st.error("Cannot toggle favorite: Invalid product ID")
        return False
        
    product_id = str(product_id)
    initialize_cart_and_favorites()
    
    if product_id in st.session_state.favorites:
        remove_from_favorites(product_id)
        return False
    else:
        add_to_favorites(product_id)
        return True

def clear_cart():
    """Clear all items from cart"""
    st.session_state.cart = {}
    
    # Sync to backend if logged in
    if st.session_state.logged_in:
        try:
            # Clear cart
            make_authenticated_request("DELETE", "/cart/clear")
            # Also clear temp order
            make_authenticated_request("DELETE", "/orders/temp")
        except Exception as e:
            print(f"Error clearing cart in backend: {e}")

def get_cart_total():
    """Get total price of items in cart"""
    initialize_cart_and_favorites()
    total = 0
    for item in st.session_state.cart.values():
        total += item['product'].get('price', 0) * item['quantity']
    return total

def get_cart_count():
    """Get total number of items in cart"""
    initialize_cart_and_favorites()
    return sum(item['quantity'] for item in st.session_state.cart.values())

def get_current_customer_info():
    """Get current user's customer information for prefilling forms"""
    if not st.session_state.get('logged_in', False):
        return {}
    
    try:
        response = make_authenticated_request("GET", "/customers/me")
        if response:
            return {
                'name': f"{response.get('first_name', '')} {response.get('last_name', '')}".strip(),
                'first_name': response.get('first_name', ''),
                'last_name': response.get('last_name', ''),
                'email': response.get('email', ''),
                'phone': response.get('phone', ''),
                'address': response.get('address', '')
            }
    except Exception as e:
        print(f"Error fetching customer info: {e}")
    
    return {}

# --- Session Persistence Functions ---
def save_auth_state():
    """Save authentication state to URL parameters for persistence"""
    if st.session_state.logged_in and st.session_state.access_token:
        # Store token in URL params for persistence (encrypted/hashed in production)
        params = dict(st.query_params)
        params["auth_token"] = st.session_state.access_token
        st.query_params.update(params)

def restore_auth_state():
    """Restore authentication state from URL parameters"""
    # Don't restore if user has explicitly logged out
    if st.session_state.get('user_logged_out', False):
        return False
        
    url_params = get_url_params()
    auth_token = url_params.get("auth_token")
    
    if auth_token and not st.session_state.logged_in:
        # Show restoration message
        with st.spinner("🔄 Restoring your session..."):
            # Validate token by making a request to /users/me
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                response = requests.get(f"{API_BASE_URL}/users/me", headers=headers)
                if response.status_code == 200:
                    user_info = response.json()
                    # Restore session state
                    st.session_state.access_token = auth_token
                    st.session_state.logged_in = True
                    st.session_state.current_user = user_info
                    # Clear the logout flag since user is now authenticated again
                    st.session_state.user_logged_out = False
                    
                    # Load cart and favorites from backend
                    load_cart_from_backend()
                    load_favorites_from_backend()
                    
                    # Redirect admin users to admin page if not already there
                    current_page_param = url_params.get("page", "").lower()
                    if (user_info.get('username') == 'admin' or user_info.get('is_admin', False)) and current_page_param != "admin":
                        st.session_state.page = "Admin"
                        st.session_state.main_page_mode = False
                        st.query_params.clear()
                        st.query_params["page"] = "admin"
                    
                    # Show success message briefly
                    st.success(f"✅ Welcome back, {user_info.get('username', 'User')}! Your session has been restored.")
                    time.sleep(1)
                    return True
                else:
                    # Invalid token, remove from URL
                    clean_auth_from_url()
                    st.warning("⚠️ Your session has expired. Please log in again.")
                    return False
            except Exception as e:
                # Error validating token, remove from URL
                clean_auth_from_url()
                st.error("❌ Error restoring session. Please log in again.")
                return False
    return st.session_state.logged_in

def clean_auth_from_url():
    """Remove authentication token and auto_admin from URL"""
    params = dict(st.query_params)
    auth_related_params = ["auth_token", "auto_admin"]
    
    for param in auth_related_params:
        if param in params:
            del params[param]
    
    st.query_params.clear()
    st.query_params.update(params)

def navigate_to(page, section=None):
    """Navigate to a specific page with URL update"""
    params = {"page": page}
    if section:
        params["section"] = section
    # Preserve auth token if logged in
    if st.session_state.logged_in and st.session_state.access_token:
        params["auth_token"] = st.session_state.access_token
    set_url_params(**params)
    st.rerun()

def logout():
    # Set flag to prevent auto-login
    st.session_state.user_logged_out = True
    
    # Clear all authentication-related session state
    st.session_state.logged_in = False
    st.session_state.access_token = None
    st.session_state.current_user = None
    
    # Clear admin login attempt flag to allow future legitimate logins
    if 'admin_login_attempted' in st.session_state:
        del st.session_state['admin_login_attempted']
    
    # Clear cart and favorites data for security
    st.session_state.cart = {}
    st.session_state.favorites = set()
    
    # Reset to shop page after logout
    st.session_state.page = "Shop"
    st.session_state.main_page_mode = True
    st.session_state.user_page = "Shop"
    
    # Reset registration state
    st.session_state.reg_step = 1
    st.session_state.reg_data = {}
    
    # Clear any stored form data for security
    session_keys_to_clear = [
        'login_username', 'login_password', 'register_username', 
        'register_password', 'register_email', 'shipping_name', 
        'shipping_email', 'shipping_address', 'shipping_phone'
    ]
    
    for key in session_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear any message states
    st.session_state.reg_message = {"type": None, "content": None}
    st.session_state.customer_message = {"type": None, "content": None}
    st.session_state.product_message = {"type": None, "content": None}
    st.session_state.order_message = {"type": None, "content": None}
    
    # Completely clear URL and navigate to shop page
    st.query_params.clear()
    st.query_params.update({"page": "shop"})
    
    st.success("👋 Logged out successfully. Your session has been cleared.")
    time.sleep(0.5)  # Brief pause to show the message
    st.rerun()

def confirm_logout():
    """Show logout confirmation dialog"""
    if 'confirm_logout_dialog' not in st.session_state:
        st.session_state.confirm_logout_dialog = False
    
    if st.session_state.confirm_logout_dialog:
        with st.container():
            st.warning("⚠️ Are you sure you want to logout?")
            st.info("This will clear your current session and you'll need to log in again.")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("✅ Yes, Logout", key="confirm_logout_yes"):
                    st.session_state.confirm_logout_dialog = False
                    logout()
            with col2:
                if st.button("❌ Cancel", key="confirm_logout_no"):
                    st.session_state.confirm_logout_dialog = False
                    st.rerun()
            with col3:
                st.empty()  # Spacer
        return True
    return False

# Initialize URL-based navigation
url_params = get_url_params()
current_page = url_params.get("page", ["shop"])[0] if isinstance(url_params.get("page", "shop"), list) else url_params.get("page", "shop")
current_section = url_params.get("section", [None])[0] if isinstance(url_params.get("section", None), list) else url_params.get("section", None)

# --- Helper function for making authenticated API requests ---
def make_authenticated_request(method, endpoint, json_data=None, params=None):
    headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=json_data, headers=headers, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, json=json_data, headers=headers, params=params)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None
        
        if response.status_code in [200, 201, 204]:
            # Handle successful responses (200 OK, 201 Created, 204 No Content)
            if response.status_code == 204:
                return {"success": True}  # For DELETE operations
            else:
                try:
                    return response.json()
                except requests.exceptions.JSONDecodeError:
                    # If response is not JSON, return success indicator
                    return {"success": True, "text": response.text}
        else:
            # Handle error responses
            try:
                error_data = response.json()
                error_message = error_data.get('detail', f'HTTP {response.status_code}')
            except requests.exceptions.JSONDecodeError:
                error_message = f"HTTP {response.status_code}: {response.text}"
            
            st.error(f"API request failed: {error_message}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"🔌 Could not connect to backend at {API_BASE_URL}. Is the server running?")
        return None
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None

# --- Main Page: User-Facing Shop ---
def show_main_shop_page():
    # Initialize cart and favorites first
    initialize_cart_and_favorites()
    
    # Add URL breadcrumb and navigation
    st.markdown(f"**🌐 URL:** `localhost:8501/?page=shop`")
    
    # Session status indicator
    if st.session_state.logged_in:
        st.success(f"🔐 Logged in as: **{st.session_state.current_user.get('username', 'User')}** (Session active)")
    else:
        st.info("🔓 Not logged in - Please log in to access all features")
    
    # Quick navigation bar - different for admin vs regular users
    if is_admin_user():
        # Admin user navigation - show all buttons
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🛍️ Shop", disabled=True):
                pass
        with col2:
            if st.button("📋 Orders", key="shop_admin_orders"):
                navigate_to("admin-orders")
        with col3:
            if st.button("🔧 Admin", key="shop_admin_dashboard"):
                navigate_to("admin")
        with col4:
            if st.button("📦 Products", key="shop_admin_products"):
                navigate_to("products")
        with col5:
            if st.button("👥 Customers", key="shop_admin_customers"):
                navigate_to("customers")
        with col6:
            if st.button("🚪 Logout", key="shop_admin_logout"):
                logout()
    else:
        # Regular user navigation - Shop, Orders, Cart, and Favorites
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("🛍️ Shop", disabled=True):
                pass
        with col2:
            if st.button("📋 My Orders", key="shop_user_orders"):
                navigate_to("orders")
        with col3:
            cart_count = get_cart_count()
            cart_label = f"🛒 Cart ({cart_count})" if cart_count > 0 else "🛒 Cart"
            if st.button(cart_label, key="shop_user_cart"):
                navigate_to("cart")
        with col4:
            fav_count = len(st.session_state.get('favorites', set()))
            fav_label = f"❤️ Favorites ({fav_count})" if fav_count > 0 else "❤️ Favorites"
            if st.button(fav_label, key="shop_user_favorites"):
                navigate_to("favorites")
        with col5:
            if st.button("🚪 Logout", key="shop_user_logout"):
                logout()
    
    st.markdown("---")
    
    st.title("🛍️ Premium Electronics Store")
    st.markdown("## 🌟 Discover Amazing Deals on Top-Quality Products!")
    st.markdown("---")

    # --- Search Area ---
    with st.expander("🔎 Search & Filter Products", expanded=True):
        # First fetch products to get categories
        products = make_authenticated_request("GET", "/products")
        if not products:
            st.info("No products found or failed to load.")
            return
        
        # Get unique categories from products for the filter
        unique_categories = sorted(list(set(p.get("category", "Other") for p in products if p.get("category"))))
        category_options = ["All"] + unique_categories
        
        col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
        with col1:
            search_terms = st.text_input("🔍 Search by name", "", placeholder="Enter product name...")
        with col2:
            stock_filter = st.text_input("📦 Stock filter", "", placeholder="e.g. >10, <5")
        with col3:
            price_filter = st.text_input("💰 Price filter", "", placeholder="e.g. >20, <100")
        with col4:
            category_filter = st.selectbox("🏷️ Category", category_options)

    # --- Filtering Logic ---
    filtered_products = products

    # Category filter
    if category_filter and category_filter != "All":
        category_filter_str = str(category_filter).lower() if category_filter else ""
        filtered_products = [p for p in filtered_products if str(p.get("category", "")).lower() == category_filter_str]

    # Name search (supports multiple terms)
    if search_terms.strip():
        terms = [t.strip().lower() for t in search_terms.split(",") if t.strip()]
        filtered_products = [p for p in filtered_products if any(term in p["name"].lower() for term in terms)]

    # Stock filter
    if stock_filter.strip():
        import re
        m = re.match(r"([<>=]=?|=)\s*(\d+)", stock_filter.strip())
        if m:
            op, val = m.group(1), int(m.group(2))
            if op == ">":
                filtered_products = [p for p in filtered_products if p["stock_quantity"] > val]
            elif op == ">=":
                filtered_products = [p for p in filtered_products if p["stock_quantity"] >= val]
            elif op == "<":
                filtered_products = [p for p in filtered_products if p["stock_quantity"] < val]
            elif op == "<=":
                filtered_products = [p for p in filtered_products if p["stock_quantity"] <= val]
            elif op == "=":
                filtered_products = [p for p in filtered_products if p["stock_quantity"] == val]

    # Price filter
    if price_filter.strip():
        import re
        m = re.match(r"([<>=]=?|=)\s*(\d+(?:\.\d+)?)", price_filter.strip())
        if m:
            op, val = m.group(1), float(m.group(2))
            if op == ">":
                filtered_products = [p for p in filtered_products if p["price"] > val]
            elif op == ">=":
                filtered_products = [p for p in filtered_products if p["price"] >= val]
            elif op == "<":
                filtered_products = [p for p in filtered_products if p["price"] < val]
            elif op == "<=":
                filtered_products = [p for p in filtered_products if p["price"] <= val]
            elif op == "=":
                filtered_products = [p for p in filtered_products if p["price"] == val]

    # --- Show Products Grid ---
    st.markdown("### 🛒 Featured Products")
    if filtered_products:
        # Display products in a responsive grid
        num_cols = 3
        for i in range(0, len(filtered_products), num_cols):
            cols = st.columns(num_cols)
            for j in range(num_cols):
                if i + j < len(filtered_products):
                    product = filtered_products[i + j]
                    with cols[j]:
                        # Streamlit native components for better compatibility
                        with st.container():
                            # Product image with proper validation
                            image_url = product.get('image_url')
                            full_image_url = get_image_url(image_url)
                            
                            if full_image_url:
                                try:
                                    st.image(
                                        full_image_url,
                                        caption=f"{product.get('name', 'Product')}",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    # Fallback to placeholder if image fails to load
                                    st.image(
                                        'https://via.placeholder.com/300x200?text=No+Image',
                                        caption=f"{product.get('name', 'Product')} (Image Error)",
                                        use_container_width=True
                                    )
                            else:
                                # Use placeholder for missing/invalid image URLs
                                st.image(
                                    'https://via.placeholder.com/300x200?text=No+Image',
                                    caption=f"{product.get('name', 'Product')} (No Image)",
                                    use_container_width=True
                                )
                            
                            # Product info
                            st.markdown(f"**{product.get('name', 'Unknown Product')}**")
                            
                            # Category and brand
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"🏷️ {product.get('category', 'General')}")
                            with col2:
                                st.markdown(f"🏢 {product.get('brand', 'Generic')}")
                            
                            # Description
                            description = product.get('description', 'No description available')
                            if len(description) > 100:
                                description = description[:100] + "..."
                            st.markdown(f"*{description}*")
                            
                            # Price and stock
                            price_col, stock_col = st.columns(2)
                            with price_col:
                                st.markdown(f"**💰 ${product.get('price', 0):.2f}**")
                            with stock_col:
                                stock_qty = product.get('stock_quantity', 0)
                                if stock_qty < 10:
                                    st.markdown(f"⚠️ {stock_qty} left")
                                else:
                                    st.markdown(f"✅ {stock_qty} in stock")
                            
                            # Action buttons
                            if st.session_state.logged_in:
                                button_col1, button_col2 = st.columns(2)
                                with button_col1:
                                    product_id = product.get('id', f"unknown_{i}_{j}")
                                    is_favorite = str(product_id) in st.session_state.get('favorites', set())
                                    fav_icon = "❤️" if is_favorite else "🤍"
                                    if st.button(f"{fav_icon} Favorite", key=f"fav_{product_id}_{i}_{j}", use_container_width=True):
                                        if toggle_favorite(product_id):
                                            st.success(f"Added {product.get('name', 'Product')} to favorites!")
                                        else:
                                            st.info(f"Removed {product.get('name', 'Product')} from favorites!")
                                        st.rerun()
                                
                                with button_col2:
                                    if st.button(f"🛒 Add to Cart", key=f"cart_{product_id}_{i}_{j}", use_container_width=True):
                                        add_to_cart(product)
                                        st.success(f"Added {product.get('name', 'Product')} to cart!")
                                        st.rerun()
                            else:
                                # Show login prompt for non-logged in users
                                st.info("🔐 Please log in to add items to cart or favorites")
                            
                            st.markdown("---")
        
        # Show summary stats
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🛍️ Products Found", len(filtered_products))
        with col2:
            avg_price = sum(p.get('price', 0) for p in filtered_products) / len(filtered_products) if filtered_products else 0
            st.metric("💰 Avg Price", f"${avg_price:.2f}")
        with col3:
            total_stock = sum(p.get('stock_quantity', 0) for p in filtered_products)
            st.metric("📦 Total Stock", total_stock)
        with col4:
            categories = len(set(p.get('category', 'Other') for p in filtered_products))
            st.metric("🏷️ Categories", categories)
            
    else:
        st.warning("🔍 No products found matching your search criteria.")
        st.info("💡 **Try adjusting your filters or search terms to find what you're looking for!**")


# --- User Navigation ---
if 'main_page_mode' not in st.session_state:
    st.session_state.main_page_mode = True
if 'user_page' not in st.session_state:
    st.session_state.user_page = "Shop"

def sync_cart_to_temp_order():
    """Sync current cart items to temp order"""
    if not st.session_state.logged_in or not st.session_state.cart:
        return
    
    try:
        # First clear any existing temp order to ensure clean sync
        make_authenticated_request("DELETE", "/orders/temp")
        
        # Add all cart items to temp order
        for product_id, item in st.session_state.cart.items():
            result = make_authenticated_request("POST", "/orders/temp/add_item", json_data={
                "product_id": int(product_id),
                "quantity": item["quantity"]
            })
            # Debug info removed - sync happens silently in background
    except Exception as e:
        st.error(f"Error syncing cart to temp order: {e}")
        print(f"Error syncing cart to temp order: {e}")

def show_user_orders_page():
    # Initialize cart and favorites first
    initialize_cart_and_favorites()
    
    # Add URL breadcrumb and navigation
    st.markdown(f"**🌐 URL:** `localhost:8501/?page=orders`")
    
    # Quick navigation bar - different for admin vs regular users
    if is_admin_user():
        # Admin user navigation - show all buttons
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🛍️ Shop", key="orders_admin_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 Orders", disabled=True):
                pass
        with col3:
            if st.button("🔧 Admin", key="orders_admin_dashboard"):
                navigate_to("admin")
        with col4:
            if st.button("📦 Products", key="orders_admin_products"):
                navigate_to("products")
        with col5:
            if st.button("👥 Customers", key="orders_admin_customers"):
                navigate_to("customers")
        with col6:
            if st.button("🚪 Logout", key="orders_admin_logout"):
                logout()
    else:
        # Regular user navigation - Shop, Orders, Cart, and Favorites
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("🛍️ Shop", key="orders_user_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 My Orders", disabled=True):
                pass
        with col3:
            cart_count = get_cart_count()
            cart_label = f"🛒 Cart ({cart_count})" if cart_count > 0 else "🛒 Cart"
            if st.button(cart_label, key="orders_user_cart"):
                navigate_to("cart")
        with col4:
            fav_count = len(st.session_state.get('favorites', set()))
            fav_label = f"❤️ Favorites ({fav_count})" if fav_count > 0 else "❤️ Favorites"
            if st.button(fav_label, key="orders_user_favorites"):
                navigate_to("favorites")
        with col5:
            if st.button("🚪 Logout", key="orders_user_logout"):
                logout()
    
    st.markdown("---")
    
    st.title("🧾 My Orders")
    if not st.session_state.logged_in:
        st.info("Please log in to view your orders.")
        return
    
    # Sync cart items to temp order when viewing orders
    sync_cart_to_temp_order()
    
    st.markdown("---")
    st.write("Below are your pending (TEMP) and completed orders. Pending orders can be managed and purchased.")
    
    # Add manual sync button for debugging
    cart_count = get_cart_count()
    if cart_count > 0:
        if st.button(f"🔄 Sync {cart_count} cart items to pending order"):
            sync_cart_to_temp_order()
            st.success("Cart items synced to pending order!")
            st.rerun()

    # --- Fetch user orders using user-specific endpoint ---
    # Add cache busting to ensure fresh data after purchase
    import time
    cache_buster = int(time.time())
    user_orders = make_authenticated_request("GET", f"/orders/user?_t={cache_buster}")
    
    # Separate TEMP and other orders (do this before debug section)
    if user_orders:
        temp_orders = [o for o in user_orders if o.get("status", "").upper() == "TEMP"]
        completed_orders = [o for o in user_orders if o.get("status", "").upper() in ["CLOSE", "PENDING", "PROCESSING", "SHIPPED", "DELIVERED"]]
    else:
        temp_orders = []
        completed_orders = []
    
    if not user_orders:
        st.info("You have no orders yet.")
        return

    # --- Show TEMP order (pending) ---
    if temp_orders:
        st.markdown("### 🟡 Pending Order (TEMP)")
        temp_order = temp_orders[0]  # Only one TEMP order per user
        
        # Show customer shipping info with edit option
        customer_info = temp_order.get('customer_info', {})
        st.write(f"**Order ID:** {temp_order['id']} | **Created:** {temp_order.get('order_date', '')}")
        
        # Shipping Information Section
        st.markdown("#### 📦 Shipping Information")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Editable shipping information
            shipping_name = st.text_input("Ship to Name", 
                                        value=customer_info.get('name', ''), 
                                        key="edit_shipping_name")
            shipping_address = st.text_area("Shipping Address", 
                                          value=customer_info.get('address', ''), 
                                          key="edit_shipping_address",
                                          height=80)
            shipping_phone = st.text_input("Phone Number", 
                                         value=customer_info.get('phone', ''), 
                                         key="edit_shipping_phone")
        
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("💾 Update Shipping", key="update_shipping", use_container_width=True):
                # Parse the name field
                name_parts = shipping_name.split(' ', 1)
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                
                shipping_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": shipping_phone,
                    "address": shipping_address
                }
                
                result = make_authenticated_request("PUT", "/customers/me/shipping", shipping_data)
                if result and result.get("success"):
                    st.success("Shipping information updated!")
                    st.rerun()
                else:
                    st.error("Failed to update shipping information.")
        
        st.write(f"**Total Price:** ${temp_order['total_amount']:.2f}")
        st.write("**Items:**")
        items = temp_order.get("items", [])
        # --- Add/Remove/Update Items ---
        products = make_authenticated_request("GET", "/products") or []
        product_lookup = {p["id"]: p for p in products}
        # Show editable table for items
        if items:
            for idx, item in enumerate(items):
                col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
                with col1:
                    prod = product_lookup.get(item["product_id"])
                    prod_name = prod["name"] if prod else f"ID {item['product_id']}"
                    st.write(f"{prod_name}")
                with col2:
                    max_qty = prod["stock_quantity"] if prod else 100
                    new_qty = st.number_input(f"Qty for {item['product_id']}", min_value=1, max_value=max_qty, value=item["quantity"], key=f"edit_qty_{item['product_id']}")
                with col3:
                    st.write(f"${item['price_at_order']:.2f}")
                with col4:
                    if st.button("Remove", key=f"remove_item_{item['product_id']}"):
                        # Remove item from order
                        result = make_authenticated_request("POST", "/orders/temp/remove_item", 
                                                          json_data={"product_id": item["product_id"]})
                        if result and result.get("success"):
                            st.success("Item removed successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to remove item.")
                # If quantity changed, update
                if new_qty != item["quantity"]:
                    result = make_authenticated_request("POST", "/orders/temp/add_item", 
                                                      json_data={"product_id": item["product_id"], "quantity": new_qty})
                    if result and result.get("success"):
                        st.success("Quantity updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update quantity.")
            st.markdown("---")
        else:
            st.info("No items in this order yet.")
        # Add new item
        st.markdown("#### Add Product to Order")
        add_prod_options = [f"{p['name']} (Stock: {p['stock_quantity']})" for p in products if p["stock_quantity"] > 0]
        if add_prod_options:
            selected = st.selectbox("Select product to add", add_prod_options, key="add_prod_select")
            selected_prod = next((p for p in products if f"{p['name']} (Stock: {p['stock_quantity']})" == selected), None)
            add_qty = st.number_input("Quantity", min_value=1, max_value=selected_prod["stock_quantity"] if selected_prod else 1, value=1, key="add_prod_qty")
            if st.button("Add to Order"):
                if selected_prod:
                    result = make_authenticated_request("POST", "/orders/temp/add_item", 
                                                      json_data={"product_id": selected_prod["id"], "quantity": add_qty})
                    if result and result.get("success"):
                        st.success("Product added to order!")
                        st.rerun()
                    else:
                        st.error("Failed to add product to order.")
        else:
            st.info("No products available to add.")
        # Purchase and Delete buttons
        colA, colB = st.columns(2)
        with colA:
            if st.button("🛒 Purchase Order (Close)", use_container_width=True, type="primary"):
                with st.spinner("Processing purchase..."):
                    # Show cart status before purchase
                    cart_count_before = get_cart_count()
                    st.write(f"Debug: Cart items before purchase: {cart_count_before}")
                    
                    result = make_authenticated_request("POST", "/orders/temp/close")
                    if result and result.get("success"):
                        st.success("🎉 Order purchased successfully!")
                        
                        # Clear both session cart and backend cart since order is completed
                        st.session_state.cart = {}
                        try:
                            cart_clear_result = make_authenticated_request("DELETE", "/cart/clear")
                            st.write(f"Debug: Backend cart clear result: {cart_clear_result}")
                        except Exception as e:
                            print(f"Error clearing backend cart: {e}")
                            st.error(f"Error clearing backend cart: {e}")
                        
                        # Show cart status after purchase
                        cart_count_after = get_cart_count()
                        st.write(f"Debug: Cart items after purchase: {cart_count_after}")
                        
                        # Add a small delay to ensure database transaction is complete
                        import time
                        time.sleep(0.5)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Failed to purchase order. Please try again.")
                        if result:
                            st.error(f"Error details: {result}")
        with colB:
            if st.button("🗑️ Delete Pending Order", use_container_width=True):
                with st.spinner("Deleting order..."):
                    # Show cart status before deletion
                    cart_count_before = get_cart_count()
                    st.write(f"Debug: Cart items before deletion: {cart_count_before}")
                    
                    result = make_authenticated_request("DELETE", "/orders/temp")
                    if result and result.get("success"):
                        st.success("🗑️ Order deleted successfully!")
                        # Clear both session cart and backend cart
                        st.session_state.cart = {}
                        # Also clear backend cart to keep everything in sync
                        try:
                            cart_clear_result = make_authenticated_request("DELETE", "/cart/clear")
                            st.write(f"Debug: Backend cart clear result: {cart_clear_result}")
                        except Exception as e:
                            print(f"Error clearing backend cart: {e}")
                            st.error(f"Error clearing backend cart: {e}")
                        
                        # Show cart status after deletion
                        cart_count_after = get_cart_count()
                        st.write(f"Debug: Cart items after deletion: {cart_count_after}")
                        
                        # Add a small delay to ensure database transaction is complete
                        import time
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete order.")
                        if result:
                            st.error(f"Error details: {result}")
    else:
        st.info("No pending (TEMP) order found.")
        
        # Show helpful message about cart-to-order relationship
        cart_count = get_cart_count()
        if cart_count > 0:
            st.info(f"💡 You have {cart_count} items in your cart. Items in your cart are automatically added to pending orders. You can view and manage them in your cart, then checkout to complete the purchase.")
            if st.button("🛒 Go to Cart", use_container_width=True):
                navigate_to("cart")
        else:
            st.info("💡 Add items to your cart from the shop to create pending orders.")
            if st.button("🛍️ Go Shopping", use_container_width=True):
                navigate_to("shop")

    # --- Show completed orders ---
    if completed_orders:
        st.markdown("### 🟢 Completed Orders")
        for order in completed_orders:
            status_icon = "✅" if order.get('status', '').upper() == "CLOSE" else "📦"
            customer_info = order.get('customer_info', {})
            with st.expander(f"{status_icon} Order #{order['id']} | {order.get('order_date', '')} | Total: ${order['total_amount']:.2f}"):
                st.write(f"**Status:** {order.get('status', '').capitalize()}")
                st.write(f"**Shipped to:** {customer_info.get('name', 'N/A')}")
                st.write(f"**Address:** {customer_info.get('address', 'Not provided')}")
                st.write(f"**Phone:** {customer_info.get('phone', 'Not provided')}")
                st.write("**Items:**")
                items = order.get("items", [])
                if items:
                    df = pd.DataFrame(items)[["product_id", "quantity", "price_at_order"]]
                    df = df.rename(columns={"product_id": "Product ID", "quantity": "Quantity", "price_at_order": "Price at Order"})
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No items in this order.")
    else:
        st.info("No completed orders found.")

def show_cart_page():
    """Display the shopping cart page"""
    initialize_cart_and_favorites()
    
    # Add URL breadcrumb and navigation
    st.markdown(f"**🌐 URL:** `localhost:8501/?page=cart`")
    
    # Quick navigation bar
    if is_admin_user():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        with col1:
            if st.button("🛍️ Shop", key="cart_admin_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 Orders", key="cart_admin_orders"):
                navigate_to("admin-orders")
        with col3:
            if st.button("🛒 Cart", disabled=True):
                pass
        with col4:
            if st.button("❤️ Favorites", key="cart_admin_favorites"):
                navigate_to("favorites")
        with col5:
            if st.button("🔧 Admin", key="cart_admin_dashboard"):
                navigate_to("admin")
        with col6:
            if st.button("📦 Products", key="cart_admin_products"):
                navigate_to("products")
        with col7:
            if st.button("👥 Customers", key="cart_admin_customers"):
                navigate_to("customers")
        with col8:
            if st.button("🚪 Logout", key="cart_admin_logout"):
                logout()
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("🛍️ Shop", key="cart_user_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 My Orders", key="cart_user_orders"):
                navigate_to("orders")
        with col3:
            if st.button("🛒 Cart", disabled=True):
                pass
        with col4:
            if st.button("❤️ Favorites", key="cart_user_favorites"):
                navigate_to("favorites")
        with col5:
            if st.button("🚪 Logout", key="cart_user_logout"):
                logout()
    
    st.markdown("---")
    
    st.title("🛒 Shopping Cart")
    
    if not st.session_state.logged_in:
        st.info("Please log in to view your cart.")
        return
    
    cart_count = get_cart_count()
    cart_total = get_cart_total()
    
    if cart_count == 0:
        st.info("Your cart is empty. Go shopping!")
        if st.button("🛍️ Continue Shopping", use_container_width=True):
            navigate_to("shop")
        return
    
    st.markdown(f"**Items in cart:** {cart_count} | **Total:** ${cart_total:.2f}")
    st.markdown("---")
    
    # Display cart items
    for product_id, item in st.session_state.cart.items():
        product = item['product']
        quantity = item['quantity']
        
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([0.3, 0.3, 0.15, 0.15, 0.1])
            
            with col1:
                # Product image and info
                image_url = get_image_url(product.get('image_url', ''))
                if image_url:
                    st.image(image_url, width=100)
                else:
                    st.markdown("📷 No Image")
            
            with col2:
                st.markdown(f"**{product.get('name', 'Unknown Product')}**")
                st.markdown(f"Price: ${product.get('price', 0):.2f}")
                st.markdown(f"Subtotal: ${product.get('price', 0) * quantity:.2f}")
            
            with col3:
                new_quantity = st.number_input(
                    "Qty", 
                    min_value=1, 
                    max_value=product.get('stock_quantity', 100),
                    value=quantity,
                    key=f"cart_qty_{product_id}"
                )
                if new_quantity != quantity:
                    update_cart_quantity(product_id, new_quantity)
                    st.rerun()
            
            with col4:
                st.write("")  # Spacer
                if st.button("🗑️ Remove", key=f"remove_cart_{product_id}"):
                    remove_from_cart(product_id)
                    st.rerun()
            
            with col5:
                # Add to favorites button
                is_favorite = product_id in st.session_state.favorites
                fav_icon = "❤️" if is_favorite else "🤍"
                if st.button(fav_icon, key=f"cart_fav_{product_id}"):
                    toggle_favorite(product_id)
                    st.rerun()
            
            st.markdown("---")
    
    # Checkout section
    st.markdown("### 💳 Checkout")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Order Summary:**")
        st.markdown(f"Items: {cart_count}")
        st.markdown(f"Subtotal: ${cart_total:.2f}")
        st.markdown(f"Tax (8%): ${cart_total * 0.08:.2f}")
        st.markdown(f"**Total: ${cart_total * 1.08:.2f}**")
    
    with col2:
        st.markdown("**Shipping Information:**")
        # Get customer information for prefilling
        customer_info = get_current_customer_info()
        
        shipping_name = st.text_input("Full Name", value=customer_info.get('name', ''), key="shipping_name")
        shipping_email = st.text_input("Email", value=customer_info.get('email', ''), key="shipping_email")
        shipping_address = st.text_area("Address", value=customer_info.get('address', ''), key="shipping_address")
        shipping_phone = st.text_input("Phone", value=customer_info.get('phone', ''), key="shipping_phone")
    
    # Checkout buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🛍️ Continue Shopping", use_container_width=True):
            navigate_to("shop")
    
    with col2:
        if st.button("🗑️ Clear Cart", use_container_width=True):
            clear_cart()
            st.success("Cart cleared!")
            st.rerun()
    
    with col3:
        if shipping_name and shipping_address and shipping_phone and shipping_email:
            if st.button("✅ Place Order", use_container_width=True):
                try:
                    # Create order via backend API
                    with st.spinner("Processing your order..."):
                        # Add all cart items to a TEMP order (creates order if none exists)
                        order_created = False
                        for product_id, item in st.session_state.cart.items():
                            add_item_response = make_authenticated_request(
                                "POST", 
                                "/orders/temp/add_item",
                                json_data={
                                    "product_id": int(product_id),
                                    "quantity": item["quantity"]
                                }
                            )
                            if add_item_response and add_item_response.get("success"):
                                order_created = True
                            else:
                                st.error(f"Failed to add {item['product']['name']} to order")
                                return
                        
                        if order_created:
                            # Close the order (complete the purchase)
                            close_order_response = make_authenticated_request("POST", "/orders/temp/close")
                            
                            if close_order_response and close_order_response.get("success"):
                                # Clear cart after successful order
                                clear_cart()
                                st.success("🎉 Order placed successfully! Thank you for your purchase!")
                                st.info(f"📦 Order details:\n- Name: {shipping_name}\n- Email: {shipping_email}\n- Address: {shipping_address}\n- Phone: {shipping_phone}")
                                st.balloons()
                                time.sleep(3)
                                navigate_to("orders")
                            else:
                                st.error("Failed to complete the order. Please try again.")
                        else:
                            st.error("Failed to create order. Please try again.")
                            
                except Exception as e:
                    st.error(f"An error occurred while processing your order: {str(e)}")
        else:
            st.button("✅ Place Order", disabled=True, use_container_width=True, help="Please fill in all shipping information")

def show_favorites_page():
    """Display the favorites page"""
    initialize_cart_and_favorites()
    
    # Add URL breadcrumb and navigation
    st.markdown(f"**🌐 URL:** `localhost:8501/?page=favorites`")
    
    # Quick navigation bar
    if is_admin_user():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        with col1:
            if st.button("🛍️ Shop", key="fav_admin_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 Orders", key="fav_admin_orders"):
                navigate_to("admin-orders")
        with col3:
            if st.button("🛒 Cart", key="fav_admin_cart"):
                navigate_to("cart")
        with col4:
            if st.button("❤️ Favorites", disabled=True):
                pass
        with col5:
            if st.button("🔧 Admin", key="fav_admin_dashboard"):
                navigate_to("admin")
        with col6:
            if st.button("📦 Products", key="fav_admin_products"):
                navigate_to("products")
        with col7:
            if st.button("👥 Customers", key="fav_admin_customers"):
                navigate_to("customers")
        with col8:
            if st.button("🚪 Logout", key="fav_admin_logout"):
                logout()
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("🛍️ Shop", key="fav_user_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 My Orders", key="fav_user_orders"):
                navigate_to("orders")
        with col3:
            if st.button("🛒 Cart", key="fav_user_cart"):
                navigate_to("cart")
        with col4:
            if st.button("❤️ Favorites", disabled=True):
                pass
        with col5:
            if st.button("🚪 Logout", key="fav_user_logout"):
                logout()
    
    st.markdown("---")
    
    st.title("❤️ My Favorites")
    
    if not st.session_state.logged_in:
        st.info("Please log in to view your favorites.")
        return
    
    if not st.session_state.favorites:
        st.info("You haven't added any favorites yet. Start shopping to add some!")
        if st.button("🛍️ Go Shopping", use_container_width=True):
            navigate_to("shop")
        return
    
    # Get all products to display favorites
    products = make_authenticated_request("GET", "/products")
    if not products:
        st.info("Failed to load products.")
        return
    
    # Filter products to show only favorites
    favorite_products = [p for p in products if str(p.get('id')) in st.session_state.favorites]
    
    if not favorite_products:
        st.info("Your favorite products are no longer available.")
        return
    
    st.markdown(f"**You have {len(favorite_products)} favorite products:**")
    st.markdown("---")
    
    # Display favorite products in a grid
    cols_per_row = 3
    for i in range(0, len(favorite_products), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(favorite_products):
                product = favorite_products[i + j]
                with cols[j]:
                    # Product card
                    with st.container():
                        st.markdown("### " + product.get('name', 'Unknown Product'))
                        
                        # Product image
                        image_url = get_image_url(product.get('image_url', ''))
                        if image_url:
                            st.image(image_url, use_container_width=True)
                        else:
                            st.markdown("📷 **No Image Available**")
                        
                        # Product details
                        category = product.get('category', 'Uncategorized')
                        st.markdown(f"**📂 Category:** {category}")
                        
                        description = product.get('description', 'No description available.')
                        if len(description) > 100:
                            description = description[:100] + "..."
                        st.markdown(f"*{description}*")
                        
                        # Price and stock
                        price_col, stock_col = st.columns(2)
                        with price_col:
                            st.markdown(f"**💰 ${product.get('price', 0):.2f}**")
                        with stock_col:
                            stock_qty = product.get('stock_quantity', 0)
                            if stock_qty < 10:
                                st.markdown(f"⚠️ {stock_qty} left")
                            else:
                                st.markdown(f"✅ {stock_qty} in stock")
                        
                        # Action buttons
                        button_col1, button_col2 = st.columns(2)
                        with button_col1:
                            if st.button(f"🛒 Add to Cart", key=f"fav_cart_{product.get('id')}", use_container_width=True):
                                add_to_cart(product)
                                st.success(f"Added {product.get('name', 'Product')} to cart!")
                                st.rerun()
                        
                        with button_col2:
                            if st.button(f"💔 Remove", key=f"fav_remove_{product.get('id')}", use_container_width=True):
                                remove_from_favorites(product.get('id'))
                                st.info(f"Removed {product.get('name', 'Product')} from favorites!")
                                st.rerun()
                        
                        st.markdown("---")

def show_chat_assistant_page():
    """Display the chat assistant page"""
    initialize_cart_and_favorites()
    
    # Add URL breadcrumb and navigation
    st.markdown(f"**🌐 URL:** `localhost:8501/?page=chat`")
    
    # Quick navigation bar
    if is_admin_user():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        with col1:
            if st.button("🛍️ Shop", key="chat_admin_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 Orders", key="chat_admin_orders"):
                navigate_to("admin-orders")
        with col3:
            if st.button("🛒 Cart", key="chat_admin_cart"):
                navigate_to("cart")
        with col4:
            if st.button("❤️ Favorites", key="chat_admin_favorites"):
                navigate_to("favorites")
        with col5:
            if st.button("🔧 Admin", key="chat_admin_dash"):
                navigate_to("admin")
        with col6:
            if st.button("👥 Customers", key="chat_admin_customers"):
                navigate_to("customers")
        with col7:
            if st.button("📦 Products", key="chat_admin_products"):
                navigate_to("products")
        with col8:
            if st.button("👤 Users", key="chat_admin_users"):
                navigate_to("users")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("🛍️ Shop", key="chat_user_shop"):
                navigate_to("shop")
        with col2:
            if st.button("📋 My Orders", key="chat_user_orders"):
                navigate_to("orders")
        with col3:
            if st.button("🛒 Cart", key="chat_user_cart"):
                navigate_to("cart")
        with col4:
            if st.button("❤️ Favorites", key="chat_user_favorites"):
                navigate_to("favorites")
    
    st.markdown("---")
    
    # Page header
    st.title("🤖 AI Shopping Assistant")
    st.markdown("**Powered by ChatGPT** - I know everything about you, your orders, and our products! Ask me anything!")
    
    # Show API status
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # Show partial key for security (only first 7 and last 4 characters)
        masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
        st.success(f"✅ Connected to ChatGPT API - Key: {masked_key}")
    else:
        st.warning("⚠️ OpenAI API key not set - Using enhanced fallback system. Set OPENAI_API_KEY environment variable for full ChatGPT integration.")
    
    # Initialize chat session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'chat_prompts_used' not in st.session_state:
        st.session_state.chat_prompts_used = 0
    
    # Prompt limit information
    max_prompts = 5
    prompts_remaining = max_prompts - st.session_state.chat_prompts_used
    
    if prompts_remaining > 0:
        st.success(f"You have **{prompts_remaining}** questions remaining in this session.")
    else:
        st.error("You have used all your questions for this session. Please refresh the page to start a new session.")
    
    # Get comprehensive context
    with st.spinner("Gathering your profile and store data..."):
        context = get_comprehensive_context()
    
    # Show user context summary
    user_info = context.get('user_info', {})
    if user_info:
        with st.expander("📊 What I know about you", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Orders", user_info.get('total_orders', 0))
                st.metric("Total Spent", f"${user_info.get('total_spent', 0):.2f}")
            with col2:
                st.metric("Cart Items", user_info.get('cart_items', 0))
                st.metric("Favorites", user_info.get('favorite_items', 0))
            with col3:
                st.metric("Pending Orders", user_info.get('pending_orders', 0))
                st.metric("Completed Orders", user_info.get('completed_orders', 0))
    
    # Show store context summary
    store_stats = context.get('store_stats', {})
    if store_stats:
        with st.expander("🏪 Store Information I Have Access To", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Products", store_stats.get('total_products', 0))
                st.metric("In Stock", store_stats.get('in_stock', 0))
            with col2:
                st.metric("Categories", len(store_stats.get('categories', [])))
                st.metric("Avg Price", f"${store_stats.get('price_range', {}).get('avg', 0):.2f}")
            with col3:
                price_range = store_stats.get('price_range', {})
                st.metric("Price Range", f"${price_range.get('min', 0):.2f} - ${price_range.get('max', 0):.2f}")
    
    # Example questions based on user context
    st.markdown("### 💡 Try asking me:")
    example_questions = [
        "What products would you recommend for me?",
        "How much have I spent so far?",
        "What's in my cart and favorites?",
        "Show me products similar to my previous orders",
        "What's the cheapest laptop you have in stock?",
        "Compare your gaming products for me",
    ]
    
    # Add personalized examples based on user data
    if user_info.get('total_orders', 0) > 0:
        example_questions.append("Analyze my buying pattern")
    if user_info.get('cart_items', 0) > 0:
        example_questions.append("Should I buy what's in my cart?")
    
    for i, question in enumerate(example_questions[:6], 1):
        st.markdown(f"{i}. *{question}*")
    
    # Display chat history
    st.markdown("### 💬 Chat History")
    if st.session_state.chat_messages:
        for i, message in enumerate(st.session_state.chat_messages):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(message["content"], unsafe_allow_html=True)
    else:
        st.info("👋 Start a conversation! I have access to your complete profile, order history, and our entire product catalog.")
    
    # Chat input
    if prompts_remaining > 0:
        user_question = st.chat_input("Ask me anything about products, your account, recommendations, etc.")
        
        if user_question:
            # Add user message to chat
            st.session_state.chat_messages.append({"role": "user", "content": user_question})
            st.session_state.chat_prompts_used += 1
            
            # Generate AI response with full context
            with st.spinner("🤖 Thinking... (analyzing your profile and product catalog)"):
                try:
                    ai_response = generate_chatgpt_response(user_question, context)
                    st.session_state.chat_messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    error_response = f"I'm sorry, I encountered an error processing your question: {str(e)}. Please try again."
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_response})
            
            st.rerun()
    
    # Clear chat button and reset session
    if st.session_state.chat_messages or st.session_state.chat_prompts_used > 0:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_messages = []
                st.rerun()
        with col2:
            if st.button("🔄 Reset Session (New 5 Questions)"):
                st.session_state.chat_messages = []
                st.session_state.chat_prompts_used = 0
                st.success("Session reset! You now have 5 new questions.")
                st.rerun()

def get_comprehensive_context():
    """Gather comprehensive context about the current user and store"""
    context = {
        'user_info': {},
        'products': [],
        'orders': [],
        'cart': {},
        'favorites': [],
        'store_stats': {}
    }
    
    try:
        # Get current user info
        if st.session_state.get('logged_in', False):
            current_user = st.session_state.get('current_user', {})
            context['user_info'] = {
                'username': current_user.get('username', 'Unknown'),
                'email': current_user.get('email', 'N/A'),
                'is_admin': current_user.get('is_admin', False)
            }
            
            # Get customer information
            try:
                customer_info = make_authenticated_request("GET", "/customers/me")
                if customer_info:
                    context['user_info'].update({
                        'first_name': customer_info.get('first_name', ''),
                        'last_name': customer_info.get('last_name', ''),
                        'phone': customer_info.get('phone', ''),
                        'address': customer_info.get('address', ''),
                        'customer_since': customer_info.get('created_at', '')
                    })
            except:
                pass
            
            # Get user's order history
            try:
                orders = make_authenticated_request("GET", "/orders/user")
                if orders:
                    context['orders'] = orders
                    # Calculate order statistics
                    total_orders = len(orders)
                    total_spent = sum(float(order.get('total_amount', 0)) for order in orders)
                    pending_orders = [o for o in orders if o.get('status') == 'TEMP']
                    completed_orders = [o for o in orders if o.get('status') == 'CLOSE']
                    
                    context['user_info'].update({
                        'total_orders': total_orders,
                        'total_spent': total_spent,
                        'pending_orders': len(pending_orders),
                        'completed_orders': len(completed_orders)
                    })
            except:
                pass
            
            # Get current cart
            try:
                cart_data = make_authenticated_request("GET", "/cart")
                if cart_data:
                    context['cart'] = cart_data
                    cart_total = sum(item.get('quantity', 0) * item.get('product', {}).get('price', 0) for item in cart_data)
                    context['user_info']['cart_items'] = len(cart_data)
                    context['user_info']['cart_total'] = cart_total
            except:
                context['cart'] = st.session_state.get('cart', {})
                context['user_info']['cart_items'] = len(context['cart'])
            
            # Get favorites
            try:
                favorites_data = make_authenticated_request("GET", "/favorites")
                if favorites_data:
                    context['favorites'] = favorites_data
                    context['user_info']['favorite_items'] = len(favorites_data)
            except:
                context['favorites'] = list(st.session_state.get('favorites', set()))
                context['user_info']['favorite_items'] = len(context['favorites'])
        
        # Get all products
        try:
            products = make_authenticated_request("GET", "/products")
            if products:
                context['products'] = products
                
                # Calculate store statistics
                total_products = len(products)
                in_stock_products = [p for p in products if p.get('stock_quantity', 0) > 0]
                out_of_stock_products = [p for p in products if p.get('stock_quantity', 0) == 0]
                categories = list(set(p.get('category', 'Unknown') for p in products))
                
                prices = [float(p.get('price', 0)) for p in products if p.get('price')]
                avg_price = sum(prices) / len(prices) if prices else 0
                min_price = min(prices) if prices else 0
                max_price = max(prices) if prices else 0
                
                context['store_stats'] = {
                    'total_products': total_products,
                    'in_stock': len(in_stock_products),
                    'out_of_stock': len(out_of_stock_products),
                    'categories': categories,
                    'price_range': {'min': min_price, 'max': max_price, 'avg': avg_price}
                }
        except:
            context['products'] = []
        
        # Get all orders (admin only) for store insights
        if context['user_info'].get('is_admin', False):
            try:
                all_orders = make_authenticated_request("GET", "/orders")
                if all_orders:
                    total_revenue = sum(float(order.get('total_amount', 0)) for order in all_orders)
                    context['store_stats']['total_orders'] = len(all_orders)
                    context['store_stats']['total_revenue'] = total_revenue
            except:
                pass
    
    except Exception as e:
        print(f"Error gathering context: {e}")
    
    return context

def create_chat_prompt(user_question, context):
    """Create a comprehensive prompt for ChatGPT with full context"""
    
    user_info = context.get('user_info', {})
    products = context.get('products', [])
    orders = context.get('orders', [])
    cart = context.get('cart', {})
    favorites = context.get('favorites', [])
    store_stats = context.get('store_stats', {})
    
    # Build user profile
    user_profile = f"""
USER PROFILE:
- Name: {user_info.get('first_name', '')} {user_info.get('last_name', '')} ({user_info.get('username', 'Guest')})
- Email: {user_info.get('email', 'N/A')}
- Phone: {user_info.get('phone', 'N/A')}
- Address: {user_info.get('address', 'N/A')}
- Customer since: {user_info.get('customer_since', 'N/A')}
- Total orders: {user_info.get('total_orders', 0)}
- Total spent: ${user_info.get('total_spent', 0):.2f}
- Pending orders: {user_info.get('pending_orders', 0)}
- Completed orders: {user_info.get('completed_orders', 0)}
- Items in cart: {user_info.get('cart_items', 0)}
- Cart total: ${user_info.get('cart_total', 0):.2f}
- Favorite items: {user_info.get('favorite_items', 0)}
- Account type: {'Admin' if user_info.get('is_admin') else 'Customer'}
"""
    
    # Build product catalog
    product_catalog = "PRODUCT CATALOG:\n"
    for i, product in enumerate(products[:20], 1):  # Limit to first 20 for token efficiency
        stock_status = "In Stock" if product.get('stock_quantity', 0) > 0 else "Out of Stock"
        product_catalog += f"{i}. {product.get('name', 'Unknown')} - ${product.get('price', 0):.2f} - {product.get('category', 'Unknown')} - Stock: {product.get('stock_quantity', 0)} ({stock_status})\n"
    
    if len(products) > 20:
        product_catalog += f"... and {len(products) - 20} more products\n"
    
    # Build order history
    order_history = "USER'S ORDER HISTORY:\n"
    if orders:
        for i, order in enumerate(orders[-5:], 1):  # Last 5 orders
            order_history += f"{i}. Order #{order.get('id')} - ${order.get('total_amount', 0):.2f} - {order.get('status')} - {order.get('order_date', '')}\n"
            items = order.get('items', [])
            for item in items:
                order_history += f"   • Product ID {item.get('product_id')} - Qty: {item.get('quantity')} - ${item.get('price_at_order', 0):.2f}\n"
    else:
        order_history += "No previous orders\n"
    
    # Build current cart
    current_cart = "CURRENT CART:\n"
    if isinstance(cart, list) and cart:
        for item in cart:
            product = item.get('product', {})
            current_cart += f"• {product.get('name', 'Unknown')} - Qty: {item.get('quantity', 0)} - ${product.get('price', 0):.2f}\n"
    elif isinstance(cart, dict) and cart:
        for product_id, item in cart.items():
            product = item.get('product', {})
            current_cart += f"• {product.get('name', 'Unknown')} - Qty: {item.get('quantity', 0)} - ${product.get('price', 0):.2f}\n"
    else:
        current_cart += "Cart is empty\n"
    
    # Build store statistics
    store_info = f"""
STORE STATISTICS:
- Total products: {store_stats.get('total_products', 0)}
- In stock: {store_stats.get('in_stock', 0)}
- Out of stock: {store_stats.get('out_of_stock', 0)}
- Categories: {', '.join(store_stats.get('categories', []))}
- Price range: ${store_stats.get('price_range', {}).get('min', 0):.2f} - ${store_stats.get('price_range', {}).get('max', 0):.2f}
- Average price: ${store_stats.get('price_range', {}).get('avg', 0):.2f}
"""
    
    if user_info.get('is_admin'):
        store_info += f"- Total store orders: {store_stats.get('total_orders', 'N/A')}\n"
        store_info += f"- Total revenue: ${store_stats.get('total_revenue', 0):.2f}\n"
    
    # Create the complete prompt
    system_prompt = f"""You are a helpful shopping assistant for an electronics e-commerce store. You have complete access to the user's profile, order history, current cart, and the entire product catalog.

{user_profile}

{product_catalog}

{order_history}

{current_cart}

{store_info}

INSTRUCTIONS:
1. Be helpful, friendly, and knowledgeable about the products and user's history
2. Make personalized recommendations based on their purchase history and preferences
3. Reference specific products by name and price from the catalog
4. Help with product comparisons, stock availability, and purchasing decisions
5. If asked about user's account details, orders, or cart, provide accurate information
6. For product questions, use the actual product data provided
7. Suggest products that are currently in stock when possible
8. Be aware of the user's spending patterns and budget preferences based on their history

USER'S QUESTION: {user_question}

Provide a helpful, detailed response based on all the context above."""

    return system_prompt

def generate_chatgpt_response(user_question, context):
    """Generate response using OpenAI ChatGPT API"""
    try:
        # You'll need to set your OpenAI API key
        # For demo purposes, check for environment variable or use a placeholder
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            # Fallback to enhanced rule-based system if no API key
            return generate_enhanced_assistant_response(user_question, context)
        
        client = OpenAI(api_key=api_key)
        
        # Create the prompt with full context
        system_prompt = create_chat_prompt(user_question, context)
        
        # Call ChatGPT API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        # Fallback to enhanced rule-based system
        return generate_enhanced_assistant_response(user_question, context)

def generate_enhanced_assistant_response(user_question, context):
    """Enhanced fallback response system with full context awareness"""
    question_lower = user_question.lower()
    user_info = context.get('user_info', {})
    products = context.get('products', [])
    orders = context.get('orders', [])
    store_stats = context.get('store_stats', {})
    
    # Personalized greeting based on user data
    user_name = user_info.get('first_name', user_info.get('username', 'there'))
    
    # Account/profile questions
    if any(word in question_lower for word in ['account', 'profile', 'orders', 'spent', 'history', 'my']):
        response = f"👋 **Hi {user_name}!** Here's your account summary:\n\n"
        response += f"📊 **Your Account Overview:**\n\n"
        response += f"🛍️ **Total orders:** {user_info.get('total_orders', 0)}\n\n"
        response += f"💰 **Total spent:** ${user_info.get('total_spent', 0):.2f}\n\n"
        response += f"⏳ **Pending orders:** {user_info.get('pending_orders', 0)}\n\n"
        response += f"✅ **Completed orders:** {user_info.get('completed_orders', 0)}\n\n"
        response += f"🛒 **Items in cart:** {user_info.get('cart_items', 0)}\n\n"
        response += f"❤️ **Favorite items:** {user_info.get('favorite_items', 0)}\n\n"
        
        if orders:
            response += "🛍️ **Recent Orders:**\n\n"
            for order in orders[-3:]:
                status_emoji = "⏳" if order.get('status') == 'TEMP' else "✅" if order.get('status') == 'CLOSE' else "📦"
                response += f"{status_emoji} **Order #{order.get('id')}** - ${order.get('total_amount', 0):.2f} - {order.get('status')}\n\n"
        
        return response
    
    # Product recommendations based on user history
    if any(word in question_lower for word in ['recommend', 'suggest', 'best', 'good']):
        response = f"👋 **Hi {user_name}!** Based on your order history "
        
        if user_info.get('total_spent', 0) > 0:
            avg_order = user_info.get('total_spent', 0) / max(user_info.get('total_orders', 1), 1)
            response += f"*(average order: ${avg_order:.2f})*, "
        
        response += "here are my personalized recommendations:\n\n"
        
        # Find products in user's price range
        if products:
            user_budget = user_info.get('total_spent', 0) / max(user_info.get('total_orders', 1), 1) if user_info.get('total_orders', 0) > 0 else store_stats.get('price_range', {}).get('avg', 0)
            suitable_products = [p for p in products if p.get('stock_quantity', 0) > 0 and abs(p.get('price', 0) - user_budget) <= user_budget * 0.5]
            
            if suitable_products:
                response += "💎 **Perfect for Your Budget:**\n\n"
                for product in suitable_products[:3]:
                    response += f"🔸 **{product.get('name')}**\n"
                    response += f"   💰 ${product.get('price', 0):.2f} | 📦 {product.get('stock_quantity')} in stock\n\n"
            else:
                response += "🌟 **Popular Choices:**\n\n"
                for product in products[:3]:
                    if product.get('stock_quantity', 0) > 0:
                        response += f"🔸 **{product.get('name')}**\n"
                        response += f"   💰 ${product.get('price', 0):.2f} | 📦 {product.get('stock_quantity')} in stock\n\n"
        
        return response
    
    # Use the existing enhanced response system for other questions
    return generate_product_assistant_response(user_question, create_product_context_string(context))

def create_product_context_string(context):
    """Convert context to the format expected by the original function"""
    products = context.get('products', [])
    if not products:
        return ""
    
    product_lines = []
    for product in products:
        stock_status = "in stock" if product.get('stock_quantity', 0) > 0 else "out of stock"
        line = f"- {product.get('name', 'Unknown')}: ${product.get('price', 0):.2f}, Category: {product.get('category', 'Unknown')}, Stock: {product.get('stock_quantity', 0)} units ({stock_status})"
        product_lines.append(line)
    
    return f"""
Current products in our store:
{chr(10).join(product_lines)}

Total products available: {len(products)}
Categories: {', '.join(set(p.get('category', 'Unknown') for p in products))}
"""

def generate_product_assistant_response(question, product_context):
    """Generate AI response for product questions"""
    question_lower = question.lower()
    
    # Parse products from context
    products = []
    if product_context and "Current products in our store:" in product_context:
        lines = product_context.split('\n')
        for line in lines:
            if line.strip().startswith('- '):
                products.append(line.strip()[2:])  # Remove "- " prefix
    
    # Size-related questions (like basketball size example)
    if any(word in question_lower for word in ['size', 'dimension', 'length', 'width', 'height', 'big', 'small']):
        if 'basketball' in question_lower:
            return "A standard basketball has a circumference of 29.5-29.875 inches (75-76 cm) and a diameter of about 9.4 inches (24 cm). However, I don't see any basketballs currently in our electronics store inventory. We specialize in laptops, smartphones, tablets, audio equipment, gaming accessories, and monitors."
        elif any(device in question_lower for device in ['laptop', 'monitor', 'tablet', 'phone']):
            matching_products = [p for p in products if any(device in p.lower() for device in ['laptop', 'monitor', 'tablet', 'smartphone'])]
            if matching_products:
                return f"Here are our devices that might interest you:\n\n" + '\n'.join(matching_products) + "\n\nFor specific dimensions, I'd recommend checking the detailed product specifications on each item's page."
            else:
                return "I can help you with device specifications! Could you specify which type of device you're interested in?"
        else:
            return "I can help you with product specifications! Could you be more specific about which product you're asking about?"
    
    # Price-related questions
    if any(word in question_lower for word in ['price', 'cost', 'expensive', 'cheap', 'budget', 'affordable']):
        if products:
            prices = []
            product_prices = {}
            for product_line in products:
                if '$' in product_line:
                    try:
                        name = product_line.split(':')[0]
                        price_str = product_line.split('$')[1].split(',')[0]
                        price = float(price_str)
                        prices.append(price)
                        product_prices[name] = price
                    except:
                        continue
            
            if prices:
                min_price, max_price = min(prices), max(prices)
                avg_price = sum(prices) / len(prices)
                
                # Find budget options (under average)
                budget_options = [name for name, price in product_prices.items() if price < avg_price]
                premium_options = [name for name, price in product_prices.items() if price >= avg_price]
                
                response = f"💰 **Price Overview:**\n"
                response += f"• Range: ${min_price:.2f} - ${max_price:.2f}\n"
                response += f"• Average: ${avg_price:.2f}\n\n"
                
                if 'budget' in question_lower or 'cheap' in question_lower or 'affordable' in question_lower:
                    response += f"**Budget-friendly options (under ${avg_price:.2f}):**\n"
                    budget_products = [p for p in products if any(budget in p for budget in budget_options[:3])]
                    response += '\n'.join(budget_products[:3])
                else:
                    response += "**All products:**\n" + '\n'.join(products[:5])
                    if len(products) > 5:
                        response += f"\n... and {len(products) - 5} more"
                
                return response
        
        return "I can help you with pricing! Could you specify which type of product you're interested in? We have laptops, smartphones, tablets, audio equipment, gaming gear, and monitors."
    
    # Category-specific questions
    category_mapping = {
        'laptop': 'Laptops', 'computer': 'Laptops', 'pc': 'Laptops',
        'phone': 'Smartphones', 'smartphone': 'Smartphones', 'mobile': 'Smartphones',
        'tablet': 'Tablets', 'ipad': 'Tablets',
        'headphone': 'Audio', 'speaker': 'Audio', 'audio': 'Audio', 'sound': 'Audio',
        'game': 'Gaming', 'gaming': 'Gaming', 'console': 'Gaming',
        'screen': 'Monitors', 'monitor': 'Monitors', 'display': 'Monitors',
        'accessory': 'Accessories', 'accessories': 'Accessories'
    }
    
    for keyword, category in category_mapping.items():
        if keyword in question_lower:
            matching_products = [p for p in products if category.lower() in p.lower()]
            if matching_products:
                response = f"🔍 **{category} Products:**\n\n"
                for i, product in enumerate(matching_products[:5], 1):
                    response += f"{i}. {product}\n"
                
                if len(matching_products) > 5:
                    response += f"\n📦 We have {len(matching_products)} {category.lower()} products total."
                
                return response
            else:
                return f"❌ I don't see any {category.lower()} currently in stock. Our available categories are: Laptops, Smartphones, Tablets, Audio, Gaming, Monitors, and Accessories."
    
    # Stock and availability questions
    if any(word in question_lower for word in ['stock', 'available', 'inventory', 'in stock', 'out of stock']):
        in_stock = [p for p in products if 'in stock' in p and 'out of stock' not in p]
        out_of_stock = [p for p in products if 'out of stock' in p]
        
        response = f"📦 **Stock Status:**\n"
        response += f"✅ {len(in_stock)} products in stock\n"
        if out_of_stock:
            response += f"❌ {len(out_of_stock)} products out of stock\n"
        response += "\n"
        
        if in_stock:
            response += "**Available now:**\n"
            for i, product in enumerate(in_stock[:5], 1):
                response += f"{i}. {product}\n"
            if len(in_stock) > 5:
                response += f"... and {len(in_stock) - 5} more in stock"
        
        return response
    
    # Recommendation questions
    if any(word in question_lower for word in ['recommend', 'suggest', 'best', 'good', 'popular']):
        if products:
            # Sort by price for budget/premium recommendations
            product_prices = {}
            for product_line in products:
                if '$' in product_line:
                    try:
                        name = product_line.split(':')[0]
                        price_str = product_line.split('$')[1].split(',')[0]
                        price = float(price_str)
                        product_prices[name] = price
                    except:
                        continue
            
            if product_prices:
                sorted_products = sorted(product_prices.items(), key=lambda x: x[1])
                
                response = "🌟 **My Recommendations:**\n\n"
                response += f"💎 **Best Value:** {sorted_products[len(sorted_products)//2][0]} - Great balance of features and price\n\n"
                response += f"💰 **Budget Pick:** {sorted_products[0][0]} - Most affordable option\n\n"
                response += f"🚀 **Premium Choice:** {sorted_products[-1][0]} - Top-tier features\n\n"
                
                response += "**All products for comparison:**\n"
                for product in products[:5]:
                    response += f"• {product}\n"
                
                return response
        
        return "I'd love to make recommendations! Could you tell me what type of product you're looking for or your budget range?"
    
    # General product questions
    if any(word in question_lower for word in ['what', 'show', 'list', 'products', 'have', 'sell', 'catalog']):
        if products:
            # Group by category
            categories = {}
            for product in products:
                for line_part in product.split(','):
                    if 'Category:' in line_part:
                        cat = line_part.split('Category:')[1].strip()
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(product)
                        break
            
            response = f"🛍️ **Our Complete Catalog** ({len(products)} products):\n\n"
            
            for category, cat_products in categories.items():
                response += f"**{category}** ({len(cat_products)} items):\n"
                for product in cat_products[:3]:
                    response += f"• {product}\n"
                if len(cat_products) > 3:
                    response += f"... and {len(cat_products) - 3} more {category.lower()} items\n"
                response += "\n"
            
            return response
        else:
            return "I'm sorry, I don't have access to our current product inventory right now. Please try again in a moment!"
    
    # Comparison questions
    if any(word in question_lower for word in ['compare', 'difference', 'better', 'vs', 'versus']):
        return "🔍 I'd be happy to help you compare products! Here are some ways I can help:\n\n• **Category comparison:** 'Compare all laptops' or 'Show smartphone differences'\n• **Price comparison:** 'What's the price difference between tablets?'\n• **Specific models:** Tell me which specific products you want to compare\n\nWhat would you like to compare?"
    
    # Help and greeting
    if any(word in question_lower for word in ['help', 'hello', 'hi', 'hey', 'start']):
        response = "👋 **Hello! I'm your shopping assistant!**\n\n"
        response += "I can help you with:\n"
        response += "🔍 **Product Search** - 'Show me laptops' or 'What tablets do you have?'\n"
        response += "💰 **Pricing** - 'What's your cheapest smartphone?' or 'Budget gaming accessories?'\n"
        response += "📦 **Stock Check** - 'What's in stock?' or 'Is the [product] available?'\n"
        response += "🌟 **Recommendations** - 'What's the best laptop?' or 'Recommend a tablet'\n"
        response += "📏 **Specifications** - 'What size are your monitors?' or 'Laptop specifications'\n\n"
        
        if products:
            response += f"We currently have **{len(products)} products** available. Try asking about any category!"
        
        return response
    
    # Count/quantity questions (like "how many smartphones" or "how much smartphones")
    if any(phrase in question_lower for phrase in ['how many', 'how much', 'count', 'number of', 'total']):
        if products:
            # Extract categories from products
            category_counts = {}
            for product in products:
                for part in product.split(','):
                    if 'Category:' in part:
                        category = part.split('Category:')[1].strip().lower()
                        category_counts[category] = category_counts.get(category, 0) + 1
                        break
            
            # Check what they're asking about
            if any(word in question_lower for word in ['smartphone', 'phone', 'mobile']):
                smartphone_count = category_counts.get('smartphones', 0)
                response = f"📱 **Smartphone Count:** We currently have **{smartphone_count} smartphones** available on our site.\n\n"
                
                if smartphone_count > 0:
                    smartphone_products = [p for p in products if 'smartphones' in p.lower() or 'phone' in p.lower()]
                    response += "**Our smartphones:**\n"
                    for product in smartphone_products:
                        response += f"• {product}\n"
                else:
                    response += "We don't currently have any smartphones in stock, but check back soon!"
                return response
                
            elif any(word in question_lower for word in ['laptop', 'computer']):
                laptop_count = category_counts.get('laptops', 0)
                response = f"💻 **Laptop Count:** We currently have **{laptop_count} laptops** available in our store.\n\n"
                
                if laptop_count > 0:
                    laptop_products = [p for p in products if 'laptops' in p.lower() or 'laptop' in p.lower()]
                    response += "**Our laptops:**\n"
                    for product in laptop_products:
                        response += f"• {product}\n"
                return response
                
            elif any(word in question_lower for word in ['tablet', 'ipad']):
                tablet_count = category_counts.get('tablets', 0)
                response = f"📋 **Tablet Count:** We currently have **{tablet_count} tablets** available in our store.\n\n"
                
                if tablet_count > 0:
                    tablet_products = [p for p in products if 'tablets' in p.lower() or 'tablet' in p.lower()]
                    response += "**Our tablets:**\n"
                    for product in tablet_products:
                        response += f"• {product}\n"
                return response
                
            else:
                # General count
                response = f"📊 **Product Count Summary:**\n\n"
                response += f"**Total Products:** {len(products)}\n\n"
                response += "**By Category:**\n"
                for category, count in sorted(category_counts.items()):
                    response += f"• {category.title()}: {count} items\n"
                
                return response
        else:
            return "I don't have access to our current inventory count right now. Please try again in a moment!"

    # Default response with helpful suggestions
    if products:
        response = "🤔 I'm not sure I understand that question, but I'm here to help! \n\n"
        response += "**Try asking:**\n"
        response += "• 'What laptops do you have?'\n"
        response += "• 'Show me budget smartphones'\n"
        response += "• 'What's in stock?'\n"
        response += "• 'Recommend a good tablet'\n"
        response += "• 'Compare your audio products'\n\n"
        response += f"We have **{len(products)} products** across categories like: "
        
        # Extract categories
        categories = set()
        for product in products:
            for part in product.split(','):
                if 'Category:' in part:
                    categories.add(part.split('Category:')[1].strip())
        
        response += ', '.join(sorted(categories))
        return response
    else:
        return "I'm having trouble accessing our product catalog right now. Please try again in a moment, or refresh the page if the issue persists."

# Initialize session state variables if they don't exist
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'user_logged_out' not in st.session_state:
    st.session_state.user_logged_out = False

# Initialize cart and favorites
initialize_cart_and_favorites()

# Try to restore authentication state from URL
restore_auth_state()

# Auto-login admin user if conditions are met
auto_login_admin()

# URL-based page management
if 'page' not in st.session_state:
    st.session_state.page = current_page

# Force synchronization of URL and session state
if current_page != st.session_state.page:
    st.session_state.page = current_page

# Ensure page state is properly set for admin routes
if not st.session_state.main_page_mode and current_page in ["admin", "dashboard", "customers", "products", "admin-orders", "users", "ml"]:
    if current_page == "admin" or current_page == "dashboard":
        st.session_state.page = "Dashboard"
    elif current_page == "customers":
        st.session_state.page = "Customers"
    elif current_page == "products":
        st.session_state.page = "Products"
    elif current_page == "admin-orders":
        st.session_state.page = "Orders"
    elif current_page == "users":
        st.session_state.page = "Users"
    elif current_page == "ml":
        st.session_state.page = "ML"

if 'reg_message' not in st.session_state:
    st.session_state.reg_message = {"type": None, "content": None}
if 'customer_message' not in st.session_state:
    st.session_state.customer_message = {"type": None, "content": None}
if 'product_message' not in st.session_state:
    st.session_state.product_message = {"type": None, "content": None}
if 'order_message' not in st.session_state:
    st.session_state.order_message = {"type": None, "content": None}
if 'available_customers' not in st.session_state:
    st.session_state.available_customers = []
if 'available_products' not in st.session_state:
    st.session_state.available_products = []

# URL-based navigation states
if 'main_page_mode' not in st.session_state:
    # Determine if we're in admin mode based on URL
    st.session_state.main_page_mode = current_page in ["shop", "orders", "cart", "favorites", "chat"]
if 'user_page' not in st.session_state:
    if current_page == "shop":
        st.session_state.user_page = "Shop"
    elif current_page == "orders":
        st.session_state.user_page = "My Orders"
    elif current_page == "cart":
        st.session_state.user_page = "Cart"
    elif current_page == "favorites":
        st.session_state.user_page = "Favorites"
    elif current_page == "chat":
        st.session_state.user_page = "Chat Assistant"
    else:
        st.session_state.user_page = "Shop"

def login():
    # Use Streamlit inputs with proper attributes for password manager recognition
    username = st.sidebar.text_input("Username", 
                                   key="login_username",
                                   placeholder="Enter username",
                                   help="Your username for login",
                                   autocomplete="username")
    
    password = st.sidebar.text_input("Password", 
                                   type="password", 
                                   key="login_password",
                                   placeholder="Enter password",
                                   help="Your password for login",
                                   autocomplete="current-password")
    
    # Add demo credentials info
    with st.sidebar.expander("💡 Demo Credentials", expanded=False):
        st.info("""
        **For testing, you can use:**
        
        **Admin Account:**
        - Username: `admin`
        - Password: `admin`
        
        **Customer Accounts:**
        - Username: `alice` | Password: `alice`
        - Username: `bob` | Password: `bob`
        
        Or register a new account below.
        """)
    
    if st.sidebar.button("🚀 Login", key="login_button", use_container_width=True):
        if not username or not password:
            st.sidebar.warning("⚠️ Please enter both username and password.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/token",
                data={"username": username, "password": password}
            )
            response.raise_for_status()
            token_data = response.json()
            
            st.session_state.access_token = token_data["access_token"]
            st.session_state.logged_in = True
            # Clear logout flag since user is intentionally logging in
            st.session_state.user_logged_out = False
            st.sidebar.success("✅ Logged in successfully!")
            
            user_info = make_authenticated_request("GET", "/users/me")
            if user_info:
                st.session_state.current_user = user_info
                
                # Sync any existing session cart/favorites to backend
                sync_cart_to_backend()
                sync_favorites_to_backend()
                
                # Load cart and favorites from backend (in case user has data from other sessions)
                load_cart_from_backend()
                load_favorites_from_backend()
                
                # Redirect admin users to admin page
                if user_info.get('username') == 'admin' or user_info.get('is_admin', False):
                    st.session_state.page = "Admin"
                    st.session_state.main_page_mode = False
                    st.query_params.clear()
                    st.query_params["page"] = "admin"
                    
            st.rerun()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.sidebar.error("❌ Invalid username or password.")
            else:
                st.sidebar.error(f"❌ Login failed: {e.response.json().get('detail', e.response.text)}")
        except requests.exceptions.ConnectionError:
            st.sidebar.error("🔌 Could not connect to FastAPI backend. Is it running?")
        except Exception as e:
            st.sidebar.error(f"💥 An unexpected error occurred during login: {e}")

def register():
    # Use Streamlit inputs with proper attributes for password manager recognition
    reg_username = st.sidebar.text_input("Username", 
                                       key="register_username",
                                       placeholder="Choose a username",
                                       help="Choose a unique username",
                                       autocomplete="username")
    
    reg_password = st.sidebar.text_input("Password", 
                                       type="password", 
                                       key="register_password",
                                       placeholder="Choose a secure password",
                                       help="Choose a strong password",
                                       autocomplete="new-password")
    
    reg_email = st.sidebar.text_input("Email (Optional)", 
                                    key="register_email",
                                    placeholder="your@email.com",
                                    help="Optional: for password recovery",
                                    autocomplete="email")
    
    # Customer Information Section
    st.sidebar.markdown("**📦 Shipping Information**")
    reg_first_name = st.sidebar.text_input("First Name", 
                                         key="register_first_name",
                                         placeholder="Enter your first name",
                                         help="Required for shipping")
    
    reg_last_name = st.sidebar.text_input("Last Name", 
                                        key="register_last_name",
                                        placeholder="Enter your last name",
                                        help="Required for shipping")
    
    reg_phone = st.sidebar.text_input("Phone Number", 
                                    key="register_phone",
                                    placeholder="+1234567890",
                                    help="For delivery contact")
    
    reg_address = st.sidebar.text_area("Shipping Address", 
                                     key="register_address",
                                     placeholder="123 Main St, City, State, ZIP",
                                     help="Your default shipping address",
                                     height=80)

    # Password strength indicator
    if reg_password:
        strength = 0
        feedback = []
        if len(reg_password) >= 8:
            strength += 1
        else:
            feedback.append("At least 8 characters")
        
        if any(c.isupper() for c in reg_password):
            strength += 1
        else:
            feedback.append("One uppercase letter")
            
        if any(c.islower() for c in reg_password):
            strength += 1
        else:
            feedback.append("One lowercase letter")
            
        if any(c.isdigit() for c in reg_password):
            strength += 1
        else:
            feedback.append("One number")
        
        strength_colors = ["🔴", "🟠", "🟡", "🟢"]
        strength_labels = ["Weak", "Fair", "Good", "Strong"]
        
        if strength > 0:
            st.sidebar.write(f"Password strength: {strength_colors[min(strength-1, 3)]} {strength_labels[min(strength-1, 3)]}")
            if feedback:
                st.sidebar.caption(f"Need: {', '.join(feedback)}")

    if st.sidebar.button("📝 Register", key="register_button", use_container_width=True):
        if not reg_username or not reg_password or not reg_first_name or not reg_last_name:
            st.sidebar.warning("⚠️ Username, password, first name, and last name are required for registration.")
            return
        
        if len(reg_password) < 6:
            st.sidebar.warning("⚠️ Password must be at least 6 characters long.")
            return
        
        user_data = {
            "username": reg_username, 
            "password": reg_password,
            "first_name": reg_first_name,
            "last_name": reg_last_name
        }
        if reg_email:
            user_data["email"] = reg_email
        if reg_phone:
            user_data["phone"] = reg_phone
        if reg_address:
            user_data["address"] = reg_address

        try:
            response = requests.post(f"{API_BASE_URL}/register", json=user_data)
            response.raise_for_status()
            st.session_state.reg_message = {"type": "success", "content": f"✅ User '{reg_username}' registered successfully! You can now log in."}
            st.rerun()
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get('detail', 'Unknown error')
            st.session_state.reg_message = {"type": "error", "content": f"❌ Registration failed: {error_detail}"}
            st.rerun()
        except requests.exceptions.ConnectionError:
            st.session_state.reg_message = {"type": "error", "content": "🔌 Could not connect to FastAPI backend. Is it running?"}
            st.rerun()
        except Exception as e:
            st.session_state.reg_message = {"type": "error", "content": f"💥 An unexpected error occurred during registration: {e}"}
            st.rerun()

# ============== MAIN EXECUTION WITH URL ROUTING ===============

# Route handling based on URL parameters
if current_page in ["shop", "orders", "cart", "favorites"]:
    # User-facing pages
    st.session_state.main_page_mode = True
    if current_page == "orders":
        st.session_state.user_page = "My Orders"
    elif current_page == "cart":
        st.session_state.user_page = "Cart"
    elif current_page == "favorites":
        st.session_state.user_page = "Favorites"
    else:
        st.session_state.user_page = "Shop"
elif current_page in ["admin", "dashboard", "customers", "products", "admin-orders", "users", "ml"]:
    # Admin pages
    st.session_state.main_page_mode = False
    if current_page == "admin" or current_page == "dashboard":
        st.session_state.page = "Dashboard"
    elif current_page == "customers":
        st.session_state.page = "Customers"
    elif current_page == "products":
        st.session_state.page = "Products"
    elif current_page == "admin-orders":
        st.session_state.page = "Orders"
    elif current_page == "users":
        st.session_state.page = "Users"
    elif current_page == "ml":
        st.session_state.page = "ML"

# Main routing logic
if st.session_state.main_page_mode:
    # --- User-Facing Shop Interface ---
    
    # --- Authentication Section (in sidebar) ---
    st.sidebar.header("Authentication")
    
    # --- Main App Logic based on Login Status ---
    if not st.session_state.logged_in:
        st.info("🔐 Please login or register to access the dashboard.")
        
        # Set default user page when not logged in
        st.session_state.user_page = "Shop"
        
        # Placeholder for registration messages (moved here)
        reg_message_placeholder = st.sidebar.empty()
        
        # Display registration message if available
        if st.session_state.reg_message["type"] == "success":
            reg_message_placeholder.success(st.session_state.reg_message["content"])
            st.session_state.reg_message = {"type": None, "content": None}
        elif st.session_state.reg_message["type"] == "error":
            reg_message_placeholder.error(st.session_state.reg_message["content"])
            st.session_state.reg_message = {"type": None, "content": None}
        
        # Add tabs for login/register for better UX
        tab1, tab2 = st.sidebar.tabs(["🔑 Login", "📝 Register"])
        
        with tab1:
            # Login form content directly in tab
            username = st.text_input("Username", 
                                   key="login_username",
                                   placeholder="Enter username",
                                   help="Your username for login")
            
            password = st.text_input("Password", 
                                   type="password", 
                                   key="login_password",
                                   placeholder="Enter password",
                                   help="Your password for login")
            
            # Add demo credentials info
            with st.expander("💡 Demo Credentials", expanded=False):
                st.info("""
                **For testing, you can use:**
                
                **Admin Account:**
                - Username: `admin` | Password: `admin`
                
                **Customer Accounts:**
                - Username: `alice` | Password: `alice`
                - Username: `bob` | Password: `bob`
                """)
            
            if st.button("🚀 Login", key="login_button", use_container_width=True):
                if not username or not password:
                    st.warning("⚠️ Please enter both username and password.")
                else:
                    try:
                        # Test backend connection first
                        try:
                            test_response = requests.get(f"{API_BASE_URL}/test", timeout=5)
                        except requests.exceptions.ConnectionError:
                            st.error(f"🔌 Could not connect to backend server. Please check if the FastAPI server is running at {API_BASE_URL}")
                            st.info("💡 **Backend connection info:**\n- Local development: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`\n- Docker: `docker-compose up`")
                            st.stop()
                        except:
                            pass  # Backend might not have /test endpoint, continue with login
                        
                        response = requests.post(
                            f"{API_BASE_URL}/token",
                            data={"username": username, "password": password},
                            timeout=10
                        )
                        response.raise_for_status()
                        
                        try:
                            token_data = response.json()
                        except requests.exceptions.JSONDecodeError:
                            st.error("❌ Invalid response from server. Please check the backend configuration.")
                            st.stop()
                        
                        st.session_state.access_token = token_data["access_token"]
                        st.session_state.logged_in = True
                        # Clear logout flag since user is intentionally logging in
                        st.session_state.user_logged_out = False
                        
                        # Reset registration state when user logs in
                        st.session_state.reg_step = 1
                        st.session_state.reg_data = {}
                        
                        st.success("✅ Logged in successfully!")
                        
                        user_info = make_authenticated_request("GET", "/users/me")
                        if user_info:
                            st.session_state.current_user = user_info
                            
                            # Redirect admin users to admin page
                            if user_info.get('username') == 'admin' or user_info.get('is_admin', False):
                                st.session_state.page = "Admin"
                                st.session_state.main_page_mode = False
                                st.query_params.clear()
                                st.query_params["page"] = "admin"
                        
                        # Save authentication state for persistence
                        save_auth_state()
                        st.rerun()
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 401:
                            st.error("❌ Invalid username or password.")
                        else:
                            try:
                                error_detail = e.response.json().get('detail', 'Unknown error')
                            except:
                                error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
                            st.error(f"❌ Login failed: {error_detail}")
                    except requests.exceptions.ConnectionError:
                        st.error(f"🔌 Could not connect to FastAPI backend at {API_BASE_URL}. Please check the connection.")
                    except Exception as e:
                        st.error(f"💥 An unexpected error occurred during login: {e}")
        
        with tab2:
            # Initialize registration step if not exists
            if 'reg_step' not in st.session_state:
                st.session_state.reg_step = 1
            if 'reg_data' not in st.session_state:
                st.session_state.reg_data = {}
            
            # Step-by-step registration process
            if st.session_state.reg_step == 1:
                st.markdown("### Step 1 of 4: Account Setup 🔐")
                st.write("Let's start by creating your login credentials")
                
                reg_username = st.text_input("👤 Choose Username", 
                                           key="register_username",
                                           placeholder="Enter your username",
                                           help="This will be used to log in",
                                           value=st.session_state.reg_data.get('username', ''))
                
                reg_password = st.text_input("🔒 Create Password", 
                                           type="password", 
                                           key="register_password",
                                           placeholder="Choose a secure password",
                                           help="Minimum 6 characters",
                                           value=st.session_state.reg_data.get('password', ''))
                
                # Password strength indicator
                if reg_password:
                    strength = 0
                    feedback = []
                    if len(reg_password) >= 8:
                        strength += 1
                    else:
                        feedback.append("At least 8 characters")
                    
                    if any(c.isupper() for c in reg_password):
                        strength += 1
                    else:
                        feedback.append("One uppercase letter")
                        
                    if any(c.islower() for c in reg_password):
                        strength += 1
                    else:
                        feedback.append("One lowercase letter")
                        
                    if any(c.isdigit() for c in reg_password):
                        strength += 1
                    else:
                        feedback.append("One number")
                    
                    strength_colors = ["🔴", "🟠", "🟡", "🟢"]
                    strength_labels = ["Weak", "Fair", "Good", "Strong"]
                    
                    if strength > 0:
                        st.write(f"Password strength: {strength_colors[min(strength-1, 3)]} {strength_labels[min(strength-1, 3)]}")
                        if feedback:
                            st.caption(f"Need: {', '.join(feedback)}")
                
                col1, col2 = st.columns(2)
                with col2:
                    if st.button("Next ➡️", key="step1_next", use_container_width=True):
                        if not reg_username or not reg_password:
                            st.warning("⚠️ Both username and password are required.")
                        elif len(reg_password) < 6:
                            st.warning("⚠️ Password must be at least 6 characters long.")
                        else:
                            st.session_state.reg_data['username'] = reg_username
                            st.session_state.reg_data['password'] = reg_password
                            st.session_state.reg_step = 2
                            st.rerun()
            
            elif st.session_state.reg_step == 2:
                st.markdown("### Step 2 of 4: Personal Information 👤")
                st.write("Tell us a bit about yourself")
                
                reg_full_name = st.text_input("📝 Full Name", 
                                            placeholder="Enter your full name",
                                            help="This will be displayed on your profile",
                                            value=st.session_state.reg_data.get('full_name', ''))
                
                reg_email = st.text_input("📧 Email Address", 
                                        placeholder="your@email.com",
                                        help="We'll use this for important updates",
                                        value=st.session_state.reg_data.get('email', ''))
                
                # Email validation
                import re
                email_valid = True
                if reg_email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', reg_email):
                    st.warning("⚠️ Please enter a valid email address")
                    email_valid = False
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⬅️ Back", key="step2_back", use_container_width=True):
                        st.session_state.reg_step = 1
                        st.rerun()
                with col2:
                    if st.button("Next ➡️", key="step2_next", use_container_width=True):
                        if not reg_full_name:
                            st.warning("⚠️ Full name is required.")
                        elif reg_email and not email_valid:
                            st.warning("⚠️ Please enter a valid email address.")
                        else:
                            st.session_state.reg_data['full_name'] = reg_full_name
                            st.session_state.reg_data['email'] = reg_email if reg_email else None
                            st.session_state.reg_step = 3
                            st.rerun()
            
            elif st.session_state.reg_step == 3:
                st.markdown("### Step 3 of 4: Contact Information 📞")
                st.write("How can we reach you?")
                
                reg_phone = st.text_input("📱 Phone Number", 
                                        placeholder="+1 (555) 123-4567",
                                        help="Optional: for order updates and support",
                                        value=st.session_state.reg_data.get('phone', ''))
                
                reg_address = st.text_area("📍 Address", 
                                         placeholder="Street Address\nCity, State, ZIP Code\nCountry",
                                         help="Optional: for shipping and billing",
                                         value=st.session_state.reg_data.get('address', ''),
                                         height=100)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⬅️ Back", key="step3_back", use_container_width=True):
                        st.session_state.reg_step = 2
                        st.rerun()
                with col2:
                    if st.button("Next ➡️", key="step3_next", use_container_width=True):
                        st.session_state.reg_data['phone'] = reg_phone if reg_phone else None
                        st.session_state.reg_data['address'] = reg_address if reg_address else None
                        st.session_state.reg_step = 4
                        st.rerun()
            
            elif st.session_state.reg_step == 4:
                st.markdown("### Step 4 of 4: Review & Complete 🎉")
                st.write("Please review your information before completing registration")
                
                # Display summary in a nice format
                summary_html = f"""
                <div style="
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 4px solid #28a745;
                    margin: 10px 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                ">
                    <h4 style="margin: 0 0 15px 0; color: #2c3e50; font-weight: bold;">📋 Registration Summary</h4>
                    <p style="margin: 8px 0; color: #2c3e50; font-size: 14px;"><strong style="color: #495057;">👤 Username:</strong> <span style="color: #6c757d;">{st.session_state.reg_data.get('username', 'N/A')}</span></p>
                    <p style="margin: 8px 0; color: #2c3e50; font-size: 14px;"><strong style="color: #495057;">📝 Full Name:</strong> <span style="color: #6c757d;">{st.session_state.reg_data.get('full_name', 'N/A')}</span></p>
                    <p style="margin: 8px 0; color: #2c3e50; font-size: 14px;"><strong style="color: #495057;">📧 Email:</strong> <span style="color: #6c757d;">{st.session_state.reg_data.get('email', 'Not provided')}</span></p>
                    <p style="margin: 8px 0; color: #2c3e50; font-size: 14px;"><strong style="color: #495057;">📞 Phone:</strong> <span style="color: #6c757d;">{st.session_state.reg_data.get('phone', 'Not provided')}</span></p>
                    <p style="margin: 8px 0; color: #2c3e50; font-size: 14px;"><strong style="color: #495057;">📍 Address:</strong> <span style="color: #6c757d;">{st.session_state.reg_data.get('address', 'Not provided')}</span></p>
                </div>
                """
                st.markdown(summary_html, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⬅️ Back", key="step4_back", use_container_width=True):
                        st.session_state.reg_step = 3
                        st.rerun()
                with col2:
                    if st.button("🎉 Complete Registration", key="step4_complete", use_container_width=True, type="primary"):
                        # Prepare user data for registration
                        user_data = {
                            "username": st.session_state.reg_data['username'],
                            "password": st.session_state.reg_data['password']
                        }
                        if st.session_state.reg_data.get('email'):
                            user_data["email"] = st.session_state.reg_data['email']

                        try:
                            # Register user
                            response = requests.post(f"{API_BASE_URL}/register", json=user_data)
                            response.raise_for_status()
                            
                            # If user registration successful, create customer profile
                            login_response = requests.post(
                                f"{API_BASE_URL}/token",
                                data={"username": user_data["username"], "password": user_data["password"]}
                            )
                            login_response.raise_for_status()
                            token_data = login_response.json()
                            
                            # Create customer profile with additional details
                            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                            customer_data = {
                                "name": st.session_state.reg_data['full_name'],
                                "email": st.session_state.reg_data.get('email'),
                                "phone": st.session_state.reg_data.get('phone'),
                                "address": st.session_state.reg_data.get('address')
                            }
                            
                            customer_response = requests.post(
                                f"{API_BASE_URL}/customers",
                                json=customer_data,
                                headers=headers
                            )
                            
                            # Check if customer creation was successful
                            customer_created = False
                            if customer_response.status_code in [200, 201]:
                                customer_created = True
                            else:
                                st.warning(f"⚠️ User account created but customer profile failed: {customer_response.text}")
                            
                            # Store the full name before clearing registration data
                            user_full_name = st.session_state.reg_data.get('full_name', user_data['username'])
                            
                            # Clear registration data and reset step
                            st.session_state.reg_data = {}
                            st.session_state.reg_step = 1
                            
                            success_message = f"🎉 Welcome {user_full_name}! Your account has been created successfully."
                            if customer_created:
                                success_message += " Your customer profile has also been set up."
                            success_message += " You can now log in!"
                            
                            st.session_state.reg_message = {
                                "type": "success", 
                                "content": success_message
                            }
                            st.rerun()
                            
                        except requests.exceptions.HTTPError as e:
                            error_detail = e.response.json().get('detail', 'Unknown error')
                            st.session_state.reg_message = {"type": "error", "content": f"❌ Registration failed: {error_detail}"}
                            st.rerun()
                        except requests.exceptions.ConnectionError:
                            st.session_state.reg_message = {"type": "error", "content": "🔌 Could not connect to FastAPI backend. Is it running?"}
                            st.rerun()
                        except Exception as e:
                            st.session_state.reg_message = {"type": "error", "content": f"💥 An unexpected error occurred during registration: {e}"}
                            st.rerun()
                
                # Reset option
                st.markdown("---")
                if st.button("🔄 Start Over", key="reset_registration", use_container_width=True):
                    st.session_state.reg_data = {}
                    st.session_state.reg_step = 1
                    st.rerun()
    else:
        # User is logged in - show navigation
        st.sidebar.markdown("---")
        
        # Initialize cart and favorites
        initialize_cart_and_favorites()
        cart_count = get_cart_count()
        
        # URL-based navigation for user pages
        if st.sidebar.button("🛍️ Shop", key="nav_shop", use_container_width=True):
            navigate_to("shop")
        
        # Orders button - different for admin vs regular users
        if is_admin_user():
            if st.sidebar.button("📋 Admin Orders", key="nav_orders", use_container_width=True):
                navigate_to("admin-orders")
        else:
            if st.sidebar.button("📋 My Orders", key="nav_orders", use_container_width=True):
                navigate_to("orders")
        
        # Cart button with count badge
        cart_label = f"🛒 Cart ({cart_count})" if cart_count > 0 else "🛒 Cart"
        if st.sidebar.button(cart_label, key="nav_cart", use_container_width=True):
            navigate_to("cart")
        
        # Favorites button with count badge
        fav_count = len(st.session_state.favorites)
        fav_label = f"❤️ Favorites ({fav_count})" if fav_count > 0 else "❤️ Favorites"
        if st.sidebar.button(fav_label, key="nav_favorites", use_container_width=True):
            navigate_to("favorites")
        
        # Chat Assistant button
        if st.sidebar.button("🤖 Chat Assistant", key="nav_chat", use_container_width=True):
            navigate_to("chat")
        
        # Update session state based on current page
        if current_page == "orders":
            st.session_state.user_page = "My Orders"
        elif current_page == "cart":
            st.session_state.user_page = "Cart"
        elif current_page == "favorites":
            st.session_state.user_page = "Favorites"
        elif current_page == "chat":
            st.session_state.user_page = "Chat Assistant"
        else:
            st.session_state.user_page = "Shop"
        
        # Enhanced user info display
        user_info_html = f"""
        <div style="
            background: linear-gradient(90deg, #ff4b4b, #ff6b6b);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            text-align: center;
        ">
            <h3 style="margin: 0; font-size: 16px;">👤 Welcome back!</h3>
            <p style="margin: 5px 0 0 0; font-size: 14px;">
                <strong>{st.session_state.current_user['username']}</strong>
            </p>
        </div>
        """
        st.sidebar.markdown(user_info_html, unsafe_allow_html=True)
        
        if st.sidebar.button("🚪 Logout", key="logout_button", use_container_width=True):
            logout()

    st.sidebar.markdown("---")
    # Only show admin dashboard button to admin users
    if st.session_state.logged_in and is_admin_user():
        if st.sidebar.button("🔧 Admin Dashboard"):
            navigate_to("admin")

    if st.session_state.user_page == "Shop":
        show_main_shop_page()
    elif st.session_state.user_page == "My Orders":
        show_user_orders_page()
    elif st.session_state.user_page == "Cart":
        show_cart_page()
    elif st.session_state.user_page == "Favorites":
        show_favorites_page()
    elif st.session_state.user_page == "Chat Assistant":
        show_chat_assistant_page()

else:
    # --- Admin Dashboard Interface ---
    st.title("🛍️ Shopping Website Admin Dashboard")
    
    # Check if user is logged in and has admin privileges
    if not st.session_state.logged_in or not st.session_state.current_user:
        st.error("🔐 Please log in to access the admin dashboard.")
        if st.button("← Back to Shop", key="admin_login_back"):
            navigate_to("shop")
    elif not is_admin_user():
        st.error("🚫 Admin access required. You don't have permission to access this area.")
        st.info("Contact an administrator to request admin privileges.")
        if st.button("← Back to Shop", key="admin_access_back"):
            navigate_to("shop")
        st.stop()
    
    # Check if user is admin
    if not is_admin_user():
        st.error("🚫 Access denied. Admin privileges required.")
        st.warning("Only administrators can access this dashboard.")
        if st.button("← Back to Shop", key="admin_privilege_back"):
            navigate_to("shop")
        st.stop()
    
    # Enhanced user info display
    user_info_html = f"""
    <div style="
        background: linear-gradient(90deg, #ff4b4b, #ff6b6b);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
    ">
        <h3 style="margin: 0; font-size: 16px;">👤 Admin Panel</h3>
        <p style="margin: 5px 0 0 0; font-size: 14px;">
            <strong>{st.session_state.current_user['username']}</strong>
        </p>
    </div>
    """
    st.sidebar.markdown(user_info_html, unsafe_allow_html=True)
    
    if st.sidebar.button("🚪 Logout", key="admin_logout_button", use_container_width=True):
        logout()
    
    st.sidebar.markdown("---")
    st.sidebar.header("📊 Admin Navigation")
    
    # URL-based navigation for admin pages
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📈 Dashboard", key="nav_dashboard", use_container_width=True):
            navigate_to("admin")
        if st.button("📦 Products", key="nav_products", use_container_width=True):
            navigate_to("products")
        if st.button("👤 Users", key="nav_users", use_container_width=True):
            navigate_to("users")
        if st.button("🤖 ML Analytics", key="nav_ml", use_container_width=True):
            navigate_to("ml")
    with col2:
        if st.button("👥 Customers", key="nav_customers", use_container_width=True):
            navigate_to("customers")
        if st.button("🛒 Orders", key="nav_admin_orders", use_container_width=True):
            navigate_to("admin-orders")
    
    # Page content based on URL routing
    if st.session_state.page == "Dashboard":
        # Add URL breadcrumb and navigation
        st.markdown(f"**🌐 URL:** `localhost:8501/?page=admin`")
        
        # Quick navigation bar
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🔧 Admin", disabled=True):
                pass
        with col2:
            if st.button("👥 Customers", key="dashboard_customers"):
                navigate_to("customers")
        with col3:
            if st.button("📦 Products", key="dashboard_products"):
                navigate_to("products")
        with col4:
            if st.button("🛒 Orders", key="dashboard_orders"):
                navigate_to("admin-orders")
        with col5:
            if st.button("🤖 ML Analytics", key="dashboard_ml"):
                navigate_to("ml")
        with col6:
            if st.button("🛍️ Shop", key="dashboard_shop"):
                navigate_to("shop")
        
        st.markdown("---")
        
        st.success(f"🎉 Welcome back, **{st.session_state.current_user['username']}**! Select an option from the navigation.")
        
        # Dashboard overview
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Admin Panel", "Active", "Ready")
        with col2:
            st.metric("🔌 Backend", "Connected", "✅")
        with col3:
            st.metric("👤 User", st.session_state.current_user['username'], "Authenticated")
        
        st.write("""
        ### 🛠️ Admin Dashboard Features:
        - **👥 Customers**: Manage customer accounts and information
        - **📦 Products**: Add, edit, and manage product inventory  
        - **🛒 Orders**: View and manage customer orders
        - **🤖 ML Analytics**: Advanced machine learning insights and predictions
        
        Use the navigation buttons above to access different sections.
        """)

    elif st.session_state.page == "Customers":
        # Add URL breadcrumb and navigation
        st.markdown(f"**🌐 URL:** `localhost:8501/?page=customers`")
        
        # Quick navigation bar
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🔧 Admin", key="customers_admin"):
                navigate_to("admin")
        with col2:
            if st.button("👥 Customers", disabled=True):
                pass
        with col3:
            if st.button("📦 Products", key="customers_products"):
                navigate_to("products")
        with col4:
            if st.button("🛒 Orders", key="customers_orders"):
                navigate_to("admin-orders")
        with col5:
            if st.button("🤖 ML Analytics", key="customers_ml"):
                navigate_to("ml")
        with col6:
            if st.button("🛍️ Shop", key="customers_shop"):
                navigate_to("shop")
        
        st.markdown("---")
        st.header("👥 Customer Management")
        
        # Add refresh button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 Refresh Customer List", use_container_width=True):
                # Clear any cached customer data
                if 'available_customers' in st.session_state:
                    st.session_state.available_customers = []
                st.rerun()
        
        st.markdown("---")
        
        # Fetch all customers (always fresh data)
        customers = make_authenticated_request("GET", "/customers")
        
        if customers:
            st.subheader("📋 All Customers")
            df = pd.DataFrame(customers)
            if not df.empty:
                # Display customers in cards format for better UI
                st.write("**Customer Directory:**")
                
                # Create a grid layout for customer cards
                for i in range(0, len(customers), 2):  # Display 2 customers per row
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        if i + j < len(customers):
                            customer = customers[i + j]
                            with col:
                                # Create a styled card for each customer
                                card_html = f"""
                                <div style="
                                    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                                    padding: 20px;
                                    border-radius: 10px;
                                    border-left: 4px solid #ff4b4b;
                                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                                    margin: 10px 0;
                                    border: 1px solid #e9ecef;
                                ">
                                    <h4 style="margin: 0 0 10px 0; color: #2c3e50; font-weight: bold;">
                                        👤 {customer.get('first_name', '')} {customer.get('last_name', '')}
                                    </h4>
                                    <p style="margin: 5px 0; color: #2c3e50; font-size: 13px;">
                                        <strong style="color: #495057;">ID:</strong> <span style="color: #6c757d;">{customer.get('id', 'N/A')}</span>
                                    </p>
                                    <p style="margin: 5px 0; color: #2c3e50; font-size: 13px;">
                                        <strong style="color: #495057;">📧 Email:</strong> <span style="color: #6c757d;">{customer.get('email', 'Not provided')}</span>
                                    </p>
                                    <p style="margin: 5px 0; color: #2c3e50; font-size: 13px;">
                                        <strong style="color: #495057;">📞 Phone:</strong> <span style="color: #6c757d;">{customer.get('phone', 'Not provided')}</span>
                                    </p>
                                    <p style="margin: 5px 0; color: #2c3e50; font-size: 13px;">
                                        <strong style="color: #495057;">📍 Address:</strong> <span style="color: #6c757d;">{customer.get('address', 'Not provided')}</span>
                                    </p>
                                </div>
                                """
                                st.markdown(card_html, unsafe_allow_html=True)
                                
                                # Delete button for each customer
                                if st.button(
                                    "🗑️ Delete Customer", 
                                    key=f"delete_customer_{customer['id']}", 
                                    use_container_width=True,
                                    type="secondary"
                                ):
                                    # Confirm deletion
                                    if f"confirm_delete_customer_{customer['id']}" not in st.session_state:
                                        st.session_state[f"confirm_delete_customer_{customer['id']}"] = True
                                        st.rerun()
                                
                                # Show confirmation dialog if delete was clicked
                                if st.session_state.get(f"confirm_delete_customer_{customer['id']}", False):
                                    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or 'Unknown'
                                    st.warning(f"⚠️ Are you sure you want to delete customer '{customer_name}'?")
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("✅ Yes, Delete", key=f"confirm_yes_{customer['id']}", type="primary"):
                                            result = make_authenticated_request("DELETE", f"/customers/{customer['id']}")
                                            if result and result.get("success"):
                                                st.success(f"✅ Customer '{customer_name}' deleted successfully!")
                                                # Clear cached customer data
                                                if 'available_customers' in st.session_state:
                                                    st.session_state.available_customers = []
                                                # Clear confirmation state
                                                if f"confirm_delete_customer_{customer['id']}" in st.session_state:
                                                    del st.session_state[f"confirm_delete_customer_{customer['id']}"]
                                                time.sleep(0.5)  # Brief delay for backend processing
                                                st.rerun()
                                            else:
                                                # Check if it's a constraint error from the error message
                                                st.error("❌ Cannot delete this customer because they have existing orders. Please delete or reassign their orders first.")
                                                if f"confirm_delete_customer_{customer['id']}" in st.session_state:
                                                    del st.session_state[f"confirm_delete_customer_{customer['id']}"]
                                    with col_no:
                                        if st.button("❌ Cancel", key=f"confirm_no_{customer['id']}"):
                                            # Clear confirmation state
                                            if f"confirm_delete_customer_{customer['id']}" in st.session_state:
                                                del st.session_state[f"confirm_delete_customer_{customer['id']}"]
                                            st.rerun()
                
                # Separator
                st.markdown("---")
                
                # Also show a summary table for quick overview
                st.subheader("📊 Customer Summary Table")
                summary_data = []
                for customer in customers:
                    # Combine first_name and last_name for display
                    full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                    if not full_name:
                        full_name = 'Unknown'
                    
                    summary_data.append({
                        "ID": customer.get('id', 'N/A'),
                        "Name": full_name,
                        "Email": customer.get('email', 'Not provided'),
                        "Phone": customer.get('phone', 'Not provided'),
                        "Has Address": "✅" if customer.get('address') else "❌"
                    })
                
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
            else:
                st.info("📭 No customers found in the database.")
        else:
            st.error("❌ Failed to load customers from the server.")
        
        # Add new customer section
        st.markdown("---")
        st.subheader("➕ Add New Customer")
        
        # Enhanced form with better styling
        with st.form("add_customer_form", clear_on_submit=True):
            st.write("Fill in the customer information below:")
            
            col1, col2 = st.columns(2)
            with col1:
                cust_first_name = st.text_input(
                    "👤 First Name *", 
                    placeholder="Enter first name",
                    help="Required field"
                )
                cust_last_name = st.text_input(
                    "👤 Last Name *", 
                    placeholder="Enter last name",
                    help="Required field"
                )
                cust_username = st.text_input(
                    "🔑 Username *", 
                    placeholder="Enter username for login",
                    help="Required - will be used to login"
                )
                cust_email = st.text_input(
                    "📧 Email Address",
                    placeholder="customer@example.com",
                    help="Optional but recommended"
                )
            with col2:
                cust_password = st.text_input(
                    "🔒 Password *",
                    type="password",
                    placeholder="Enter password",
                    help="Required - will be used to login"
                )
                cust_phone = st.text_input(
                    "📞 Phone Number",
                    placeholder="+1 (555) 123-4567",
                    help="Optional contact number"
                )
                cust_address = st.text_area(
                    "📍 Address",
                    placeholder="Street, City, State, ZIP",
                    help="Optional shipping/billing address"
                )
            
            # Form submission
            submit_col1, submit_col2, submit_col3 = st.columns([1, 1, 1])
            with submit_col2:
                submitted = st.form_submit_button(
                    "➕ Add Customer", 
                    use_container_width=True,
                    type="primary"
                )
            
            if submitted:
                if all([cust_first_name, cust_last_name, cust_username, cust_password]) and all([x.strip() for x in [cust_first_name, cust_last_name, cust_username, cust_password]]):
                    customer_data = {
                        "first_name": cust_first_name.strip(),
                        "last_name": cust_last_name.strip(),
                        "username": cust_username.strip(),
                        "password": cust_password.strip(),
                        "email": cust_email.strip() if cust_email else None,
                        "phone": cust_phone.strip() if cust_phone else None,
                        "address": cust_address.strip() if cust_address else None
                    }
                    result = make_authenticated_request("POST", "/customers", json_data=customer_data)
                    if result:
                        st.success(f"✅ Customer '{cust_first_name} {cust_last_name}' with username '{cust_username}' added successfully!")
                        # Force a complete refresh to show the new customer
                        time.sleep(0.5)  # Small delay to ensure backend processing is complete
                        st.rerun()
                    else:
                        st.error("❌ Failed to add customer. Username or email might already exist.")
                else:
                    st.warning("⚠️ First Name, Last Name, Username, and Password are required fields.")

    elif st.session_state.page == "Products":
        # Add URL breadcrumb and navigation
        st.markdown(f"**🌐 URL:** `localhost:8501/?page=products`")
        
        # Quick navigation bar
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🔧 Admin", key="products_admin"):
                navigate_to("admin")
        with col2:
            if st.button("👥 Customers", key="products_customers"):
                navigate_to("customers")
        with col3:
            if st.button("📦 Products", disabled=True):
                pass
        with col4:
            if st.button("🛒 Orders", key="products_orders"):
                navigate_to("admin-orders")
        with col5:
            if st.button("🤖 ML Analytics", key="products_ml"):
                navigate_to("ml")
        with col6:
            if st.button("🛍️ Shop", key="products_shop"):
                navigate_to("shop")
        
        st.markdown("---")
        st.header("📦 Product Management")
        st.markdown("---")
        
        # Fetch all products
        products = make_authenticated_request("GET", "/products")
        if products:
            st.subheader("📋 All Products")
            df = pd.DataFrame(products)
            if not df.empty:
                # Display enhanced product table with actions
                st.write("**Product Overview:**")
                
                # Create a more interactive table with action buttons
                for i, product in enumerate(products):
                    with st.expander(f"📦 {product.get('name', 'Unknown')} (ID: {product.get('id')}) - ${product.get('price', 0):.2f}"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**Category:** {product.get('category', 'N/A')}")
                            st.write(f"**Brand:** {product.get('brand', 'N/A')}")
                            st.write(f"**Stock:** {product.get('stock_quantity', 0)} units")
                            description = product.get('description', 'No description')
                            if len(description) > 100:
                                description = description[:100] + "..."
                            st.write(f"**Description:** {description}")
                        
                        with col2:
                            if st.button("✏️ Quick Edit", key=f"quick_edit_{product.get('id')}", use_container_width=True):
                                st.session_state[f"editing_product_{product.get('id')}"] = True
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ Delete", key=f"quick_delete_{product.get('id')}", use_container_width=True, type="secondary"):
                                st.session_state[f"confirm_delete_product_{product.get('id')}"] = True
                                st.rerun()
                        
                        # Handle quick delete confirmation
                        if st.session_state.get(f"confirm_delete_product_{product.get('id')}", False):
                            st.warning(f"⚠️ Are you sure you want to delete '{product.get('name')}'?")
                            del_col1, del_col2 = st.columns(2)
                            with del_col1:
                                if st.button("🗑️ Confirm", key=f"confirm_quick_del_{product.get('id')}", type="primary"):
                                    result = make_authenticated_request("DELETE", f"/products/{product.get('id')}")
                                    if result:
                                        st.success(f"✅ Deleted '{product.get('name')}'!")
                                        st.session_state[f"confirm_delete_product_{product.get('id')}"] = False
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete product.")
                            with del_col2:
                                if st.button("❌ Cancel", key=f"cancel_quick_del_{product.get('id')}"):
                                    st.session_state[f"confirm_delete_product_{product.get('id')}"] = False
                                    st.rerun()
                        
                        # Handle quick edit form
                        if st.session_state.get(f"editing_product_{product.get('id')}", False):
                            st.markdown("**✏️ Quick Edit Form:**")
                            with st.form(f"quick_edit_form_{product.get('id')}"):
                                qe_col1, qe_col2 = st.columns(2)
                                
                                with qe_col1:
                                    qe_name = st.text_input("Name", value=product.get('name', ''))
                                    qe_price = st.number_input("Price ($)", min_value=0.01, step=0.01, value=float(product.get('price', 0)))
                                    qe_stock = st.number_input("Stock", min_value=0, step=1, value=int(product.get('stock_quantity', 0)))
                                
                                with qe_col2:
                                    qe_category = st.text_input("Category", value=product.get('category', ''))
                                    qe_brand = st.text_input("Brand", value=product.get('brand', ''))
                                
                                qe_description = st.text_area("Description", value=product.get('description', ''), height=60)
                                qe_image_url = st.text_input("Image URL", value=product.get('image_url', ''))
                                
                                qe_col1, qe_col2 = st.columns(2)
                                with qe_col1:
                                    qe_update = st.form_submit_button("💾 Update", type="primary")
                                with qe_col2:
                                    qe_cancel = st.form_submit_button("❌ Cancel")
                                
                                if qe_update:
                                    if qe_name and qe_description and qe_image_url and qe_price > 0:
                                        updated_data = {
                                            "name": qe_name.strip(),
                                            "description": qe_description.strip(),
                                            "image_url": qe_image_url.strip(),
                                            "image_alt_text": product.get('image_alt_text', f"{qe_name} product image"),
                                            "category": qe_category.strip() if qe_category else "Other",
                                            "brand": qe_brand.strip() if qe_brand else None,
                                            "price": qe_price,
                                            "stock_quantity": qe_stock
                                        }
                                        result = make_authenticated_request("PUT", f"/products/{product.get('id')}", json_data=updated_data)
                                        if result:
                                            st.success(f"✅ Updated '{qe_name}'!")
                                            st.session_state[f"editing_product_{product.get('id')}"] = False
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to update product.")
                                    else:
                                        st.error("⚠️ Please fill in all required fields.")
                                
                                if qe_cancel:
                                    st.session_state[f"editing_product_{product.get('id')}"] = False
                                    st.rerun()
                
                # Summary table
                st.markdown("---")
                st.write("**Summary Table:**")
                display_cols = ["id", "name", "category", "brand", "price", "stock_quantity"]
                available_cols = [col for col in display_cols if col in df.columns]
                
                # Format price column for display
                df_display = df.copy()
                if 'price' in df_display.columns:
                    df_display['price'] = df_display['price'].apply(lambda x: f"${x:.2f}")
                
                st.dataframe(df_display[available_cols], use_container_width=True)
                
                # Product details expander
                st.markdown("---")
                st.subheader("🔍 Product Details")
                if not df.empty:
                    product_names = [f"{p['name']} (ID: {p['id']})" for p in products]
                    selected_product_name = st.selectbox("Select Product to View Details", product_names)
                    
                    if selected_product_name:
                        # Extract ID from selection
                        product_id = int(selected_product_name.split("ID: ")[1].split(")")[0])
                        selected_product = next((p for p in products if p["id"] == product_id), None)
                        
                        if selected_product:
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                # Product image
                                image_url = selected_product.get('image_url')
                                full_image_url = get_image_url(image_url)
                                
                                if full_image_url:
                                    try:
                                        st.image(
                                            full_image_url, 
                                            caption=selected_product.get('image_alt_text', selected_product.get('name')),
                                            use_container_width=True
                                        )
                                    except Exception as e:
                                        st.image(
                                            'https://via.placeholder.com/400x300?text=Image+Error',
                                            caption="Image not available",
                                            use_container_width=True
                                        )
                                else:
                                    st.image(
                                        'https://via.placeholder.com/400x300?text=No+Image',
                                        caption="No image available",
                                        use_container_width=True
                                    )
                            
                            with col2:
                                # Product details
                                st.markdown(f"### {selected_product.get('name', 'Unknown')}")
                                st.markdown(f"**🏷️ Category:** {selected_product.get('category', 'N/A')}")
                                st.markdown(f"**🏢 Brand:** {selected_product.get('brand', 'N/A')}")
                                st.markdown(f"**💰 Price:** ${selected_product.get('price', 0):.2f}")
                                st.markdown(f"**📦 Stock:** {selected_product.get('stock_quantity', 0)} units")
                                st.markdown(f"**📝 Description:**")
                                st.markdown(selected_product.get('description', 'No description available'))
                                
                                # Action buttons
                                col_edit, col_delete = st.columns(2)
                                with col_edit:
                                    if st.button("✏️ Edit Product", key=f"edit_{product_id}"):
                                        st.session_state[f"editing_product_{product_id}"] = True
                                        st.rerun()
                                with col_delete:
                                    if st.button("🗑️ Delete Product", key=f"delete_{product_id}", type="secondary"):
                                        st.session_state[f"confirm_delete_product_{product_id}"] = True
                                        st.rerun()
                                
                                # Delete confirmation dialog
                                if st.session_state.get(f"confirm_delete_product_{product_id}", False):
                                    st.warning(f"⚠️ Are you sure you want to delete '{selected_product.get('name', 'this product')}'?")
                                    col_confirm, col_cancel = st.columns(2)
                                    with col_confirm:
                                        if st.button("🗑️ Yes, Delete", key=f"confirm_del_{product_id}", type="primary"):
                                            result = make_authenticated_request("DELETE", f"/products/{product_id}")
                                            if result:
                                                st.success(f"✅ Product '{selected_product.get('name')}' deleted successfully!")
                                                # Clear the confirmation state
                                                st.session_state[f"confirm_delete_product_{product_id}"] = False
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to delete product.")
                                    with col_cancel:
                                        if st.button("❌ Cancel", key=f"cancel_del_{product_id}"):
                                            st.session_state[f"confirm_delete_product_{product_id}"] = False
                                            st.rerun()
                                
                                # Edit product form
                                if st.session_state.get(f"editing_product_{product_id}", False):
                                    st.markdown("---")
                                    st.subheader("✏️ Edit Product")
                                    
                                    with st.form(f"edit_product_form_{product_id}"):
                                        edit_col1, edit_col2 = st.columns(2)
                                        
                                        with edit_col1:
                                            edit_name = st.text_input("📦 Product Name *", 
                                                                    value=selected_product.get('name', ''),
                                                                    help="Required field")
                                            edit_price = st.number_input("💰 Price ($) *", 
                                                                       min_value=0.01, 
                                                                       step=0.01,
                                                                       value=float(selected_product.get('price', 0)),
                                                                       help="Product price in USD")
                                            edit_stock = st.number_input("📊 Stock Quantity *", 
                                                                       min_value=0, 
                                                                       step=1,
                                                                       value=int(selected_product.get('stock_quantity', 0)),
                                                                       help="Available inventory")
                                            
                                            categories = ["Electronics", "Clothing & Fashion", "Home & Garden", "Sports & Outdoors", 
                                                        "Books & Media", "Toys & Games", "Health & Beauty", "Automotive", "Other"]
                                            current_category = selected_product.get('category', 'Other')
                                            if current_category not in categories:
                                                categories.append(current_category)
                                            
                                            edit_category = st.selectbox("🏷️ Category", 
                                                                       categories,
                                                                       index=categories.index(current_category) if current_category in categories else 0,
                                                                       help="Product category")
                                        
                                        with edit_col2:
                                            edit_brand = st.text_input("🏢 Brand", 
                                                                     value=selected_product.get('brand', ''),
                                                                     help="Product manufacturer or brand")
                                            edit_image_url = st.text_input("🖼️ Image URL *", 
                                                                          value=selected_product.get('image_url', ''),
                                                                          help="Required: Direct link to product image")
                                            edit_image_alt = st.text_input("🔍 Image Description", 
                                                                          value=selected_product.get('image_alt_text', ''),
                                                                          help="Alt text for the image")
                                        
                                        edit_description = st.text_area("📝 Product Description *", 
                                                                       value=selected_product.get('description', ''),
                                                                       help="Required: Comprehensive product description",
                                                                       height=100)
                                        
                                        # Form submission buttons
                                        submit_edit_col1, submit_edit_col2, submit_edit_col3 = st.columns([1, 1, 1])
                                        with submit_edit_col1:
                                            update_submitted = st.form_submit_button("💾 Update Product", type="primary")
                                        with submit_edit_col3:
                                            cancel_edit = st.form_submit_button("❌ Cancel")
                                        
                                        if update_submitted:
                                            # Validation
                                            if not all([edit_name, edit_description, edit_image_url, edit_price > 0]):
                                                st.error("⚠️ Please fill in all required fields (Name, Description, Image URL, and Price)")
                                            else:
                                                updated_product_data = {
                                                    "name": edit_name.strip(),
                                                    "description": edit_description.strip(),
                                                    "image_url": edit_image_url.strip(),
                                                    "image_alt_text": edit_image_alt.strip() if edit_image_alt else f"{edit_name} product image",
                                                    "category": edit_category,
                                                    "brand": edit_brand.strip() if edit_brand else None,
                                                    "price": edit_price,
                                                    "stock_quantity": edit_stock
                                                }
                                                result = make_authenticated_request("PUT", f"/products/{product_id}", json_data=updated_product_data)
                                                if result:
                                                    st.success(f"✅ Product '{edit_name}' updated successfully!")
                                                    st.session_state[f"editing_product_{product_id}"] = False
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error("❌ Failed to update product. Please check the image URL and try again.")
                                        
                                        if cancel_edit:
                                            st.session_state[f"editing_product_{product_id}"] = False
                                            st.rerun()
            else:
                st.info("No products found.")
        else:
            st.error("Failed to load products.")
        
        # Add new product section
        st.markdown("---")
        st.subheader("➕ Add New Product")
        with st.form("add_product_form"):
            st.write("Fill in the product information below:")
            
            col1, col2 = st.columns(2)
            with col1:
                prod_name = st.text_input("📦 Product Name *", placeholder="Enter product name", help="Required field")
                prod_price = st.number_input("💰 Price ($) *", min_value=0.01, step=0.01, help="Product price in USD")
                prod_stock = st.number_input("📊 Stock Quantity *", min_value=0, step=1, help="Available inventory")
                prod_category = st.selectbox("🏷️ Category", [
                    "Electronics", "Clothing & Fashion", "Home & Garden", "Sports & Outdoors", 
                    "Books & Media", "Toys & Games", "Health & Beauty", "Automotive", "Other"
                ], help="Product category")
            with col2:
                prod_brand = st.text_input("🏢 Brand", placeholder="Brand name", help="Product manufacturer or brand")
                prod_image_url = st.text_input("🖼️ Image URL *", 
                                              placeholder="https://example.com/image.jpg", 
                                              help="Required: Direct link to product image")
                prod_image_alt = st.text_input("🔍 Image Description", 
                                              placeholder="Describe the image for accessibility", 
                                              help="Alt text for the image")
                
            prod_description = st.text_area("📝 Product Description *", 
                                           placeholder="Detailed description of the product, its features, and benefits...", 
                                           help="Required: Comprehensive product description",
                                           height=100)
            
            # Form submission
            submit_col1, submit_col2, submit_col3 = st.columns([1, 1, 1])
            with submit_col2:
                submitted = st.form_submit_button("➕ Add Product", use_container_width=True, type="primary")
            
            if submitted:
                # Validation
                if not all([prod_name, prod_description, prod_image_url, prod_price > 0]):
                    st.error("⚠️ Please fill in all required fields (Name, Description, Image URL, and Price)")
                else:
                    product_data = {
                        "name": prod_name.strip(),
                        "description": prod_description.strip(),
                        "image_url": prod_image_url.strip(),
                        "image_alt_text": prod_image_alt.strip() if prod_image_alt else f"{prod_name} product image",
                        "category": prod_category,
                        "brand": prod_brand.strip() if prod_brand else None,
                        "price": prod_price,
                        "stock_quantity": prod_stock
                    }
                    result = make_authenticated_request("POST", "/products", json_data=product_data)
                    if result:
                        st.success(f"✅ Product '{prod_name}' added successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add product. Please check the image URL and try again.")

    elif st.session_state.page == "Orders":
        # Add URL breadcrumb and navigation
        st.markdown(f"**🌐 URL:** `localhost:8501/?page=admin-orders`")
        
        # Quick navigation bar
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🔧 Admin", key="orders_admin"):
                navigate_to("admin")
        with col2:
            if st.button("👥 Customers", key="orders_customers"):
                navigate_to("customers")
        with col3:
            if st.button("📦 Products", key="orders_products"):
                navigate_to("products")
        with col4:
            if st.button("🛒 Orders", disabled=True):
                pass
        with col5:
            if st.button("🤖 ML Analytics", key="orders_ml"):
                navigate_to("ml")
        with col6:
            if st.button("🛍️ Shop", key="orders_shop"):
                navigate_to("shop")
        
        st.markdown("---")
        st.header("🛒 Order Management")
        st.markdown("---")
        
        # Fetch all orders
        orders = make_authenticated_request("GET", "/orders")
        if orders:
            st.subheader("📋 All Orders")
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "TEMP", "CLOSE", "PENDING", "PROCESSING", "SHIPPED", "DELIVERED"])
            with col2:
                sort_by = st.selectbox("Sort by", ["Order Date", "Total Amount", "Customer ID"])
            
            # Apply filters
            filtered_orders = orders
            if status_filter != "All":
                filtered_orders = [o for o in filtered_orders if o.get("status", "").upper() == status_filter]
            
            if filtered_orders:
                df = pd.DataFrame(filtered_orders)
                if not df.empty:
                    # Display order summary table
                    display_cols = ["id", "customer_id", "status", "total_amount", "order_date"]
                    available_cols = [col for col in display_cols if col in df.columns]
                    st.dataframe(df[available_cols], use_container_width=True)
                    
                    # Detailed order view
                    st.markdown("---")
                    st.subheader("🔍 Order Details")
                    order_ids = [str(o["id"]) for o in filtered_orders]
                    selected_order_id = st.selectbox("Select Order to View Details", order_ids)
                    
                    if selected_order_id:
                        selected_order = next((o for o in filtered_orders if str(o["id"]) == selected_order_id), None)
                        if selected_order:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Order ID", selected_order["id"])
                            with col2:
                                st.metric("Customer ID", selected_order.get("customer_id", "N/A"))
                            with col3:
                                st.metric("Status", selected_order.get("status", "N/A"))
                            
                            st.write(f"**Total Amount:** ${selected_order.get('total_amount', 0):.2f}")
                            st.write(f"**Order Date:** {selected_order.get('order_date', 'N/A')}")
                            
                            # Show customer shipping information
                            customer_info = selected_order.get('customer_info', {})
                            st.write(f"**Customer:** {customer_info.get('name', 'N/A')}")
                            st.write(f"**Shipping Address:** {customer_info.get('address', 'Not provided')}")
                            st.write(f"**Phone:** {customer_info.get('phone', 'Not provided')}")
                            
                            # Show order items
                            items = selected_order.get("items", [])
                            if items:
                                st.write("**Items:**")
                                items_df = pd.DataFrame(items)
                                st.dataframe(items_df, use_container_width=True)
                            else:
                                st.info("No items in this order.")
                else:
                    st.info("No orders found.")
            else:
                st.info(f"No orders found with status '{status_filter}'.")
        else:
            st.error("Failed to load orders.")
    
    elif st.session_state.page == "Users":
        # Add URL breadcrumb and navigation
        st.markdown(f"**🌐 URL:** `localhost:8501/?page=users`")
        
        # Quick navigation bar
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🔧 Admin", key="users_admin"):
                navigate_to("admin")
        with col2:
            if st.button("👥 Customers", key="users_customers"):
                navigate_to("customers")
        with col3:
            if st.button("📦 Products", key="users_products"):
                navigate_to("products")
        with col4:
            if st.button("🛒 Orders", key="users_orders"):
                navigate_to("admin-orders")
        with col5:
            if st.button("🤖 ML Analytics", key="users_ml"):
                navigate_to("ml")
        with col6:
            st.write("")  # Spacer
        
        st.markdown("---")
        
        st.header("👤 User Management")
        st.write("Manage user accounts and admin privileges.")
        
        # Fetch all users
        users = get_all_users()
        
        if users:
            st.subheader("📋 All Users")
            
            # Display users in a table format
            for user in users:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 2])
                    
                    with col1:
                        st.write(f"**{user.get('username')}**")
                        st.caption(f"ID: {user.get('id')}")
                    
                    with col2:
                        st.write(user.get('email', 'No email'))
                        st.caption(f"Created: {user.get('created_at', 'Unknown')[:10]}")
                    
                    with col3:
                        # Admin status
                        is_admin = user.get('is_admin', False)
                        if is_admin:
                            st.success("👑 Admin")
                        else:
                            st.info("👤 User")
                    
                    with col4:
                        # Active status
                        is_active = user.get('is_active', True)
                        if is_active:
                            st.success("✅ Active")
                        else:
                            st.error("❌ Inactive")
                    
                    with col5:
                        # Action buttons
                        user_id = user.get('id')
                        current_user_id = st.session_state.current_user.get('id')
                        
                        # Prevent admin from modifying themselves
                        if user_id != current_user_id:
                            col5a, col5b = st.columns(2)
                            
                            with col5a:
                                # Admin toggle
                                if is_admin:
                                    if st.button("🔻 Remove Admin", key=f"remove_admin_{user_id}", 
                                               help="Remove admin privileges"):
                                        if update_user_admin_status(user_id, False):
                                            st.success("Admin privileges removed!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update user")
                                else:
                                    if st.button("👑 Make Admin", key=f"make_admin_{user_id}",
                                               help="Grant admin privileges"):
                                        if update_user_admin_status(user_id, True):
                                            st.success("Admin privileges granted!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update user")
                            
                            with col5b:
                                # Active toggle
                                if is_active:
                                    if st.button("🚫 Deactivate", key=f"deactivate_{user_id}",
                                               help="Deactivate user account"):
                                        if update_user_active_status(user_id, False):
                                            st.success("User deactivated!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update user")
                                else:
                                    if st.button("✅ Activate", key=f"activate_{user_id}",
                                               help="Activate user account"):
                                        if update_user_active_status(user_id, True):
                                            st.success("User activated!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update user")
                        else:
                            st.info("(You)")
                    
                    st.markdown("---")
            
            # User statistics
            st.subheader("📊 User Statistics")
            total_users = len(users)
            admin_users = sum(1 for user in users if user.get('is_admin', False))
            active_users = sum(1 for user in users if user.get('is_active', True))
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Users", total_users)
            with col2:
                st.metric("Admin Users", admin_users)
            with col3:
                st.metric("Active Users", active_users)
            with col4:
                st.metric("Inactive Users", total_users - active_users)
        
        else:
            st.error("Failed to load users.")
    
    elif st.session_state.page == "ML":
        # Add URL breadcrumb and navigation
        st.markdown(f"**🌐 URL:** `localhost:8501/?page=ml`")
        
        # Quick navigation bar
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            if st.button("🔧 Admin", key="ml_admin"):
                navigate_to("admin")
        with col2:
            if st.button("👥 Customers", key="ml_customers"):
                navigate_to("customers")
        with col3:
            if st.button("📦 Products", key="ml_products"):
                navigate_to("products")
        with col4:
            if st.button("🛒 Orders", key="ml_orders"):
                navigate_to("admin-orders")
        with col5:
            if st.button("🤖 ML Analytics", disabled=True):
                pass
        with col6:
            if st.button("🛍️ Shop", key="ml_shop"):
                navigate_to("shop")
        
        st.markdown("---")
        
        # Machine Learning Analytics Dashboard
        st.markdown("### 🤖 Machine Learning Dashboard")
        
        # Debug information
        with st.expander("🔧 Debug Session State", expanded=False):
            st.write("**Current Authentication State:**")
            st.write(f"- logged_in: {st.session_state.get('logged_in', False)}")
            st.write(f"- current_user: {st.session_state.get('current_user', {})}")
            st.write(f"- access_token exists: {bool(st.session_state.get('access_token'))}")
            st.write(f"- is_admin_user(): {is_admin_user()}")
            st.write(f"- API_BASE_URL: {API_BASE_URL}")
            
            # Test API connectivity
            if st.button("🧪 Test API Connection"):
                try:
                    response = requests.get(f"{API_BASE_URL}/ml/health")
                    st.write(f"ML Health Check: {response.status_code} - {response.json()}")
                except Exception as e:
                    st.error(f"API Test Failed: {e}")
        
        if ML_DASHBOARD_AVAILABLE:
            show_ml_dashboard(API_BASE_URL)
        else:
            st.error("🚫 ML Dashboard not available")
            st.warning("The ML dashboard module could not be loaded. This may be due to missing dependencies.")
            st.info("To enable ML features, ensure all required packages are installed:")
            st.code("""
pip install plotly scikit-learn numpy
            """)
            
            if st.button("← Back to Dashboard", key="ml_unavailable_back"):
                navigate_to("admin")
    
    # Back to shop button
    st.markdown("---")
    if st.button("← Back to Shop", key="user_stats_back"):
        navigate_to("shop")