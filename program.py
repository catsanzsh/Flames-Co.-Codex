import os
import subprocess
import queue
import requests
import tkinter as tk
from tkinter import messagebox, Scrollbar, Text, Button, Frame, Entry, OptionMenu, StringVar, Label
import threading
import time

from crewai import Agent, Task, Crew, Process

# ===================== Configuration: LM Studio API =======================
LMSTUDIO_API_URL = "http://localhost:1234/v1"  # LM Studio API URL

current_model = None
server_process = None  # Store the server process
continuous_task_thread = None
stop_continuous_task = threading.Event()

# ===================== Start LM Studio API Server =========================
def start_lm_studio_server():
    """Start LM Studio API server automatically."""
    global server_process
    if server_process is None or server_process.poll() is not None:  # Check if server is already running
        try:
            # Launch the LM Studio server in the background
            server_process = subprocess.Popen(
                ["lmstudio", "--port", "1234"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True if os.name == "nt" else False,
            )
            time.sleep(5)  # Wait a few seconds for the server to start
            print("LM Studio server started.")
            return server_process
        except FileNotFoundError:
            print("Error: 'lmstudio' command not found. Make sure LM Studio is installed and in your PATH.")
            messagebox.showerror("Error", "LM Studio executable ('lmstudio') not found. Ensure it's installed and in your PATH.")
            return None
        except Exception as e:
            print(f"Failed to start LM Studio API server: {e}")
            messagebox.showerror("Error", f"Failed to start LM Studio API server: {e}")
            return None
    else:
        print("LM Studio server is already running.")
        return server_process

def stop_lm_studio_server():
    """Stop the LM Studio API server."""
    global server_process
    if server_process:
        try:
            server_process.terminate()
            server_process.wait(5)
            if server_process.poll() is None:
                server_process.kill()
            print("LM Studio server stopped.")
            server_process = None
        except Exception as e:
            print(f"Error stopping LM Studio server: {e}")

# ===================== Agent Definitions =========================
class ResearcherAgent:
    def __init__(self):
        self.agent = Agent(
            role='Senior Research Analyst',
            goal='Uncover cutting-edge developments in AI and machine learning',
            backstory="""You are a Senior Research Analyst at a leading tech think tank.
            Your expertise lies in identifying emerging trends and technologies in AI.
            You have a knack for sifting through vast amounts of information to find the most relevant and impactful insights.""",
            verbose=True,
            allow_delegation=False,
            llm=current_model,
            max_iter=10,
        )

class WriterAgent:
    def __init__(self):
        self.agent = Agent(
            role='Tech Content Strategist',
            goal='Craft compelling and informative blog posts about AI advancements',
            backstory="""You are a Tech Content Strategist at a popular AI-focused blog.
            You have a talent for translating complex technical topics into engaging and accessible content for a broad audience.
            You work closely with researchers to create content that informs and inspires.""",
            verbose=True,
            allow_delegation=False,
            llm=current_model,
            max_iter=10
        )

# ===================== Model Management =======================
def load_available_models():
    """Fetches the list of available models from the LM Studio /models API."""
    try:
        response = requests.get(f"{LMSTUDIO_API_URL}/models")
        response.raise_for_status()
        models_data = response.json()['data']
        return [model['id'] for model in models_data]
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not load models from LM Studio: {e}")
        return []
    except (KeyError, ValueError) as e:
        messagebox.showerror("Error", f"Error parsing LM Studio response: {e}")
        return []

def set_model(model_name):
    """Sets the global current_model for use in agents."""
    global current_model
    current_model = model_name
    print(f"Model set to: {current_model}")

# ===================== Continuous Task Management =======================
def create_dump_directory():
    """Create the /dumps directory if it doesn't exist."""
    dump_dir = os.path.join(os.path.dirname(__file__), 'dumps')
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)
    return dump_dir

