import pyduinocli
import os
import sys

# Get the directory where the current Python script is located
python_script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

# Initialize pyduinocli.Arduino (adjust path to arduino-cli if necessary)
# If arduino-cli is in your system PATH, you might not need to specify the path.
arduino = pyduinocli.Arduino("./arduino-cli") # Or simply pyduinocli.Arduino()

# Define your sketch path
sketch_path = r"C:\Users\Pintu\Documents\Arduino\sync_test"

# Define the FQBN for Arduino Uno
fqbn = "arduino:avr:uno"

# Define the output directory to be the same as the Python script's directory
output_directory = python_script_dir

try:
    print(f"Compiling sketch: {sketch_path} for board: {fqbn}")
    print(f"Saving compiled output to: {output_directory}")

    # Compile the sketch, specifying the output directory
    compile_result = arduino.compile(fqbn=fqbn, sketch=sketch_path, output_dir=output_directory)

    print("Compilation successful!")
    # The 'compile_result' object might contain useful information,
    # but the primary goal here is to check for the file.

    # Construct the likely name of the .hex file
    # It's usually based on the sketch folder name or the .ino file name
    sketch_name = os.path.basename(sketch_path) # Gets "simple_serial"
    hex_file_name = f"{sketch_name}.ino.hex"    # Results in "simple_serial.ino.hex"
    hex_file_path = os.path.join(output_directory, hex_file_name)

    if os.path.exists(hex_file_path):
        print(f"Hex file found at: {hex_file_path}")
    else:
        print(f"Hex file NOT found at the expected path: {hex_file_path}. "
              "Check the 'output_dir' parameter and arduino-cli behavior.")

except pyduinocli.errors.arduinoerror.ArduinoError as e:
    print(f"Compilation failed: {e}")
    # You can parse e.__stdout__ for more detailed compiler errors
    # For example: print(e.__stdout__['compiler_err'])
except Exception as e:
    print(f"An unexpected error occurred: {e}")