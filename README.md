# 🔥 Bosch ME7.5 HardCut CMD

An open-source command-line utility for installing and configuring **Hard Cut Rev Limiter** on **Bosch ME7.5 (1MB)** ECUs.

The application automatically detects the required HardCut calibration data, allows you to select the desired RPM limit, applies all necessary modifications, and saves the patched firmware as a new BIN file without overwriting the original.

---

# ✨ Features

* ✅ Automatic HardCut detection
* ✅ Supports Bosch **ME7.5 (1MB)** ECUs
* ✅ RPM limiter selection:

  * 6400 RPM
  * 6500 RPM
  * 6600 RPM
  * 6700 RPM
  * 6800 RPM
  * 6900 RPM
  * 7000 RPM
  * 7100 RPM
  * 7200 RPM
* ✅ Automatic variant detection
* ✅ ECU information display
* ✅ Detailed modification log
* ✅ Original BIN is never overwritten
* ✅ Command-line interface
* ✅ Open Source

---

# 🚀 Usage

Run the application from the command line:

```bash
HardCut_ME75_CMD.exe
```

or

```bash
python HardCut_ME75_CMD.py your_file.bin
```

The program will:

1. Load the BIN file.
2. Read ECU information.
3. Detect the correct HardCut variant.
4. Allow you to select the desired RPM limiter.
5. Apply all required HardCut modifications.
6. Save a new modified BIN.
7. Generate a detailed modification log.

---

# 📄 Output

The original file is never modified.

Example output:

```
your_file_HARDCUT_7200.bin
your_file_HARDCUT_7200.bin.log.txt
```

---

# ⚠️ Checksum

The application **does not correct ECU checksums**.

Before flashing the ECU, the modified BIN **must be checksum corrected** using the appropriate checksum tool.

---

# 📜 License

This project is released as **Open Source**.

Feel free to improve, modify and contribute.
