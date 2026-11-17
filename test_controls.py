
import sri_controls

print("SRI CONTROL TEST")
print("----------------")

while True:
    command = input("\nEnter a command: ")

    if command.lower() == "exit":
        break

    result = sri_controls.handle_command(command)

    if result:
        print("SRI:", result)
    else:
        print("SRI: Command not recognized.")
