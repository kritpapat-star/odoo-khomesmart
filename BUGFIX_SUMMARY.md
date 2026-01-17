# Bug Fix Summary for app_secure.py

## Date: 2026-01-17

## Bugs Fixed

### 🔴 CRITICAL BUG #1: Timezone Inconsistency in Auto Check-Out

**Problem:**
Auto check-out times were NOT converted to UTC, while all other times were.

**Evidence:**
- Scan data (line 104): `att.timestamp - timedelta(hours=7)` ✓ Converts to UTC
- Auto check-in (lines 549, 607): `auto_checkin_dt - timedelta(hours=7)` ✓ Converts to UTC
- Auto check-out (lines 224-228, 244-248, 375-379): ❌ **NO timezone conversion!**

**Impact:**
- Check-in times were in UTC (Thai time - 7 hours)
- Auto check-out times were in LOCAL Thai time
- This created a **7-hour discrepancy** where check-out could appear BEFORE check-in in Odoo!

**Example:**
```
Employee checks in at 09:00 Thai time
→ Stored in Odoo as: 2026-01-17 02:00:00 UTC

Auto check-out at 23:59 Thai time
→ Stored in Odoo as: 2026-01-17 23:59:00 (LOCAL, not UTC!)
```

This breaks attendance logic because Odoo expects all times in UTC.

**Fix Applied:**
Added `- timedelta(hours=7)` to convert auto check-out times to UTC in 3 locations:

1. **Line 232-233** (sync_attendance - Auto Check-Out, first occurrence):
```python
auto_checkout_utc = auto_checkout_dt - timedelta(hours=7)  # FIX: Convert to UTC
auto_checkout_str = auto_checkout_utc.strftime('%Y-%m-%d %H:%M:%S')
```

2. **Line 249-250** (sync_attendance - Auto Check-Out, second occurrence):
```python
auto_checkout_utc = auto_checkout_dt - timedelta(hours=7)  # FIX: Convert to UTC
auto_checkout_str = auto_checkout_utc.strftime('%Y-%m-%d %H:%M:%S')
```

3. **Line 380-381** (auto_checkout_pending_attendance function):
```python
auto_checkout_utc = auto_checkout_dt - timedelta(hours=7)  # FIX: Convert to UTC
auto_checkout_str = auto_checkout_utc.strftime('%Y-%m-%d %H:%M:%S')
```

4. **Line 273-274** (sync_attendance - Auto Check-In):
```python
auto_checkin_utc = auto_checkin_dt - timedelta(hours=7)  # FIX: Convert to UTC
auto_checkin_str = auto_checkin_utc.strftime('%Y-%m-%d %H:%M:%S')
```

---

### 🟡 BUG #2: Status Attribute Warning

**Problem:**
The code assumes ZK devices provide a `status` field (0=Check-In, 1=Check-Out), but some models may not support this field.

**Impact:**
- If `status` is None, the code falls through to complex fallback logic
- Could lead to incorrect attendance categorization
- No warning was shown when status attribute was missing

**Fix Applied:**
Added warning message when status attribute is missing (line 126-127):

```python
# แสดง warning เมื่อ status attribute ไม่มี
if scan_status is None:
    print(f"Warning: Employee {att.user_id} scan at {check_time} has no status attribute, using fallback logic")
```

This helps users identify when their ZK device doesn't support the status field.

---

## Diagnostic Logging Added

Added debug logging to help validate issues:

1. **Lines 68-78** - First attendance record details:
   - Shows user_id, timestamp, timestamp type
   - Checks if status attribute exists
   - Shows status value if available
   - Lists all attributes for debugging

---

## Testing Recommendations

After applying these fixes, test the following scenarios:

1. **Normal sync:**
   ```powershell
   python app_secure.py
   ```
   - Check that [DEBUG] output shows status attribute details
   - Verify times are consistent

2. **Auto check-out:**
   ```powershell
   python app_secure.py --auto-checkout
   ```
   - Verify check-out times are in UTC (7 hours behind Thai time)

3. **Auto check-in:**
   ```powershell
   python app_secure.py --auto-checkin
   ```
   - Verify check-in times are in UTC (7 hours behind Thai time)

4. **Check Odoo records:**
   - All times should be in UTC
   - Check-out should always be AFTER check-in
   - No negative duration records

---

## Files Modified

- `app_secure.py` - Fixed timezone conversion and added status warnings
- `BUGFIX_SUMMARY.md` - This documentation file

---

## Next Steps

1. Test the fixes with actual ZK device and Odoo connection
2. Monitor logs for the new warning messages about status attribute
3. Verify all attendance records in Odoo have correct UTC times
4. Consider adding timezone configuration to .env file if needed

---

## Notes

- The timezone conversion assumes Thai time (UTC+7)
- If your system uses a different timezone, update the `timedelta(hours=7)` accordingly
- The status attribute issue may require firmware update on ZK device or alternative logic
