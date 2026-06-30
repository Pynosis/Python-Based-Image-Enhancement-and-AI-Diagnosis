from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    print(f"\nFERNET_KEY={key}\n")