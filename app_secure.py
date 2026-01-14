import xmlrpc.client
from zk import ZK
import os
from dotenv import load_dotenv
from datetime import timedelta, datetime, time as dt_time
import time
import logging
import sys
 

# Load environment variables
load_dotenv()

# --- 1. ตั้งค่าการเชื่อมต่อ ZKTeco K50 ---
ZK_IP = os.getenv('ZK_DEVICE_IP', '192.168.1.130')  # IP ของเครื่องสแกนนิ้ว
ZK_PORT = int(os.getenv('ZK_DEVICE_PORT', '4370'))

# --- 2. ตั้งค่าการเชื่อมต่อ Odoo ---
ODOO_URL = os.getenv('ODOO_URL', 'https://odoo.rtk_landmos.com')
ODOO_DB = os.getenv('ODOO_DB', 'prod_db')
ODOO_USER = os.getenv('ODOO_USER', 'kritpapat69@gmail.com')
ODOO_PASS = os.getenv('ODOO_API_KEY','3280a2014d6ce2422fb16d0294d6d579cdda4974')  # ใช้ API Key จาก environment variable

# --- 3. ตั้งค่า Auto Check-In / Check-Out ---
AUTO_CHECKIN_HOUR = int(os.getenv('AUTO_CHECKIN_HOUR', '10'))
AUTO_CHECKIN_MINUTE = int(os.getenv('AUTO_CHECKIN_MINUTE', '0'))
AUTO_CHECKOUT_HOUR = int(os.getenv('AUTO_CHECKOUT_HOUR', '23'))
AUTO_CHECKOUT_MINUTE = int(os.getenv('AUTO_CHECKOUT_MINUTE', '59'))

def connect_to_odoo():
    """เชื่อมต่อกับ Odoo ผ่าน XML-RPC"""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

# --- ทำการเรียก API ของ Odoo แบบมี retry mechanism ---
def exec_with_retry(models, db, uid, pwd, model, method, args=None, kwargs=None, retries=3, delay=1):
    args = args or []
    kwargs = kwargs or {}
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return models.execute_kw(db, uid, pwd, model, method, args if args is not None else [], kwargs if kwargs is not None else {})
        except xmlrpc.client.Fault as f:
            last_exc = f
            logging.warning('XML-RPC Fault on %s.%s attempt %d/%d: %s', model, method, attempt, retries, f)
            # For certain faults it's useful to retry after a short wait
            time.sleep(delay * attempt)
        except Exception as e:
            last_exc = e
            logging.exception('Exception on %s.%s attempt %d/%d', model, method, attempt, retries)
            time.sleep(delay * attempt)
    # If we reach here, all retries failed; re-raise the last exception
    raise last_exc

