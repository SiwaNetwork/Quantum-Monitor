import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog


def run_command(command):
    """Выполнение команды в терминале и возврат результата."""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Ошибка при выполнении команды: {command}\nВывод: {e.output.strip()}"


def do_info():
    messagebox.showinfo("Information", 
                        "This tool provides a straight-forward way of doing initial configuration of the Qantum Card. "
                        "Although it can be run at any time, some of the options may have difficulties if you have "
                        "heavily customised your installation.")


def do_device():
    result = run_command("lspci | grep 0x0400")
    if not result:
        messagebox.showinfo("Device Configuration", "No device found with code 0x0400.")
    else:
        messagebox.showinfo("Device Configuration", result)


def do_clock_sources():
    new_password = simpledialog.askstring("Clock Sources", "Enter a new password for the pi user:", show='*')
    if new_password:
        result = run_command(f"echo 'pi:{new_password}' | sudo chpasswd")
        messagebox.showinfo("Clock Sources", result)
    else:
        messagebox.showerror("Clock Sources", "No password entered.")


def do_peripherals():
    answer = messagebox.askyesno("Peripherals", "What would you like to do with overscan?", 
                                 icon='question', default='yes', detail="Click 'Yes' to disable, 'No' to enable.")
    action = 0 if answer else 1
    result = run_command(f"set_overscan {action}")
    messagebox.showinfo("Peripherals", result)


def do_signal_generators():
    result = run_command("sudo dpkg-reconfigure keyboard-configuration")
    messagebox.showinfo("Signal Generators", f"Reloading keymap. This may take a short while.\n{result}")


def do_other_settings():
    result = run_command("sudo dpkg-reconfigure locales")
    messagebox.showinfo("Other Settings", result)


def do_gnss_status():
    result = run_command("mountpoint -q /boot")
    if result == '':
        memsplit = simpledialog.askstring("GNSS Status", "Set memory split (224, 192, 128):", initialvalue="224")
        if memsplit in ["224", "192", "128"]:
            result = run_command(f"sudo cp -a /boot/arm{memsplit}_start.elf /boot/start.elf && sudo sync")
            messagebox.showinfo("GNSS Status", f"Memory split set to {memsplit} MiB.\n{result}")
        else:
            messagebox.showerror("GNSS Status", "Invalid memory split value.")
    else:
        messagebox.showerror("GNSS Status", "Error: /boot is not a mountpoint.")


def do_mac_status():
    result = run_command("grep -q '^finished' /var/log/regen_ssh_keys.log")
    if "finished" not in result:
        answer = messagebox.askyesno("MAC Status", "Would you like the SSH server enabled or disabled?", 
                                     icon='question', default='yes', detail="Click 'Yes' to enable, 'No' to disable.")
        action = "enable" if answer else "disable"
        result = run_command(f"sudo update-rc.d ssh {action} && sudo invoke-rc.d ssh start")
        messagebox.showinfo("MAC Status", f"SSH server {action}d.\n{result}")
    else:
        messagebox.showerror("MAC Status", "Initial SSH key generation still running. Please wait and try again.")


def do_timestampers():
    answer = messagebox.askyesno("Timestampers", "Should we boot straight to desktop?", icon='question')
    action = "enable" if answer else "disable"
    result = run_command(f"sudo update-rc.d lightdm {action} && sudo sed /etc/lightdm/lightdm.conf -i -e 's/^#autologin-user=.*/autologin-user=pi/'")
    messagebox.showinfo("Timestampers", result)


def do_update():
    result = run_command("sudo apt-get update && sudo apt-get install raspi-config")
    messagebox.showinfo("Update", f"To start raspi-config again, do 'sudo raspi-config'. Now exiting.\n{result}")


def do_finish():
    messagebox.showinfo("Finish", "Configuration complete. Rebooting now.")
    # Reboot can be uncommented if you want to perform automatic reboot.
    # result = run_command("sudo reboot")
    # messagebox.showinfo("Finish", f"System reboot initiated.\n{result}")


def main_menu():
    root = tk.Tk()
    root.title("Qantum Card Configurator")
    root.geometry("400x300")

    tk.Button(root, text="Info", command=do_info).pack(pady=5)
    tk.Button(root, text="Device", command=do_device).pack(pady=5)
    tk.Button(root, text="Clock Sources", command=do_clock_sources).pack(pady=5)
    tk.Button(root, text="Peripherals", command=do_peripherals).pack(pady=5)
    tk.Button(root, text="Signal Generators", command=do_signal_generators).pack(pady=5)
    tk.Button(root, text="Other Settings", command=do_other_settings).pack(pady=5)
    tk.Button(root, text="GNSS Status", command=do_gnss_status).pack(pady=5)
    tk.Button(root, text="MAC Status", command=do_mac_status).pack(pady=5)
    tk.Button(root, text="Timestampers", command=do_timestampers).pack(pady=5)
    tk.Button(root, text="Update", command=do_update).pack(pady=5)
    tk.Button(root, text="Finish", command=do_finish).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main_menu()
