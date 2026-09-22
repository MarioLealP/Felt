import socket
import json
import time

def send_msg(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 8765))
        s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
        s.close()
    except Exception as e:
        print("Failed to send:", e)

def main():
    print("Sending garment override...")
    send_msg({
        "garment": {
            "material": "N00_004_01_Tops_01_CLOTH",
            "albedo": "E:/Felt/tools/outfits/debug_tee.png"
        }
    })
    time.sleep(0.5)
    print("Sending screenshot request...")
    send_msg({"screenshot": True})
    print("Done")

if __name__ == "__main__":
    main()
