
import sys
import os
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("Commands:")
        print("  doctor   - Run data diagnosis and integrity check")
        print("  test     - Run all tests")
        sys.exit(1)

    command = sys.argv[1]

    if command == "doctor":
        print("Running Data Doctor...")
        subprocess.run([sys.executable, "scripts/diagnose_data.py"])
    elif command == "test":
        print("Running Tests...")
        subprocess.run([sys.executable, "-m", "pytest"])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
