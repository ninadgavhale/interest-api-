"""
main.py
Simple mobile-like calculator (Tkinter) with:
 - Basic arithmetic keypad (+ - * / % . ( ) )
 - Simple Interest calculator
 - Compound Interest calculator (n compounds per year)
 - Small history panel
No external libraries required. Works with Python 3.8+.
Run: python main.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ast, operator as op, math, sys, json, os
from datetime import datetime

ALLOWED_OPERATORS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg, ast.UAdd: op.pos
}
ALLOWED_FUNCTIONS = {
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "ceil": math.ceil, "floor": math.floor, "abs": abs, "round": round
}

def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers are allowed")
    if isinstance(node, ast.Num):  # older Python
        return node.n
    if isinstance(node, ast.BinOp):
        if type(node.op) not in ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed")
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        return ALLOWED_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in ALLOWED_OPERATORS:
            raise ValueError("Unary operator not allowed")
        return ALLOWED_OPERATORS[type(node.op)](safe_eval(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Invalid function")
        name = node.func.id
        if name not in ALLOWED_FUNCTIONS:
            raise ValueError("Function not allowed")
        args = [safe_eval(a) for a in node.args]
        return ALLOWED_FUNCTIONS[name](*args)
    raise ValueError("Invalid expression")

def evaluate_expression(expr: str):
    # allow percent like 50% => (50/100)
    expr = expr.replace('%', '/100')
    parsed = ast.parse(expr, mode='eval')
    return safe_eval(parsed)

# ---------------- UI & logic ----------------
HISTORY_FILE = "calc_history.json"

class MobileCalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mobile Calculator — Interest + Basic")
        self.geometry("360x640")
        self.resizable(False, False)
        self.configure(bg="#1f2937")  # dark background
        
        self.history = self.load_history()
        self._build_ui()

    def _build_ui(self):
        # header
        header = tk.Frame(self, bg="#111827", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="Calculator", fg="white", bg="#111827", font=("Inter", 18, "bold")).pack()

        # tabs
        tab_control = ttk.Notebook(self)
        tab_control.pack(expand=True, fill="both", padx=10, pady=10)

        # calculator tab
        calc_tab = tk.Frame(tab_control, bg="#0b1220")
        tab_control.add(calc_tab, text="Calc")

        # simple interest tab
        simple_tab = tk.Frame(tab_control, bg="#0b1220")
        tab_control.add(simple_tab, text="Simple Interest")

        # compound interest tab
        compound_tab = tk.Frame(tab_control, bg="#0b1220")
        tab_control.add(compound_tab, text="Compound Interest")

        # history tab
        history_tab = tk.Frame(tab_control, bg="#0b1220")
        tab_control.add(history_tab, text="History")

        # --- Calculator UI ---
        self.expr_var = tk.StringVar(value="")
        self.result_var = tk.StringVar(value="")

        display_frame = tk.Frame(calc_tab, bg="#000", bd=0)
        display_frame.pack(fill="x", pady=(10,8))
        tk.Label(display_frame, textvariable=self.expr_var, anchor="e", fg="#cbd5e1", bg="#000", font=("Consolas", 12)).pack(fill="x", padx=8)
        tk.Label(display_frame, textvariable=self.result_var, anchor="e", fg="#fff", bg="#000", font=("Consolas", 28, "bold")).pack(fill="x", padx=8, pady=(4,8))

        # keypad
        keys = [
            ["7","8","9","/"],
            ["4","5","6","*"],
            ["1","2","3","-"],
            ["0",".","%","+"]
        ]
        kp = tk.Frame(calc_tab, bg="#0b1220")
        kp.pack()
        for r,row in enumerate(keys):
            rowf = tk.Frame(kp, bg="#0b1220")
            rowf.pack(fill="x")
            for c,key in enumerate(row):
                b = tk.Button(rowf, text=key, width=6, height=2, bg="#374151", fg="white",
                              command=lambda k=key: self._append(k))
                b.grid(row=r, column=c, padx=4, pady=6)

        ctrl = tk.Frame(calc_tab, bg="#0b1220")
        ctrl.pack(pady=6)
        tk.Button(ctrl, text="⌫", width=6, bg="#ef4444", fg="white", command=self._back).pack(side="left", padx=6)
        tk.Button(ctrl, text="C", width=6, bg="#ef4444", fg="white", command=self._clear).pack(side="left", padx=6)
        tk.Button(ctrl, text="=", width=12, bg="#10b981", fg="white", command=self._evaluate).pack(side="left", padx=6)

        # --- Simple Interest UI ---
        self.si_principal = tk.StringVar(value="1000")
        self.si_rate = tk.StringVar(value="7.5")
        self.si_time = tk.StringVar(value="1")
        si_frame = tk.Frame(simple_tab, bg="#0b1220", pady=20)
        si_frame.pack(fill="x", padx=12)

        self._add_labeled_entry(si_frame, "Principal (P):", self.si_principal)
        self._add_labeled_entry(si_frame, "Rate % (R):", self.si_rate)
        self._add_labeled_entry(si_frame, "Time (years):", self.si_time)
        tk.Button(si_frame, text="Calculate Simple Interest", bg="#3b82f6", fg="white", command=self._calc_simple).pack(pady=10, fill="x")
        self.si_result_label = tk.Label(si_frame, text="", bg="#0b1220", fg="#cbd5e1")
        self.si_result_label.pack()

        # --- Compound Interest UI ---
        self.ci_principal = tk.StringVar(value="1000")
        self.ci_rate = tk.StringVar(value="7.5")
        self.ci_time = tk.StringVar(value="1")
        self.ci_freq = tk.StringVar(value="1")
        ci_frame = tk.Frame(compound_tab, bg="#0b1220", pady=20)
        ci_frame.pack(fill="x", padx=12)

        self._add_labeled_entry(ci_frame, "Principal (P):", self.ci_principal)
        self._add_labeled_entry(ci_frame, "Rate % (annual):", self.ci_rate)
        self._add_labeled_entry(ci_frame, "Time (years):", self.ci_time)
        self._add_labeled_entry(ci_frame, "Compounds per year (n):", self.ci_freq)
        tk.Button(ci_frame, text="Calculate Compound Interest", bg="#3b82f6", fg="white", command=self._calc_compound).pack(pady=10, fill="x")
        self.ci_result_label = tk.Label(ci_frame, text="", bg="#0b1220", fg="#cbd5e1")
        self.ci_result_label.pack()

        # --- History UI ---
        hist_frame = tk.Frame(history_tab, bg="#0b1220", pady=10)
        hist_frame.pack(fill="both", expand=True, padx=8)
        self.hist_listbox = tk.Listbox(hist_frame, bg="#0b1220", fg="#e5e7eb")
        self.hist_listbox.pack(fill="both", expand=True, side="left", padx=(0,8))
        hist_ctrl = tk.Frame(hist_frame, bg="#0b1220")
        hist_ctrl.pack(side="right", fill="y")
        tk.Button(hist_ctrl, text="Copy last 10", command=self._copy_history).pack(pady=6)
        tk.Button(hist_ctrl, text="Clear history", command=self._clear_history).pack(pady=6)
        self._refresh_history_listbox()

    def _add_labeled_entry(self, parent, label, var):
        f = tk.Frame(parent, bg="#0b1220")
        f.pack(fill="x", pady=6)
        tk.Label(f, text=label, bg="#0b1220", fg="#cbd5e1").pack(anchor="w")
        e = tk.Entry(f, textvariable=var, bg="#111827", fg="white", insertbackground="white")
        e.pack(fill="x", pady=4)

    # ---------- calculator logic ----------
    def _append(self, char):
        cur = self.expr_var.get()
        if cur == "0": cur = ""
        self.expr_var.set(cur + char)

    def _back(self):
        cur = self.expr_var.get()
        self.expr_var.set(cur[:-1])

    def _clear(self):
        self.expr_var.set("")
        self.result_var.set("")

    def _evaluate(self):
        expr = self.expr_var.get().strip()
        if not expr:
            return
        try:
            val = evaluate_expression(expr)
            self.result_var.set(str(round(val, 12)))
            self._push_history({"type":"calc","expr":expr,"result":val})
        except Exception as e:
            messagebox.showerror("Error", f"Invalid expression: {e}")

    # ---------- simple interest ----------
    def _calc_simple(self):
        try:
            P = float(self.si_principal.get())
            R = float(self.si_rate.get())
            T = float(self.si_time.get())
            si = (P * R * T) / 100.0
            total = P + si
            text = f"Simple Interest: ₹ {round(si,4)}    Total: ₹ {round(total,4)}"
            self.si_result_label.config(text=text)
            self._push_history({"type":"simple","inputs":{"P":P,"R":R,"T":T},"result":{"si":si,"total":total}})
        except Exception as e:
            messagebox.showerror("Error", f"Invalid inputs: {e}")

    # ---------- compound interest ----------
    def _calc_compound(self):
        try:
            P = float(self.ci_principal.get())
            R = float(self.ci_rate.get())/100.0
            T = float(self.ci_time.get())
            n = int(float(self.ci_freq.get()))
            A = P * ((1 + R/n) ** (n * T))
            ci = A - P
            text = f"Compound Interest: ₹ {round(ci,4)}    Total: ₹ {round(A,4)}"
            self.ci_result_label.config(text=text)
            self._push_history({"type":"compound","inputs":{"P":P,"rate_percent":R*100,"T":T,"n":n},"result":{"ci":ci,"total":A}})
        except Exception as e:
            messagebox.showerror("Error", f"Invalid inputs: {e}")

    # ---------- history ----------
    def _push_history(self, item):
        item["at"] = datetime.now().isoformat()
        self.history.insert(0, item)
        self.history = self.history[:50]
        self._save_history()
        self._refresh_history_listbox()

    def _refresh_history_listbox(self):
        self.hist_listbox.delete(0, tk.END)
        if not self.history:
            self.hist_listbox.insert(tk.END, "No history yet.")
            return
        for h in self.history:
            t = h.get("type","")
            if t=="calc":
                self.hist_listbox.insert(tk.END, f"Calc: {h['expr']} = {round(h['result'],6)}")
            else:
                self.hist_listbox.insert(tk.END, f"{t.title()}: {json.dumps(h['inputs'])} -> {json.dumps(h['result'])}")

    def _copy_history(self):
        text = "\n".join(self.hist_listbox.get(0, min(9, self.hist_listbox.size()-1)))
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Last items copied to clipboard")

    def _clear_history(self):
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.history = []
            self._save_history()
            self._refresh_history_listbox()

    def load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE,"r",encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self):
        try:
            with open(HISTORY_FILE,"w",encoding="utf-8") as f:
                json.dump(self.history,f,ensure_ascii=False,indent=2)
        except Exception:
            pass

if __name__ == "__main__":
    app = MobileCalcApp()
    app.mainloop()
