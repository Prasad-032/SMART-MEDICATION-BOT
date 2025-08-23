import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from plyer import notification
import threading
import time
import json
import os
import requests
from datetime import datetime
import hashlib

# ----------- Global State -----------
medicine_list = []
confirmed_today = set()
last_reset_date = datetime.now().date()
logged_in_user = None
LOG_FILE = "confirmation_logs.json"
USERS_FILE = "users.json"
SYNC_INTERVAL = 300  # seconds (5 minutes)

# ----------- Utility Functions -----------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_file_if_missing(filename, initial_data):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        with open(filename, "w") as f:
            json.dump(initial_data, f)

def load_json_file(filename):
    init_file_if_missing(filename, [])
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(filename, "w") as f:
            json.dump([], f)
        return []

def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# ----------- User Management -----------

def load_users():
    return load_json_file(USERS_FILE)

def save_users(users):
    save_json_file(USERS_FILE, users)

def register_user(username, password):
    users = load_users()
    if any(u['username'] == username for u in users):
        return False, "Username already exists"
    hashed = hash_password(password)
    users.append({"username": username, "password": hashed})
    save_users(users)
    return True, "User registered successfully"

def login_user(username, password):
    users = load_users()
    hashed = hash_password(password)
    for u in users:
        if u['username'] == username and u['password'] == hashed:
            return True, u
    return False, "Invalid username or password"

# ----------- Confirmation Logging -----------

def init_log_file():
    init_file_if_missing(LOG_FILE, [])

def log_confirmation(name, method):
    if logged_in_user is None:
        return
    log = {
        "username": logged_in_user['username'],
        "medicine": name,
        "confirmed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "confirmed_by": method,
        "status": "taken"
    }
    data = load_json_file(LOG_FILE)
    data.append(log)
    save_json_file(LOG_FILE, data)

# ----------- Sync Data to Server -----------

def sync_data_to_server():
    while True:
        time.sleep(SYNC_INTERVAL)
        try:
            data = load_json_file(LOG_FILE)
            if not data:
                continue
            # Replace with your actual API endpoint
            response = requests.post("https://your-server.com/upload", json=data)
            if response.status_code == 200:
                print("✅ Data synced with server.")
                save_json_file(LOG_FILE, [])
        except Exception as e:
            print("🛑 Sync failed or offline:", e)

# ----------- Reminder & Notification -----------

def get_seconds(val, unit):
    return int(val) * {"Seconds": 1, "Minutes": 60, "Hours": 3600}.get(unit, 60)

def popup_confirm(med_index):
    def confirm_with_text():
        response = text_entry.get().strip().lower()
        if response == 'yes':
            medicine_list[med_index]["confirmed"] = True
            confirmed_today.add(medicine_list[med_index]["name"])
            log_confirmation(medicine_list[med_index]["name"], "text")
            popup.destroy()
            update_medicine_listbox()

    def confirm_with_image():
        file_path = filedialog.askopenfilename(title="Select Medicine Image")
        if file_path:
            medicine_list[med_index]["confirmed"] = True
            confirmed_today.add(medicine_list[med_index]["name"])
            medicine_list[med_index]["proof_image"] = file_path
            log_confirmation(medicine_list[med_index]["name"], "image")
            popup.destroy()
            update_medicine_listbox()

    popup = tk.Toplevel(root)
    popup.title(f"Confirm {medicine_list[med_index]['name']} Taken")
    popup.geometry("350x150")
    tk.Label(popup, text=f"Have you taken {medicine_list[med_index]['name']}?").pack(pady=5)
    text_entry = tk.Entry(popup)
    text_entry.pack(pady=5)
    tk.Button(popup, text="✔ Confirm by Typing 'yes'", command=confirm_with_text).pack(pady=5)
    tk.Button(popup, text="🖼 Confirm by Uploading Image", command=confirm_with_image).pack(pady=5)
    popup.grab_set()

def notify_and_confirm(med_index):
    med = medicine_list[med_index]
    notification.notify(
        title=f"Take {med['name']}",
        message=f"{med['meal']} meal medicine.\nConfirm intake.",
        timeout=10
    )
    root.after(0, lambda: popup_confirm(med_index))

