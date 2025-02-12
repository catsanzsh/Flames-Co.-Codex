import subprocess
import threading
import requests
import psutil
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# Ensure LM Studio's CLI is available. If not, inform the user.
# (In a real scenario, you might check `shutil.which("lms")` and prompt to install via `npx lmstudio install-cli` if missing.)

# LM Studio server default configuration
LMSTUDIO_PORT = 1234  # default port for LM Studio API server
API_BASE_URL = f"http://localhost:{LMSTUDIO_PORT}/v1"

# Global state variables
server_running = False
current_model = None
started_server_this_session = False

# Initialize main application window
root = tk.Tk()
root.title("LM Studio Controller")
root.geometry("600x500")  # width x height
root.resizable(False, False)  # fixed window size for simplicity

# Define GUI elements
status_label = tk.Label(root, text="Server Status: Stopped", fg="red")
start_button = tk.Button(root, text="Start Server")
stop_button = tk.Button(root, text="Stop Server")
model_label = tk.Label(root, text="Model:")
# We'll use ttk.Combobox for model selection dropdown
model_var = tk.StringVar()
model_combo = ttk.Combobox(root, textvariable=model_var, state="readonly")  # read-only dropdown
load_button = tk.Button(root, text="Load Model")
prompt_label = tk.Label(root, text="Prompt:")
prompt_text = scrolledtext.ScrolledText(root, height=5, width=70)
run_button = tk.Button(root, text="Run Query")
output_label = tk.Label(root, text="Response:")
output_text = scrolledtext.ScrolledText(root, height=10, width=70)
output_text.configure(state="disabled")  # make output read-only initially
# Labels for resource usage and tips
usage_label = tk.Label(root, text="CPU: 0%   Memory: 0%")
tip_label = tk.Label(root, text="", fg="orange")  # will display performance tips when needed

# Place GUI elements using grid geometry for a structured layout
status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
start_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")
stop_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

model_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
model_combo.grid(row=1, column=1, padx=5, pady=5, sticky="we", columnspan=2)
load_button.grid(row=1, column=3, padx=5, pady=5, sticky="w")

prompt_label.grid(row=2, column=0, padx=5, pady=(10,5), sticky="ne")
prompt_text.grid(row=2, column=1, padx=5, pady=(10,5), columnspan=3)
run_button.grid(row=3, column=3, padx=5, pady=5, sticky="e")

output_label.grid(row=4, column=0, padx=5, pady=(10,5), sticky="nw")
output_text.grid(row=4, column=1, padx=5, pady=(10,5), columnspan=3)

usage_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
tip_label.grid(row=5, column=1, padx=5, pady=5, columnspan=3, sticky="w")

# Configure some widget options
start_button.configure(width=10)
stop_button.configure(width=10)
load_button.configure(width=10)
run_button.configure(width=10)
# Initially, until server is running and a model is loaded, disable certain buttons
load_button.config(state="disabled")
run_button.config(state="disabled")
stop_button.config(state="disabled")

