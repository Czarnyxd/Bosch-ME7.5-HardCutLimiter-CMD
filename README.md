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

# 🚧 Work in Progress

Support for additional Bosch VAG ECUs is currently under development.

Planned and currently implemented detection includes:

- ✅ BOSCH VAG ME3.8.3
- ✅ BOSCH VAG ME7.1 2.7T V6
- ✅ BOSCH VAG ME7.1 4.2 V8
- ✅ BOSCH VAG ME7.1.1 1.8T 20V
- ✅ BOSCH VAG ME7.1.1 3.2 VR6 / R32
- ✅ BOSCH VAG MED9.1 2.0 TFSI
- ✅ BOSCH VAG MED9.1 RS3

Future releases will gradually add full HardCut support for these ECU families.

---

# 🚀 Usage

Run the application from the command line:

```bash
HardCut_ME75_CMD.exe your_file.bin
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



---

<h2 align="center">❤️ Want to say thank you?</h2>

<p align="center">
If this project helped you and you would like to show your appreciation,<br>
<strong>there is no need to support me financially.</strong>
</p>

<p align="center">
Instead, if you are willing and able, please consider supporting organizations<br>
that help children and people fighting serious illnesses.
</p>

<table align="center">
<tr>
<td align="center">

<a href="https://www.siepomaga.pl/">
<img src="https://img.shields.io/badge/SUPPORT-SIEPOMAGA.PL-ff4f81?style=for-the-badge" alt="Support Siepomaga.pl">
</a>

</td>
<td align="center">

<a href="https://cancerfighters.pl/">
<img src="https://img.shields.io/badge/SUPPORT-CANCER%20FIGHTERS-e30613?style=for-the-badge" alt="Support Cancer Fighters">
</a>

</td>
</tr>
</table>

<p align="center">
<strong>Thank you for using my project. ❤️</strong><br><br>
If it helped you, consider helping someone who truly needs it.<br>
Even a small contribution can make a meaningful difference.
</p>

---