def continuous_task(user_query):
    """Performs the task continuously until stopped."""
    global stop_continuous_task
    dump_dir = create_dump_directory()
    counter = 0

    while not stop_continuous_task.is_set():
        try:
            researcher = ResearcherAgent()
            writer = WriterAgent()

            crew = Crew(
                agents=[researcher.agent, writer.agent],
                tasks=[
                    Task(
                        description=f"Research this topic: {user_query}",
                        agent=researcher.agent,
                    ),
                    Task(
                        description=f"Write a compelling summary of the research on: {user_query}",
                        agent=writer.agent,
                        expected_output="A well-written, concise summary suitable for a blog post."
                    )
                ],
                process=Process.sequential,
                verbose=2
            )
            result = crew.kickoff()

            # Write result to a file
            file_path = os.path.join(dump_dir, f"output_{counter}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result)

            counter += 1
            time.sleep(60)  # Wait for a minute before next execution
        except Exception as e:
            append_chat("System", f"Error in continuous workflow: {e}\n")
            time.sleep(60)  # Wait before retrying in case of error

def start_continuous_task():
    """Starts the continuous task."""
    global continuous_task_thread, stop_continuous_task
    if continuous_task_thread is None or not continuous_task_thread.is_alive():
        stop_continuous_task.clear()
        user_query = user_input.get()
        if not user_query:
            messagebox.showwarning("Warning", "Please enter a query before starting the continuous task.")
            return
        continuous_task_thread = threading.Thread(target=continuous_task, args=(user_query,), daemon=True)
        continuous_task_thread.start()
        append_chat("System", "Continuous task started.\n")

def stop_continuous_task_func():
    """Stops the continuous task."""
    global stop_continuous_task, continuous_task_thread
    if continuous_task_thread and continuous_task_thread.is_alive():
        stop_continuous_task.set()
        continuous_task_thread.join()
        append_chat("System", "Continuous task stopped.\n")
    else:
        messagebox.showinfo("Info", "No continuous task running.")

# ===================== GUI Setup (Tkinter) =======================
root = tk.Tk()
root.title("CatGPT V0")

# Top frame for model controls and server management
top_frame = Frame(root)
top_frame.pack(side="top", fill="x", padx=5, pady=5)

# Model selection
model_label = Label(top_frame, text="Model:")
model_label.pack(side="left", padx=5)

model_var = StringVar(root)
model_dropdown = OptionMenu(top_frame, model_var, *["Select Model"])
model_dropdown.pack(side="left", padx=5)

def refresh_models(*args):
    """Refreshes the model list in the dropdown."""
    models = load_available_models()
    menu = model_dropdown["menu"]
    menu.delete(0, "end")
    for model in models:
        menu.add_command(label=model, command=lambda value=model: model_var.set(value))
    if models:
        model_var.set(models[0])  # Set default selection
model_var.trace('w', refresh_models)

# Set Model Button
set_model_button = Button(top_frame, text="Set Model", command=lambda: set_model(model_var.get()))
set_model_button.pack(side="left", padx=5)

# Start/Stop Server Button
server_button = Button(top_frame, text="Start Server", command=start_lm_studio_server)
server_button.pack(side="left", padx=5)

stop_server_button = Button(top_frame, text="Stop Server", command=stop_lm_studio_server)
stop_server_button.pack(side="left", padx=5)

# Main chat area
chat_frame = Frame(root)
chat_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

chat_log = Text(chat_frame, state="disabled", wrap="word", width=80, height=20)
chat_log.pack(side="left", fill="both", expand=True)

scrollbar = Scrollbar(chat_frame, command=chat_log.yview)
scrollbar.pack(side="right", fill="y")
chat_log["yscrollcommand"] = scrollbar.set

# Input area
input_frame = Frame(root)
input_frame.pack(side="bottom", fill="x", padx=5, pady=5)

user_input = Entry(input_frame, width=60)
user_input.pack(side="left", fill="x", expand=True, padx=5)

def send_message():
    """Sends the user's message and initiates the autonomous workflow."""
    message = user_input.get()
    if message:
        append_chat("You", message + "\n")
        user_input.delete(0, tk.END)
        threading.Thread(target=run_autonomous_workflow, args=(message,), daemon=True).start()

send_button = Button(input_frame, text="Send", command=send_message)
send_button.pack(side="left", padx=5)

def append_chat(speaker, message):
    chat_log.configure(state="normal")
    chat_log.insert(tk.END, f"{speaker}: {message}")
    chat_log.configure(state="disabled")
    chat_log.yview(tk.END)

# Continuous task buttons
continuous_task_frame = Frame(input_frame)
continuous_task_frame.pack(side="right", padx=5)

start_button = Button(continuous_task_frame, text="Run Forever", command=start_continuous_task)
start_button.pack(side="left")

stop_button = Button(continuous_task_frame, text="Stop", command=stop_continuous_task_func)
stop_button.pack(side="left")

# ===================== Autonomous Workflow =====================
def run_autonomous_workflow(user_query):
    """Runs the researcher and writer agents in sequence."""
    if not current_model:
        messagebox.showerror("Error", "Please select a model before running the workflow.")
        return

    try:
        researcher = ResearcherAgent()
        writer = WriterAgent()

        crew = Crew(
            agents=[researcher.agent, writer.agent],
            tasks=[
                Task(
                    description=f"Research this topic: {user_query}",
                    agent=researcher.agent,
                ),
                Task(
                    description=f"Write a compelling summary of the research on: {user_query}",
                    agent=writer.agent,
                    expected_output="A well-written, concise summary suitable for a blog post."
                )
            ],
            process=Process.sequential,
            verbose=2
        )
        result = crew.kickoff()
        append_chat("CrewAI", result + "\n")

    except Exception as e:
        append_chat("System", f"Error in autonomous workflow: {e}\n")

# ===================== Main Event Loop =========================
def on_closing():
    stop_lm_studio_server()  # Ensure server is closed before closing the window
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

refresh_models()  # Load models on startup
root.mainloop()
