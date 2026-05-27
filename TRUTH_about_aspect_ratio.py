#!/usr/bin/env python3
"""
DEFINITIVE ANSWER: What is the STANDARD character for aspect_ratio in Fooocus?

TRUTH: The standard is Unicode MULTIPLICATION SIGN: × (U+00D7)

Evidence from source code:
"""

print("=" * 70)
print("THE TRUTH ABOUT FOOOCUS ASPECT_RATIO FORMAT")
print("=" * 70)

# Show the actual character codes
formats = {
    "ASCII asterisk (*)": "*",
    "Letter x (x)": "x",
    "Unicode multiplication sign (×)": "\u00d7",  # This is the REAL one
}

print("\n[CHARACTER CODES]")
for name, char in formats.items():
    code_point = hex(ord(char))
    print(f"  {name:40} -> '{char}' U+{code_point[2:].upper()}")

print("\n" + "-" * 70)
print("EVIDENCE FROM FOOOCUS SOURCE CODE")
print("-" * 70)

print("""
FILE: modules/flags.py (Line 101-106)
----------------------------------------
INTERNAL STORAGE uses * (asterisk):
    sdxl_aspect_ratios = [
        '1152*896', '1024*1024', ...  # <-- Stored with *
    ]

FILE: modules/config.py (Line 767-771)
----------------------------------------
add_ratio() CONVERTS * to × for UI display:
    def add_ratio(x):
        a, b = x.replace('*', ' ').split(' ')[:2]  # Parse the * format
        return f'{a}×{b} <span>...</span>'          # Output with × (U+00D7)!

FILE: webui.py (Line 572-574)
----------------------------------------
GRADIO UI CHOICES use × (from add_ratio conversion):
    aspect_ratios_selection = gr.Radio(
        choices=modules.config.available_aspect_ratios_labels,  # These have ×!
        value=modules.config.default_aspect_ratio,              # This has ×!
        info='width × height'                                   # Even the label has ×!
    )

FILE: modules/async_worker.py (Line 1118)
----------------------------------------
HANDLER PARSING expects × (U+00D7):
    width, height = async_task.aspect_ratios_selection.replace('×', ' ').split(' ')[:2]
                                                    ^^^^
                                                    THIS IS THE STANDARD!
""")

print("-" * 70)
print("DATA FLOW (The Complete Picture)")
print("-" * 70)

flow = """
Step 1: config.py stores internally
        "1152*896"  (with ASCII *)

            |
            v  [add_ratio() conversion]

Step 2: webui.py displays in Gradio UI
        "1152×896  ∷ 23:18"  (with Unicode ×)

            |
            v  [User selects in UI]

Step 3: Gradio returns selected value to backend
        "1152×896  ∷ 23:18"  (still with Unicode ×)

            |
            v  [get_task() -> AsyncTask()]

Step 4: async_worker.py handler receives it
        async_task.aspect_ratios_selection = "1152×896  ∷ 23:18"

            |
            v  [Line 1118: .replace('×', ' ')]

Step 5: Handler parses successfully!
        width, height = "1152", "896"  [SUCCESS!]
"""

print(flow)

print("-" * 70)
print("CONCLUSION")
print("-" * 70)

conclusion = """
THERE IS ONLY ONE STANDARD CHARACTER FOR THE HANDLER:

    Unicode MULTIPLICATION SIGN: × (U+00D7)

NOT:
    - * (ASCII asterisk, code 0x2A)  <- Only for internal storage
    - x (Latin letter x, code 0x78)  <- NEVER used in Fooocus

WHY THE CONFUSION?
------------------
1. Internal config files use * (easy for programming)
2. add_ratio() converts * to × for display
3. Handler only sees what comes from UI (which has ×)
4. Our API bypassed the UI, so we must do the conversion ourselves!

OUR FIX (in api_server.py):
---------------------------
User sends:     "1024*1024"  (easy to type)
                    |
                    v  .replace('*', '\\u00d7')
Handler gets:   "1024×1024"  (standard format!)
                    |
                    v  .replace('×', ' ')
Result:         width=1024, height=1024  [WORKS!]
"""

print(conclusion)

print("=" * 70)
print("[ANSWER] The standard is: Unicode MULTIPLICATION SIGN (×) U+00D7")
print("=" * 70)
