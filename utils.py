import os
import socket


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()

    return ip


def get_file_from_log_line(log_line):
    return log_line.strip("\n").split(" ")[-1]


def cleanup_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        return ("error", f"NOT FOUND FILE {path}")
    except PermissionError:
        return ("error", f"NO PERMISSION TO REMOVE {path}")

    return ("info", f"REMOVED - {path}")