# Function to update the model dropdown with available models
def refresh_model_list():
    try:
        # Use the LM Studio CLI to list models in JSON for easy parsing
        result = subprocess.run(["lms", "ls", "--json"], capture_output=True, text=True)
        model_list = []
        if result.returncode == 0:
            import json
            try:
                data = json.loads(result.stdout)
                # Assuming data is a list of models with 'filename' or 'name' field
                for m in data:
                    # Some JSON entries might have 'name' or 'filename'; handle accordingly
                    name = m.get("name") or m.get("filename") or str(m)
                    model_list.append(name)
            except json.JSONDecodeError:
                # If JSON parsing failed, fallback to plain text parsing
                lines = result.stdout.strip().splitlines()
                for line in lines:
                    # ignore empty lines or header lines if any
                    if line.strip() and "Models directory" not in line:
                        # Take the first token or whole line as model name (assuming name is one word or rest of line)
                        model_name = line.split(":")[0]  # split at ':' if output like 'ModelName: ...'
                        model_list.append(model_name.strip())
        else:
            # If the CLI returned an error (perhaps --json not supported), try without JSON
            result = subprocess.run(["lms", "ls"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                for line in lines:
                    if line.strip() and "Models directory" not in line:
                        model_name = line.split(":")[0]
                        model_list.append(model_name.strip())
    except FileNotFoundError:
        messagebox.showerror("LM Studio CLI not found", 
            "The 'lms' CLI tool for LM Studio is not found. Please ensure LM Studio is installed and the CLI is set up.")
        return []

    # Update the combobox values
    model_combo['values'] = model_list
    if model_list:
        model_combo.current(0)  # pre-select the first model by default
    return model_list

# Function to start the LM Studio server
def start_server():
    global server_running, started_server_this_session
    # Double-check if not already running
    try:
        status_res = subprocess.run(["lms", "server", "status"], capture_output=True, text=True)
        if "ON" in status_res.stdout or "running" in status_res.stdout:
            # Server already running
            server_running = True
        else:
            # Launch the server
            status_label.config(text="Server Status: Starting...", fg="orange")
            root.update_idletasks()
            result = subprocess.run(["lms", "server", "start"], capture_output=True, text=True)
            # Check output for confirmation
            if result.returncode == 0 and ("now running" in result.stdout or "ON" in result.stdout):
                server_running = True
                started_server_this_session = True
            else:
                # Failed to start – show error
                server_running = False
                err_msg = result.stderr if result.stderr else result.stdout
                messagebox.showerror("Server Start Failed", f"Could not start LM Studio server.\nOutput: {err_msg}")
                status_label.config(text="Server Status: Stopped", fg="red")
                return
    except FileNotFoundError:
        messagebox.showerror("LM Studio CLI not found", 
            "Cannot start server because 'lms' CLI was not found. Ensure LM Studio is installed.")
        return

    if server_running:
        status_label.config(text="Server Status: Running", fg="green")
        # Now that server is on, enable model loading
        load_button.config(state="normal")
        stop_button.config(state="normal")
        # Populate model list
        refresh_model_list()
    else:
        status_label.config(text="Server Status: Stopped", fg="red")

# Function to stop the LM Studio server
def stop_server():
    global server_running, started_server_this_session, current_model
    try:
        result = subprocess.run(["lms", "server", "stop"], capture_output=True, text=True)
        # Assume if returncode 0, it's stopped
        server_running = False
        current_model = None
        status_label.config(text="Server Status: Stopped", fg="red")
        load_button.config(state="disabled")
        run_button.config(state="disabled")
        stop_button.config(state="disabled")
    except FileNotFoundError:
        messagebox.showerror("LM Studio CLI not found", "Cannot stop server because 'lms' CLI was not found.")

# Background thread target for loading a model
def load_model_thread(model_name):
    global current_model
    # Unload any currently loaded model first (to free memory)
    try:
        if current_model:
            subprocess.run(["lms", "unload", current_model], capture_output=True, text=True)
    except FileNotFoundError:
        pass  # If CLI not found, error already handled earlier
    # Load the new model with GPU acceleration
    try:
        # The -y flag auto-confirms and uses max GPU by default (per LM Studio CLI docs)
        result = subprocess.run(["lms", "load", model_name, "-y"], capture_output=True, text=True)
    except FileNotFoundError:
        root.after(0, lambda: messagebox.showerror("LM Studio CLI not found", 
                     "Cannot load model because 'lms' CLI was not found."))
        return

    if result.returncode != 0:
        # Loading failed, show error (possibly model not found or other issue)
        err = result.stderr if result.stderr else result.stdout
        root.after(0, lambda: messagebox.showerror("Model Load Failed", f"Could not load model '{model_name}'.\nDetails: {err}"))
        root.after(0, lambda: status_label.config(text="Server Status: Running (Model load failed)", fg="orange"))
        return

    # If success, set current_model and update UI
    current_model = model_name
    root.after(0, lambda: status_label.config(text=f"Server Status: Running - Model: {model_name}", fg="green"))
    root.after(0, lambda: run_button.config(state="normal"))  # enable query button now that model is loaded

# Function to initiate model loading in a thread
def load_model():
    model_name = model_var.get().strip()
    if not model_name:
        return  # no model selected
    # Disable UI elements related to model loading and querying while loading
    load_button.config(state="disabled")
    run_button.config(state="disabled")
    status_label.config(text=f"Server Status: Running - Loading '{model_name}'...", fg="orange")
    # Start background thread to load model
    threading.Thread(target=load_model_thread, args=(model_name,), daemon=True).start()

# Background thread target for running an inference query
def run_query_thread(prompt):
    global current_model
    # Prepare request payload for completion
    payload = {
        "model": current_model or "",  # model field; LM Studio uses the loaded model anyway
        "prompt": prompt,
        "max_tokens": 100,
        "temperature": 0.7,
        # You can add other OpenAI-compatible parameters here if needed (top_p, etc.)
    }
    headers = {"Content-Type": "application/json"}
    # Use a dummy API key as LM Studio does not require a real key (OpenAI compatibility)
    headers["Authorization"] = "Bearer lm-studio"
    try:
        # Measure start time
        import time
        start_time = time.time()
        resp = requests.post(f"{API_BASE_URL}/completions", json=payload, headers=headers)
        elapsed = time.time() - start_time
    except Exception as e:
        # If request fails (e.g., server not responding), show an error in the GUI
        root.after(0, lambda: messagebox.showerror("Query Failed", f"Failed to get response from model:\n{e}"))
        root.after(0, lambda: run_button.config(state="normal"))
        return

    if resp.status_code != 200:
        # API returned an error
        err_msg = resp.text
        root.after(0, lambda: messagebox.showerror("Query Error", f"Model returned an error:\n{err_msg}"))
        root.after(0, lambda: run_button.config(state="normal"))
        return

    # Parse the response assuming OpenAI-like format
    result_text = ""
    try:
        data = resp.json()
        # The completion text might be in different fields depending on model (choices[0].text for completion models, or choices[0].message.content for chat models)
        if "choices" in data:
            choices = data["choices"]
            if choices:
                choice = choices[0]
                if "text" in choice:
                    result_text = choice["text"]
                elif "message" in choice and "content" in choice["message"]:
                    result_text = choice["message"]["content"]
    except ValueError:
        # Not JSON or unexpected format
        result_text = resp.text

    # Define a function to update the output UI, to be called in main thread
    def update_output(text, latency):
        # Insert the result into output_text widget
        output_text.configure(state="normal")
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, text.strip())
        output_text.configure(state="disabled")
        # Re-enable the Run button for new queries
        run_button.config(state="normal")
        # Provide a performance tip if needed based on latency or usage
        if latency > 5.0:
            tip_label.config(text="Tip: The response took quite long. Consider a smaller model for faster replies.")
        else:
            tip_label.config(text="")  # clear tip if not needed

    # Schedule the UI update on the main thread
    root.after(0, lambda: update_output(result_text, elapsed))

# Function to initiate a query
def run_query():
    prompt = prompt_text.get("1.0", tk.END).strip()
    if not prompt:
        return  # no prompt entered
    # Disable the Run button to prevent multiple simultaneous queries
    run_button.config(state="disabled")
    # Optionally, show a status or spinner (not implemented here for brevity)
    # Start the inference in a background thread
    threading.Thread(target=run_query_thread, args=(prompt,), daemon=True).start()

# Function to periodically update CPU and memory usage in the GUI
def update_usage():
    # Get system CPU and memory usage
    cpu_percent = psutil.cpu_percent(interval=0)  # non-blocking call (since we call it periodically)
    mem = psutil.virtual_memory()
    mem_percent = mem.percent
    # Format memory usage (used/total in GB)
    used_gb = mem.used / (1024**3)
    total_gb = mem.total / (1024**3)
    usage_label.config(text=f"CPU: {cpu_percent:.0f}%   Memory: {used_gb:.1f}/{total_gb:.1f} GB ({mem_percent:.0f}%)")
    # Schedule the next update
    root.after(1000, update_usage)

# Tie the GUI buttons to their functions
start_button.config(command=start_server)
stop_button.config(command=stop_server)
load_button.config(command=load_model)
run_button.config(command=run_query)

# Immediately refresh model list (in case server is already running when script starts)
# If server is running, enable load and stop controls; if not, models list will populate after start.
available_models = refresh_model_list()
if available_models:
    # It appears server might already be running (since we could list models), update status
    server_running = True
    status_label.config(text="Server Status: Running", fg="green")
    stop_button.config(state="normal")
    load_button.config(state="normal")
else:
    # No models listed (maybe server not running yet)
    server_running = False

# Start the resource usage updater loop
root.after(1000, update_usage)

# Handle window close event to stop server if we started it
def on_close():
    if started_server_this_session:
        try:
            subprocess.run(["lms", "server", "stop"], capture_output=True)
        except Exception:
            pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# Launch the Tkinter event loop
root.mainloop()