def sync_attendance():
    """ซิงค์ข้อมูลการลงเวลาจาก ZKTeco ไปยัง Odoo"""
    zk = ZK(ZK_IP, port=ZK_PORT, timeout=5)
    conn = None
    
    try:
        # เชื่อมต่อเครื่องสแกน
        conn = zk.connect()
        print("Connected to ZKTeco...")
        attendances = conn.get_attendance()
        
        # เชื่อมต่อ Odoo
        uid, models = connect_to_odoo()
        print(f"Connected to Odoo (UID: {uid})...")

        for att in attendances:
            # att.user_id คือรหัสพนักงานจากเครื่องสแกน
            # att.timestamp คือเวลาที่สแกน
            
            # ค้นหา ID ของพนักงานใน Odoo ที่มี Badge ID ตรงกับเครื่องสแกน
            employee_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'hr.employee', 'search', 
                [[['barcode', '=', str(att.user_id)]]]) # หรือเปลี่ยน 'barcode' เป็น 'pin' ตามที่ตั้งไว้

            if employee_ids:
                emp_id = employee_ids[0]
                # ปรับเวลาโดยลบ 7 ชั่วโมง (timezone / offset correction)
                adjusted_ts = att.timestamp - timedelta(hours=7)
                check_time = adjusted_ts.strftime('%Y-%m-%d %H:%M:%S')
                # ตรวจสอบว่ามี attendance ที่เปิดอยู่ (ไม่มี check_out) สำหรับพนักงานนี้
                open_att_ids = exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'search', args=[[['employee_id', '=', emp_id], ['check_out', '=', False]]])

                if open_att_ids:
                    # อ่าน check_in ของเรคอร์ดที่เปิดอยู่เพื่อเปรียบเทียบเวลา (ถ้าต้องการ)
                    open_ats = exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'read', args=[open_att_ids, ['check_in']])
                    for oid, rec in zip(open_att_ids, open_ats):
                        check_in_str = rec.get('check_in')
                        try:
                            # แปลง check_in เป็น datetime เพื่อความแม่นยำ
                            if check_in_str:
                                check_in_dt = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                            else:
                                check_in_dt = None

                            # ถ้าเวลาสแกนก่อน check_in (ผิดปกติ) ให้ใช้ check_in + 1 วินาที
                            if check_in_dt and adjusted_ts <= check_in_dt:
                                fallback_dt = check_in_dt + timedelta(seconds=1)
                                fallback_str = fallback_dt.strftime('%Y-%m-%d %H:%M:%S')
                                try:
                                    exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'write', args=[[oid], {'check_out': fallback_str}])
                                    print(f"Sync: Employee {att.user_id} check_out adjusted to {fallback_str} for attendance {oid}")
                                    continue
                                except Exception:
                                    logging.exception('Failed fallback write for attendance %s', oid)

                            # ปกติพยายามเขียน check_out เป็นเวลา scan ที่ปรับแล้ว
                            try:
                                exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'write', args=[[oid], {'check_out': check_time}])
                                print(f"Sync: Employee {att.user_id} check_out set to {check_time} for attendance {oid}")
                            except xmlrpc.client.Fault as f:
                                # วิเคราะห์ Fault: ถ้าเป็นปัญหา duplicate/constraint ให้ลอง fallback
                                logging.warning('Fault when writing check_out for %s: %s', oid, f)
                                if check_in_str:
                                    try:
                                        check_in_dt = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                                        fallback_dt = check_in_dt + timedelta(seconds=1)
                                        fallback_str = fallback_dt.strftime('%Y-%m-%d %H:%M:%S')
                                        exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'write', args=[[oid], {'check_out': fallback_str}])
                                        print(f"Sync: Employee {att.user_id} check_out fallback to {fallback_str} for attendance {oid}")
                                    except Exception:
                                        logging.exception('Fallback also failed for attendance %s', oid)
                                else:
                                    logging.exception('No check_in found to compute fallback for attendance %s', oid)
                        except Exception as e:
                            logging.exception('Unexpected error while setting check_out for %s: %s', oid, e)
                else:
                    # ตรวจสอบว่ามีข้อมูลนี้ใน Odoo หรือยัง (ป้องกันการส่งซ้ำ)
                    existing = exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'search', args=[[['employee_id', '=', emp_id], ['check_in', '=', check_time]]])

                    if not existing:
                        try:
                            exec_with_retry(models, ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'create', args=[{
                                'employee_id': emp_id,
                                'check_in': check_time,
                            }], retries=3)
                            print(f"Sync: Employee {att.user_id} at {check_time} -> Odoo Success")
                        except Exception as e:
                            logging.exception('Failed to create attendance for %s at %s: %s', att.user_id, check_time, e)
                            print(f"Warning: failed to create check_in for {att.user_id}: {e}")
            else:
                print(f"Warning: Employee ID {att.user_id} not found in Odoo")

    except Exception as e:
        # แปลง error เป็น string และ encode เป็น UTF-8 เพื่อแสดงภาษาไทยได้
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"Error: {error_msg}")
    finally:
        if conn:
            conn.disconnect()
            print("Disconnected from ZKTeco")