def check_reminders():
    global confirmed_today, last_reset_date
    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        today = now.date()

        if today != last_reset_date:
            last_reset_date = today
            confirmed_today.clear()
            for med in medicine_list:
                med["confirmed"] = False
                med["last_notified_time"] = None
            root.after(0, update_medicine_listbox)
            print("✔ Daily reset complete.")

        for idx, med in enumerate(medicine_list):
            if med["confirmed"] or med["name"] in confirmed_today:
                continue
            if med["start"] <= current_time_str <= med["end"]:
                interval_secs = get_seconds(med["freq_value"], med["freq_unit"])
                last = med.get("last_notified_time")
                if last is None or (now - last).total_seconds() >= interval_secs:
                    med["last_notified_time"] = now
                    notify_and_confirm(idx)

        root.after(0, update_medicine_listbox)
        time.sleep(1)

# ----------- GUI Updates -----------

def update_medicine_listbox():
    listbox.delete(0, tk.END)
    now = datetime.now()
    for med in medicine_list:
        try:
            end_obj = datetime.strptime(med["end"], "%H:%M").replace(year=now.year, month=now.month, day=now.day)
            remaining = int((end_obj - now).total_seconds() // 60)
            if remaining > 0:
                status = f" | Ends in {remaining} min"
            else:
                status = " | Time Over"
        except:
            status = ""
        confirm = "✅" if med.get("confirmed", False) else "❌"
        listbox.insert(tk.END, f"{confirm} {med['name']} ({med['meal']}){status}")

def save_medicine():
    name = name_entry.get().strip()
    meal_type = meal_var.get()
    start = start_time_entry.get().strip()
    end = end_time_entry.get().strip()
    freq_val = freq_value_entry.get().strip()
    freq_unit = freq_unit_var.get()

    if not name or not start or not end or not freq_val:
        messagebox.showerror("Error", "All fields are required.")
        return

    # Validate time format HH:MM
    try:
        datetime.strptime(start, "%H:%M")
        datetime.strptime(end, "%H:%M")
    except ValueError:
        messagebox.showerror("Error", "Start and End time must be in HH:MM format.")
        return

    try:
        val = int(freq_val)
        if val <= 0:
            raise ValueError
    except:
        messagebox.showerror("Error", "Frequency must be a positive integer.")
        return

    # Prevent duplicates
    if any(m["name"] == name for m in medicine_list):
        messagebox.showerror("Error", "Medicine with this name already added.")
        return

    medicine_list.append({
        "name": name,
        "meal": meal_type,
        "start": start,
        "end": end,
        "confirmed": False,
        "last_notified_time": None,
        "freq_value": val,
        "freq_unit": freq_unit
    })
    update_medicine_listbox()
    messagebox.showinfo("Added", f"{name} added!")
    name_entry.delete(0, tk.END)
    start_time_entry.delete(0, tk.END)
    end_time_entry.delete(0, tk.END)
    freq_value_entry.delete(0, tk.END)

def disable_app_widgets():
    for w in root.winfo_children():
        # Only disable widgets that support 'state'
        try:
            w.config(state='disabled')
        except tk.TclError:
            pass
    listbox.config(state='disabled')
    btn_add.config(state='disabled')
    logout_btn.config(state='disabled')

def enable_app_widgets():
    for w in root.winfo_children():
        try:
            w.config(state='normal')
        except tk.TclError:
            pass
    listbox.config(state='normal')
    btn_add.config(state='normal')
    logout_btn.config(state='normal')

# ----------- Login / Register GUI -----------

def do_register():
    u = reg_user_entry.get().strip()
    p = reg_pass_entry.get().strip()
    if not u or not p:
        messagebox.showerror("Error", "Enter username and password")
        return
    success, msg = register_user(u, p)
    messagebox.showinfo("Register", msg)
    if success:
        reg_user_entry.delete(0, tk.END)
        reg_pass_entry.delete(0, tk.END)

def do_login():
    global logged_in_user, medicine_list
    u = login_user_entry.get().strip()
    p = login_pass_entry.get().strip()
    if not u or not p:
        messagebox.showerror("Error", "Enter username and password")
        return
    success, data = login_user(u, p)
    if success:
        logged_in_user = data
        messagebox.showinfo("Login", f"Welcome {u}!")
        # Load user's medicines or reset list
        medicine_list.clear()
        confirmed_today.clear()
        # Optionally: load medicines from file per user if implemented
        enable_app_widgets()
        login_frame.pack_forget()
        register_frame.pack_forget()
        app_frame.pack(fill="both", expand=True)
        update_medicine_listbox()
    else:
        messagebox.showerror("Login Failed", data)

def do_logout():
    global logged_in_user, medicine_list
    logged_in_user = None
    medicine_list.clear()
    confirmed_today.clear()
    disable_app_widgets()
    app_frame.pack_forget()
    login_frame.pack(fill="both", expand=True)
    register_frame.pack(fill="both", expand=True)
    messagebox.showinfo("Logout", "You have logged out.")

# ----------- Setup GUI -----------

root = tk.Tk()
root.title("Smart Medication Reminder")
root.geometry("520x600")

# Login Frame
login_frame = tk.Frame(root)
tk.Label(login_frame, text="Login", font=("Arial", 16)).pack(pady=5)
tk.Label(login_frame, text="Username").pack()
login_user_entry = tk.Entry(login_frame)
login_user_entry.pack()
tk.Label(login_frame, text="Password").pack()
login_pass_entry = tk.Entry(login_frame, show="*")
login_pass_entry.pack()
tk.Button(login_frame, text="Login", command=do_login).pack(pady=5)

# Register Frame
register_frame = tk.Frame(root)
tk.Label(register_frame, text="Register", font=("Arial", 16)).pack(pady=5)
tk.Label(register_frame, text="Username").pack()
reg_user_entry = tk.Entry(register_frame)
reg_user_entry.pack()
tk.Label(register_frame, text="Password").pack()
reg_pass_entry = tk.Entry(register_frame, show="*")
reg_pass_entry.pack()
tk.Button(register_frame, text="Register", command=do_register).pack(pady=5)

login_frame.pack(fill="both", expand=True)
register_frame.pack(fill="both", expand=True)

# Main App Frame
app_frame = tk.Frame(root)

tk.Label(app_frame, text="Medicine Name").pack()
name_entry = tk.Entry(app_frame)
name_entry.pack()

tk.Label(app_frame, text="Before or After Meal").pack()
meal_var = tk.StringVar(value="Before")
ttk.Combobox(app_frame, textvariable=meal_var, values=["Before", "After"]).pack()

tk.Label(app_frame, text="Start Time (HH:MM)").pack()
start_time_entry = tk.Entry(app_frame)
start_time_entry.pack()

tk.Label(app_frame, text="End Time (HH:MM)").pack()
end_time_entry = tk.Entry(app_frame)
end_time_entry.pack()

tk.Label(app_frame, text="Remind Every...").pack()
freq_frame = tk.Frame(app_frame)
freq_frame.pack()

freq_value_entry = tk.Entry(freq_frame, width=10)
freq_value_entry.pack(side=tk.LEFT)

freq_unit_var = tk.StringVar(value="Minutes")
ttk.Combobox(freq_frame, textvariable=freq_unit_var, values=["Seconds", "Minutes", "Hours"]).pack(side=tk.LEFT)

btn_add = tk.Button(app_frame, text="Add Reminder", command=save_medicine)
btn_add.pack(pady=10)

tk.Label(app_frame, text="Your Medication List").pack()
listbox = tk.Listbox(app_frame, width=60, height=12)
listbox.pack()

logout_btn = tk.Button(app_frame, text="Logout", command=do_logout)
logout_btn.pack(pady=10)

# Disable app widgets initially until login
disable_app_widgets()

# Init files
init_log_file()
init_file_if_missing(USERS_FILE, [])

# Start background threads
threading.Thread(target=check_reminders, daemon=True).start()
threading.Thread(target=sync_data_to_server, daemon=True).start()

root.mainloop()
