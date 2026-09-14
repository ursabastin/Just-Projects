import os
import sys
import json
import stat
import ctypes
from ctypes import wintypes
import hashlib
from datetime import datetime, date, timedelta
import calendar

DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
LEDGER_FILE = os.path.join(DEFAULT_DATA_DIR, "tracker_ledger.dat")

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

crypt32 = ctypes.windll.crypt32

def _dpapi_encrypt(data_bytes: bytes) -> bytes:
    blob_in = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if crypt32.CryptProtectData(ctypes.byref(blob_in), "NoFapImmutableLedger", None, None, None, 0, ctypes.byref(blob_out)):
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return out
    raise RuntimeError("CryptProtectData failed")

def _dpapi_decrypt(cipher_bytes: bytes) -> bytes:
    blob_in = DATA_BLOB(len(cipher_bytes), ctypes.cast(ctypes.create_string_buffer(cipher_bytes), ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return out
    raise RuntimeError("CryptUnprotectData failed: Ledger has been tampered with or corrupted")

def _calc_block_hash(index: int, date_str: str, status: str, timestamp: str, prev_hash: str) -> str:
    raw = f"{index}|{date_str}|{status}|{timestamp}|{prev_hash}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

class ImmutableRecordError(Exception):
    pass

class TamperDetectedError(Exception):
    pass

class Storage:
    def __init__(self, data_path=LEDGER_FILE):
        self.data_path = data_path
        self.ledger = self._load_and_verify_ledger()

    def _load_and_verify_ledger(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        if not os.path.exists(self.data_path):
            return {"version": "2.0-hashchain", "blocks": [], "head_hash": GENESIS_HASH}

        try:
            with open(self.data_path, "rb") as f:
                cipher = f.read()
            if not cipher:
                return {"version": "2.0-hashchain", "blocks": [], "head_hash": GENESIS_HASH}
            plain = _dpapi_decrypt(cipher)
            data = json.loads(plain.decode("utf-8"))
        except Exception as e:
            raise TamperDetectedError(f"Security Alert: Data file cannot be verified. Tampering detected: {e}")

        # Cryptographic chain verification
        blocks = data.get("blocks", [])
        expected_prev = GENESIS_HASH
        for idx, block in enumerate(blocks):
            if block["index"] != idx:
                raise TamperDetectedError(f"Block index mismatch at block {idx}")
            if block["prev_hash"] != expected_prev:
                raise TamperDetectedError(f"Hash chain broken at block {idx}: prev_hash mismatch")
            computed_hash = _calc_block_hash(idx, block["date"], block["status"], block["timestamp"], block["prev_hash"])
            if block["hash"] != computed_hash:
                raise TamperDetectedError(f"Block hash integrity failure at block {idx}")
            expected_prev = block["hash"]

        if blocks and data.get("head_hash") != expected_prev:
            raise TamperDetectedError("Head hash mismatch in ledger")

        return data

    def _save_ledger(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        raw_json = json.dumps(self.ledger, indent=2).encode("utf-8")
        encrypted = _dpapi_encrypt(raw_json)

        # Clear read-only attribute if file exists
        if os.path.exists(self.data_path):
            try:
                os.chmod(self.data_path, stat.S_IWRITE)
            except Exception:
                pass

        temp_path = self.data_path + ".tmp"
        with open(temp_path, "wb") as f:
            f.write(encrypted)
        
        if os.path.exists(self.data_path):
            os.remove(self.data_path)
        os.rename(temp_path, self.data_path)

        # Set file to Read-Only so no text editor or external tool can write to it
        try:
            os.chmod(self.data_path, stat.S_IREAD)
        except Exception:
            pass

    # --- Query API ---
    def get_yesterday_date(self) -> str:
        return (date.today() - timedelta(days=1)).isoformat()

    def get_day_status(self, date_str: str):
        for block in self.ledger.get("blocks", []):
            if block["date"] == date_str:
                return block["status"]
        return None

    def is_yesterday_recorded(self) -> bool:
        yest_str = self.get_yesterday_date()
        return self.get_day_status(yest_str) is not None

    def get_calendar_dict(self):
        res = {}
        for block in self.ledger.get("blocks", []):
            res[block["date"]] = block["status"]
        return res

    # --- Strict Append-Only Operation ---
    def record_yesterday(self, status: str) -> bool:
        """
        STRICT HARD LOCK:
        1. Can ONLY record yesterday's date.
        2. Status must be 'clean' or 'slip'.
        3. If yesterday has already been recorded, HARD REJECT.
        4. No edit, no reset, no rewrite allowed.
        """
        if status not in ("clean", "slip"):
            raise ValueError("Status must be 'clean' or 'slip'")

        yest_str = self.get_yesterday_date()

        # Check if already recorded in ledger
        if self.is_yesterday_recorded():
            raise ImmutableRecordError(f"Yesterday ({yest_str}) is already permanently sealed in the ledger. Changes are forbidden.")

        blocks = self.ledger.setdefault("blocks", [])
        idx = len(blocks)
        prev_hash = self.ledger.get("head_hash", GENESIS_HASH)
        now_ts = datetime.utcnow().isoformat() + "Z"
        block_hash = _calc_block_hash(idx, yest_str, status, now_ts, prev_hash)

        new_block = {
            "index": idx,
            "date": yest_str,
            "status": status,
            "timestamp": now_ts,
            "prev_hash": prev_hash,
            "hash": block_hash
        }

        blocks.append(new_block)
        self.ledger["head_hash"] = block_hash
        self._save_ledger()
        return True

    # --- Stats ---
    def get_streak_stats(self):
        cal = self.get_calendar_dict()
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Count consecutive clean days ending at yesterday (or today if ever recorded)
        current_streak = 0
        check_date = yesterday
        while True:
            d_str = check_date.isoformat()
            if cal.get(d_str) == "clean":
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        # Longest streak across history
        clean_dates = []
        for d_str, st in cal.items():
            if st == "clean":
                try:
                    clean_dates.append(date.fromisoformat(d_str))
                except ValueError:
                    pass

        clean_dates.sort()
        longest_streak = 0
        temp_streak = 0
        prev_date = None

        for d in clean_dates:
            if prev_date is None:
                temp_streak = 1
            elif d == prev_date + timedelta(days=1):
                temp_streak += 1
            elif d == prev_date:
                pass
            else:
                temp_streak = 1
            prev_date = d
            if temp_streak > longest_streak:
                longest_streak = temp_streak

        return {
            "current_streak": current_streak,
            "longest_streak": max(current_streak, longest_streak),
            "total_clean_days": len(clean_dates)
        }

    def get_month_stats(self, year, month):
        cal = self.get_calendar_dict()
        num_days = calendar.monthrange(year, month)[1]
        
        clean_count = 0
        slip_count = 0
        today = date.today()

        if year < today.year or (year == today.year and month < today.month):
            elapsed_days = num_days
        elif year == today.year and month == today.month:
            # Day before today is elapsed
            elapsed_days = max(0, today.day - 1)
        else:
            elapsed_days = 0

        for day in range(1, num_days + 1):
            d_str = f"{year:04d}-{month:02d}-{day:02d}"
            st = cal.get(d_str)
            if st == "clean":
                clean_count += 1
            elif st == "slip":
                slip_count += 1

        pct = (clean_count / elapsed_days * 100) if elapsed_days > 0 else 0.0

        return {
            "year": year,
            "month": month,
            "total_days": num_days,
            "elapsed_days": elapsed_days,
            "clean_count": clean_count,
            "slip_count": slip_count,
            "clean_percentage": pct
        }
