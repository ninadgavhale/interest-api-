# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import json, os, math, traceback
from datetime import datetime

# Attempt to reuse safe evaluator from your main.py
try:
    import main as calc_main
    evaluate_expression = getattr(calc_main, "evaluate_expression")
except Exception:
    # Fallback if import fails - minimal safe evaluator
    def evaluate_expression(expr: str):
        raise RuntimeError("Failed to import evaluate_expression from main.py")

# History file - same name as in your single-file app
HISTORY_FILE = "calc_history.json"
MAX_HISTORY = 50

app = FastAPI(title="Mobile Calculator API", description="Calc, Simple & Compound interest, History")

# ---------- Pydantic models ----------
class CalcRequest(BaseModel):
    expr: str = Field(..., example="2+2*3")
class SimpleInterestRequest(BaseModel):
    P: float = Field(..., example=1000)
    R: float = Field(..., example=7.5, description="annual rate percent")
    T: float = Field(..., example=1, description="time in years")
class CompoundInterestRequest(BaseModel):
    P: float = Field(..., example=1000)
    rate_percent: float = Field(..., example=7.5)
    T: float = Field(..., example=1)
    n: int = Field(..., example=4, description="compounds per year")
class HistoryItem(BaseModel):
    at: str
    type: str
    inputs: Optional[dict] = None
    expr: Optional[str] = None
    result: Any

# ---------- history helpers ----------
def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def push_history(item: dict):
    history = load_history()
    item["at"] = datetime.now().isoformat()
    history.insert(0, item)
    history = history[:MAX_HISTORY]
    save_history(history)
    return item

# ---------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/calc")
def calc(req: CalcRequest):
    expr = req.expr.strip()
    if not expr:
        raise HTTPException(status_code=400, detail="Empty expression")
    try:
        val = evaluate_expression(expr)
        # record numeric result as float
        rec = {"type": "calc", "expr": expr, "result": float(val)}
        push_history(rec)
        return {"ok": True, "result": val}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid expression: {e}")

@app.post("/simple")
def simple(si: SimpleInterestRequest):
    try:
        P = float(si.P)
        R = float(si.R)
        T = float(si.T)
        si_val = (P * R * T) / 100.0
        total = P + si_val
        rec = {"type": "simple", "inputs": {"P": P, "R": R, "T": T}, "result": {"si": si_val, "total": total}}
        push_history(rec)
        return {"ok": True, "si": si_val, "total": total}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid inputs: {e}")

@app.post("/compound")
def compound(ci: CompoundInterestRequest):
    try:
        P = float(ci.P)
        r = float(ci.rate_percent) / 100.0
        T = float(ci.T)
        n = int(ci.n)
        if n <= 0:
            raise ValueError("n must be positive integer")
        A = P * ((1 + r / n) ** (n * T))
        ci_val = A - P
        rec = {"type": "compound", "inputs": {"P": P, "rate_percent": ci.rate_percent, "T": T, "n": n}, "result": {"ci": ci_val, "total": A}}
        push_history(rec)
        return {"ok": True, "ci": ci_val, "total": A}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid inputs: {e}")

@app.get("/history", response_model=List[HistoryItem])
def get_history(limit: Optional[int] = 20):
    h = load_history()
    # return up to 'limit'
    return h[:min(int(limit), len(h))]

@app.post("/history/clear")
def clear_history():
    save_history([])
    return {"ok": True, "cleared": True}