# --- ฟังก์ชัน Auto Check-Out ---
def auto_checkout_pending_attendance(date_to_process=None):
    """
    ปิด attendance ที่ค้างอยู่อัตโนมัติเวลา 23:59 น.
    
    Args:
        date_to_process: วันที่ต้องการประมวลผล (datetime.date object)
                        ถ้าไม่ระบุจะใช้วันก่อนหน้า
    """
    uid, models = connect_to_odoo()
    if not uid or not models:
        print("Error: Cannot connect to Odoo")
        return
    
    print(f"Connected to Odoo for Auto Check-Out (UID: {uid})...")
    
    # กำหนดวันที่ต้องการประมวลผล
    if date_to_process is None:
        # ใช้วันก่อนหน้า (เช่น รันตอน 00:00 จะประมวลผลวันเมื่อวาน)
        date_to_process = (datetime.now() - timedelta(days=1)).date()
    
    date_str = date_to_process.strftime('%Y-%m-%d')
    print(f"Processing pending attendance for date: {date_str}")
    
    try:
        # ค้นหา attendance ที่ยังไม่มี check_out ในวันที่กำหนด
        pending_att_ids = exec_with_retry(
            models, ODOO_DB, uid, ODOO_PASS,
            'hr.attendance', 'search',
            args=[[
                ['check_out', '=', False],
                ['check_in', '>=', f'{date_str} 00:00:00'],
                ['check_in', '<=', f'{date_str} 23:59:59']
            ]]
        )
        
        if not pending_att_ids:
            print(f"No pending attendance found for {date_str}")
            return
        
        print(f"Found {len(pending_att_ids)} pending attendance record(s)")
        
        # อ่านข้อมูล attendance ที่ค้างอยู่
        pending_atts = exec_with_retry(
            models, ODOO_DB, uid, ODOO_PASS,
            'hr.attendance', 'read',
            args=[pending_att_ids, ['id', 'check_in', 'employee_id']]
        )
        
        # ประมวลผลแต่ละรายการ
        success_count = 0
        error_count = 0
        
        for att in pending_atts:
            try:
                check_in_dt = datetime.strptime(att['check_in'], '%Y-%m-%d %H:%M:%S')
                
                # ตั้ง check_out เป็นเวลาที่กำหนด (23:59) ของวันนั้น
                auto_checkout_dt = datetime.combine(
                    check_in_dt.date(), 
                    dt_time(AUTO_CHECKOUT_HOUR, AUTO_CHECKOUT_MINUTE, 0)
                )
                auto_checkout_str = auto_checkout_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # อัปเดต check_out
                exec_with_retry(
                    models, ODOO_DB, uid, ODOO_PASS,
                    'hr.attendance', 'write',
                    args=[[att['id']], {'check_out': auto_checkout_str}]
                )
                
                employee_name = att['employee_id'][1] if att['employee_id'] else 'Unknown'
                print(f"✅ Auto check-out: {employee_name} | "
                      f"Check-in: {att['check_in']} | Check-out: {auto_checkout_str}")
                success_count += 1
                
            except Exception as e:
                employee_name = att.get('employee_id', ['', 'Unknown'])[1]
                logging.exception(f"Failed to auto check-out for {employee_name}: {e}")
                print(f"❌ Failed: {employee_name}")
                error_count += 1
        
        # สรุปผลการทำงาน
        print("=" * 60)
        print(f"AUTO CHECK-OUT SUMMARY for {date_str}")
        print(f"Total pending: {len(pending_att_ids)}")
        print(f"Success: {success_count}")
        print(f"Failed: {error_count}")
        print("=" * 60)
        
    except Exception as e:
        logging.exception(f"Error during auto check-out process: {e}")
        print(f"Error: {e}")


