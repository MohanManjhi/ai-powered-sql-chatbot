#!/usr/bin/env python3
"""Convert pytest JUnit XML into a flat CSV report.

Reads `test_reports/junit_api_report.xml` (or the junit xml present) and writes
`test_reports/api_test_report.csv` with columns:
  classname, test_name, time, status, message

This script does not modify your application code.
"""
import os
import sys
import csv
from xml.etree import ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
XML_INPUTS = [
    os.path.join(ROOT, 'test_reports', 'junit_api_report.xml'),
    os.path.join(ROOT, 'test_reports', 'junit_report.xml'),
]
OUT_CSV = os.path.join(ROOT, 'test_reports', 'api_test_report.csv')


def find_xml():
    for p in XML_INPUTS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError('No JUnit XML file found in test_reports')


def parse_junit(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suites = []
    if root.tag == 'testsuites':
        suites = list(root.findall('testsuite'))
    elif root.tag == 'testsuite':
        suites = [root]
    else:
        suites = root.findall('.//testsuite')

    rows = []
    for suite in suites:
        for case in suite.findall('testcase'):
            classname = case.attrib.get('classname', '')
            name = case.attrib.get('name', '')
            time = case.attrib.get('time', '')
            status = 'passed'
            message = ''
            for child in list(case):
                tag = child.tag.lower()
                if tag in ('failure', 'error'):
                    status = tag
                    message = (child.attrib.get('message', '') + '\n' + (child.text or '')).strip()
                    break
                if tag == 'skipped':
                    status = 'skipped'
                    message = (child.attrib.get('message', '') + '\n' + (child.text or '')).strip()
                    break

            rows.append({
                'classname': classname,
                'test_name': name,
                'time': time,
                'status': status,
                'message': message,
            })
    return rows


def write_csv(rows, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['classname', 'test_name', 'time', 'status', 'message'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    xml_path = find_xml()
    rows = parse_junit(xml_path)
    write_csv(rows, OUT_CSV)
    print('CSV written to', OUT_CSV)


if __name__ == '__main__':
    main()
