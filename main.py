import tkinter as tk
from tf2_obs_plugin import TF2OBSPlugin

def main():
    root = tk.Tk()
    app = TF2OBSPlugin(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()