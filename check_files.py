import os

print("--- Ordner-Check ---")
print(f"Aktueller Pfad: {os.getcwd()}")
print("\nGefundene Dateien:")
for file in os.listdir():
    print(f" - {file}")
print("--------------------")
input("\nDrücke Enter zum Beenden...")