#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
สคริปต์ตรวจสอบสถานะ attendance ที่เปิดค้างอยู่ใน Odoo
"""
import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASS = os.getenv('ODOO_API_KEY')

try:
    # เชื่อมต่อ Odoo
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    print(f'Connected to Odoo (UID: {uid})')
    print('=' * 70)
    print()

    # ค้นหาพนักงานทั้งหมดที่มี barcode
    employees = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'hr.employee', 'search_read',
        [[['barcode', '!=', False]]], {'fields': ['id', 'name', 'barcode']})

    print(f'Employees with barcode: {len(employees)}')
    print('=' * 70)

    for emp in employees:
        print(f"\nEmployee: {emp['name']}")
        print(f"  - ID: {emp['id']}")
        print(f"  - Barcode: {emp['barcode']}")

        # เช็คว่ามี attendance ที่เปิดอยู่หรือไม่
        open_att = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'hr.attendance', 'search_read',
            [[['employee_id', '=', emp['id']], ['check_out', '=', False]]],
            {'fields': ['id', 'check_in'], 'limit': 1})

        if open_att:
            print(f"  - Status: HAS OPEN CHECK-IN")
            print(f"  - Check-in time: {open_att[0]['check_in']}")
            print(f"  - Attendance ID: {open_att[0]['id']}")
            print(f"  >>> Next scan will be: CHECK OUT <<<")
        else:
            print(f"  - Status: NO OPEN CHECK-IN")
            print(f"  >>> Next scan will be: CHECK IN <<<")

    print()
    print('=' * 70)

except Exception as e:
    print(f'Error: {e}')