# --- ฟังก์ชัน Auto Check-In ---
def auto_checkin_employees(date_to_process=None):
    """
    สร้าง check-in อัตโนมัติเวลา 10:00 น. สำหรับพนักงานที่ลืมสแกนเข้า
    แต่มีการ check-out ในวันนั้น (จากข้อมูลเครื่องสแกน)
    
    Args:
        date_to_process: วันที่ต้องการประมวลผล (datetime.date object)
                        ถ้าไม่ระบุจะใช้วันปัจจุบัน
    """
    uid, models = connect_to_odoo()
    if not uid or not models:
        print("Error: Cannot connect to Odoo")
        return
    
    print(f"Connected to Odoo for Auto Check-In (UID: {uid})...")
    
    # กำหนดวันที่ต้องการประมวลผล
    if date_to_process is None:
        date_to_process = datetime.now().date()
    
    date_str = date_to_process.strftime('%Y-%m-%d')
    print(f"Processing auto check-in for date: {date_str}")
    
    try:
        # ดึงรายชื่อพนักงานทั้งหมดที่ active
        all_employee_ids = exec_with_retry(
            models, ODOO_DB, uid, ODOO_PASS,
            'hr.employee', 'search',
            args=[[['active', '=', True]]]
        )
        
        if not all_employee_ids:
            print("No active employees found")
            return
        
        print(f"Found {len(all_employee_ids)} active employee(s)")
        
        # ตรวจสอบแต่ละพนักงาน
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for emp_id in all_employee_ids:
            try:
                # ตรวจสอบว่าพนักงานมี attendance ในวันนี้หรือไม่
                existing_att = exec_with_retry(
                    models, ODOO_DB, uid, ODOO_PASS,
                    'hr.attendance', 'search',
                    args=[[
                        ['employee_id', '=', emp_id],
                        ['check_in', '>=', f'{date_str} 00:00:00'],
                        ['check_in', '<=', f'{date_str} 23:59:59']
                    ]]
                )
                
                if existing_att:
                    # มี attendance อยู่แล้ว ข้ามไป
                    skipped_count += 1
                    continue
                
                # ดึงข้อมูลพนักงาน
                emp_data = exec_with_retry(
                    models, ODOO_DB, uid, ODOO_PASS,
                    'hr.employee', 'read',
                    args=[[emp_id], ['name', 'barcode']]
                )
                
                if not emp_data:
                    continue
                
                emp_name = emp_data[0].get('name', 'Unknown')
                emp_barcode = emp_data[0].get('barcode', '')
                
                # ตรวจสอบว่าพนักงานมี barcode หรือไม่ (ต้องมี barcode จึงจะ sync ได้)
                if not emp_barcode:
                    skipped_count += 1
                    continue
                
                # สร้าง check-in เวลา 10:00 น.
                auto_checkin_dt = datetime.combine(
                    date_to_process,
                    dt_time(AUTO_CHECKIN_HOUR, AUTO_CHECKIN_MINUTE, 0)
                )
                # ปรับเวลาเป็น UTC (ลบ 7 ชั่วโมงสำหรับเวลาไทย)
                auto_checkin_utc = auto_checkin_dt - timedelta(hours=7)
                auto_checkin_str = auto_checkin_utc.strftime('%Y-%m-%d %H:%M:%S')
                
                # สร้าง attendance record
                exec_with_retry(
                    models, ODOO_DB, uid, ODOO_PASS,
                    'hr.attendance', 'create',
                    args=[{
                        'employee_id': emp_id,
                        'check_in': auto_checkin_str
                    }]
                )
                
                print(f"✅ Auto check-in: {emp_name} | Check-in: {auto_checkin_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                success_count += 1
                
            except Exception as e:
                logging.exception(f"Failed to auto check-in for employee {emp_id}: {e}")
                print(f"❌ Failed: Employee ID {emp_id}")
                error_count += 1
        
        # สรุปผลการทำงาน
        print("=" * 60)
        print(f"AUTO CHECK-IN SUMMARY for {date_str}")
        print(f"Total employees: {len(all_employee_ids)}")
        print(f"Created check-in: {success_count}")
        print(f"Skipped (already checked in): {skipped_count}")
        print(f"Failed: {error_count}")
        print("=" * 60)
        
    except Exception as e:
        logging.exception(f"Error during auto check-in process: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    # ตรวจสอบว่ามี API Key
    if not ODOO_PASS:
        print("Error: ODOO_API_KEY not found in environment variables")
        print("Please create a .env file with your credentials")
        sys.exit(1)
    
    # รองรับ command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--auto-checkout':
            # รัน auto check-out สำหรับวันก่อนหน้า
            auto_checkout_pending_attendance()
        elif sys.argv[1] == '--auto-checkout-date':
            # ระบุวันที่เอง เช่น --auto-checkout-date 2026-01-13
            if len(sys.argv) > 2:
                try:
                    specific_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
                    auto_checkout_pending_attendance(specific_date)
                except ValueError:
                    print("Error: Invalid date format. Use YYYY-MM-DD")
                    sys.exit(1)
            else:
                print("Error: Please specify a date. Example: --auto-checkout-date 2026-01-13")
                sys.exit(1)
        elif sys.argv[1] == '--auto-checkin':
            # รัน auto check-in สำหรับวันปัจจุบัน
            auto_checkin_employees()
        elif sys.argv[1] == '--auto-checkin-date':
            # ระบุวันที่เอง เช่น --auto-checkin-date 2026-01-13
            if len(sys.argv) > 2:
                try:
                    specific_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
                    auto_checkin_employees(specific_date)
                except ValueError:
                    print("Error: Invalid date format. Use YYYY-MM-DD")
                    sys.exit(1)
            else:
                print("Error: Please specify a date. Example: --auto-checkin-date 2026-01-13")
                sys.exit(1)
        elif sys.argv[1] == '--help':
            print("ZK50-ODOO Sync Tool")
            print("="*60)
            print("Usage:")
            print("  python app_secure.py                    - Sync attendance from ZKTeco")
            print("")
            print("Auto Check-Out (23:59):")
            print("  python app_secure.py --auto-checkout    - Auto check-out for yesterday")
            print("  python app_secure.py --auto-checkout-date YYYY-MM-DD")
            print("")
            print("Auto Check-In (10:00):")
            print("  python app_secure.py --auto-checkin     - Auto check-in for today")
            print("  python app_secure.py --auto-checkin-date YYYY-MM-DD")
            print("")
            print("  python app_secure.py --help             - Show this help")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # รันแบบปกติ: ซิงค์จากเครื่องสแกน
        sync_attendance()
