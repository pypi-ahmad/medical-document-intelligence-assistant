"""Live end-to-end verifier for medical document assistant workflow.

Runs against locally running backend/frontend instances and writes
artifacts to ``artifacts/verification``.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import fitz
import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKEND = 'http://127.0.0.1:18000'
FRONTEND = 'http://127.0.0.1:3100'
API = f'{BACKEND}/api'
OUT_DIR = ROOT / 'artifacts' / 'verification'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / 'verification_live_run.json'
OUT_MD = OUT_DIR / 'verification_live_run.md'


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


checks: list[Check] = []


def record(name: str, passed: bool, detail: str) -> None:
    checks.append(Check(name=name, passed=bool(passed), detail=detail))


def make_pdf(path: Path, pages: list[str]) -> None:
    doc = fitz.open()
    for page_text in pages:
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(40, 40, 555, 800)
        page.insert_textbox(rect, page_text, fontsize=11, fontname='helv', lineheight=1.3)
    doc.save(path)
    doc.close()


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    for p in candidates:
        fp = Path(p)
        if fp.exists():
            return ImageFont.truetype(str(fp), size=size)
    return ImageFont.load_default()


def make_scan_png(path: Path, text: str, handwritten: bool = False) -> None:
    img = Image.new('RGB', (1400, 1800), color=(250, 250, 246))
    draw = ImageDraw.Draw(img)
    font = _load_font(38 if handwritten else 34)
    y = 80
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            y += 28
            continue
        draw.text((90, y), line, fill=(20, 20, 20), font=font)
        y += 58 if handwritten else 52
    if handwritten:
        img = img.rotate(1.2, expand=False, fillcolor=(250, 250, 246))
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    img.save(path, format='PNG')


def upload_doc(client: httpx.Client, file_path: Path, mime: str) -> dict:
    with file_path.open('rb') as fh:
        resp = client.post(
            f'{API}/documents/',
            files={'file': (file_path.name, fh, mime)},
            timeout=60.0,
        )
    resp.raise_for_status()
    return resp.json()


def process_doc(client: httpx.Client, doc_id: str) -> dict:
    last_payload: dict | None = None
    for _ in range(2):
        resp = client.post(f'{API}/medical/process/{doc_id}', timeout=360.0)
        resp.raise_for_status()
        payload = resp.json()
        last_payload = payload
        if payload.get('status') == 'completed':
            return payload
        time.sleep(1.0)
    return last_payload or {'status': 'failed', 'error': 'no payload'}


def get_json(client: httpx.Client, url: str, **kwargs) -> dict | list:
    resp = client.get(url, timeout=90.0, **kwargs)
    resp.raise_for_status()
    return resp.json()


def post_json(client: httpx.Client, url: str, payload: dict) -> dict:
    resp = client.post(url, json=payload, timeout=120.0)
    resp.raise_for_status()
    return resp.json()


def get_json_with_retry(
    client: httpx.Client,
    url: str,
    *,
    attempts: int = 6,
    delay_seconds: float = 0.5,
    **kwargs,
) -> dict | list:
    last_exc: Exception | None = None
    for idx in range(attempts):
        try:
            return get_json(client, url, **kwargs)
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code != 404 or idx == attempts - 1:
                raise
            time.sleep(delay_seconds)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Retry loop failed without an exception")


def main() -> int:
    run_id = str(int(time.time()))
    tmp = Path(f'/tmp/mdia_live_verify_{run_id}')
    tmp.mkdir(parents=True, exist_ok=True)

    prescription_pdf = tmp / 'prescription_sample.pdf'
    lab_pdf = tmp / 'lab_report_sample.pdf'
    scanned_png = tmp / 'scanned_referral_sample.png'
    handwritten_png = tmp / 'handwritten_note_sample.png'

    prescription_text = """City Care Medical Center
Prescription
Patient Name: Ahmad Khan
Patient ID: MRN-88421
Age: 34
Sex: Male
Visit Date: 2026-06-21
Doctor: Dr. Sarah Lee
Diagnosis: Type 2 diabetes mellitus
Allergy: Penicillin

Medications:
Started Metformin 500 mg bid
Started Atorvastatin 20 mg daily
Aspirin 75 mg once daily

Follow-up Date: 2026-07-05
"""

    lab_text = """City Care Medical Center
Laboratory Report
Patient Name: Ahmad Khan
Date of Service: 2026-06-25

Hemoglobin: 10.8 g/dL (13.0-17.0)
WBC: 12.2 K/uL (4.0-11.0)
Creatinine: 1.4 mg/dL (0.7-1.3)
Glucose: 168 mg/dL (70-99)
Sodium: 138 mmol/L (135-145)
Potassium: 4.6 mmol/L (3.5-5.1)
"""

    scan_text = """Referral Letter
Date of Visit: 2026-06-24
Patient Name: Ahmad Khan
Hospital: City Care Hospital
Chief Complaint: persistent cough
Procedure: Chest X-ray
Provider: Dr. Umar Ali
"""

    handwritten_text = """Handwritten Follow-up Note
Date of visit: 2026-06-27
new Lisinopril 5 mg daily
Symptoms: mild dizziness
Allergy: none
"""

    make_pdf(prescription_pdf, [prescription_text])
    make_pdf(lab_pdf, [lab_text])
    make_scan_png(scanned_png, scan_text, handwritten=False)
    make_scan_png(handwritten_png, handwritten_text, handwritten=True)

    result: dict = {
        'run_id': run_id,
        'generated_files': [str(prescription_pdf), str(lab_pdf), str(scanned_png), str(handwritten_png)],
        'docs': {},
        'api': {},
        'workflow': {},
        'frontend': {},
        'db': {},
    }

    with httpx.Client() as client:
        health = get_json(client, f'{BACKEND}/health')
        ready_resp = client.get(f'{BACKEND}/health/ready', timeout=30.0)
        ready: dict = {'http_status': ready_resp.status_code}
        try:
            ready.update(ready_resp.json())
        except ValueError:
            ready['body'] = ready_resp.text[:300]
        providers_cfg = get_json(client, f'{API}/providers/config')
        system_health = get_json(client, f'{API}/system/health')
        disclaimer = get_json(client, f'{API}/medical/disclaimer')

        result['api']['health'] = health
        result['api']['ready'] = ready
        result['api']['providers_config'] = providers_cfg
        result['api']['system_health'] = system_health
        result['api']['disclaimer'] = disclaimer

        record('backend health ok', health.get('status') == 'ok', str(health))
        record('backend ready endpoint reachable', ready_resp.status_code in (200, 503), str(ready))
        record('glm ocr enabled', providers_cfg.get('ocr_engine_flags', {}).get('glm_ocr') is True, str(providers_cfg.get('ocr_engine_flags')))
        record('gpu visible to backend', bool(system_health.get('gpu_available')), str(system_health.get('gpu_info')))

        uploaded = {
            'prescription': upload_doc(client, prescription_pdf, 'application/pdf'),
            'lab_report': upload_doc(client, lab_pdf, 'application/pdf'),
            'scanned_document': upload_doc(client, scanned_png, 'image/png'),
            'handwritten_note': upload_doc(client, handwritten_png, 'image/png'),
        }

        for kind, payload in uploaded.items():
            result['docs'][kind] = {'upload': payload}
            record(f'{kind} upload', bool(payload.get('id')), f"id={payload.get('id')}, type={payload.get('file_type')}")

        for kind, payload in uploaded.items():
            doc_id = payload['id']
            processed = process_doc(client, doc_id)
            ocr = []
            for _ in range(6):
                ocr = get_json(client, f'{API}/medical/documents/{doc_id}/ocr')
                if ocr:
                    break
                time.sleep(0.5)
            entities = get_json(client, f'{API}/medical/documents/{doc_id}/entities')
            meds = get_json(client, f'{API}/medical/documents/{doc_id}/medications')
            labs = get_json(client, f'{API}/medical/documents/{doc_id}/labs')
            result['docs'][kind].update({
                'process': processed,
                'ocr': ocr,
                'entities': entities,
                'medications': meds,
                'labs': labs,
            })
            record(f'{kind} process completed', processed.get('status') == 'completed', str(processed.get('error', 'ok')))

        doc_ids = [uploaded[k]['id'] for k in ('prescription', 'lab_report', 'scanned_document', 'handwritten_note')]

        presc_data = result['docs']['prescription']
        lab_data = result['docs']['lab_report']
        scan_data = result['docs']['scanned_document']
        hw_data = result['docs']['handwritten_note']

        presc_meds = presc_data['medications']
        lab_values = lab_data['labs']
        all_entities = sum(len(result['docs'][k]['entities']) for k in result['docs'])

        record('medical entity extraction', all_entities > 0, f'entities_total={all_entities}')
        record('medication extraction', len(presc_meds) > 0, f'prescription_medications={len(presc_meds)}')
        record('lab value extraction', len(lab_values) > 0, f'lab_results={len(lab_values)}')
        record(
            'lab out-of-range flagging',
            any(lab_item.get('is_out_of_range') is True for lab_item in lab_values),
            str(lab_values),
        )

        scan_ocr_text = '\n'.join((p.get('text') or '') for p in scan_data['ocr']).strip()
        hw_ocr_text = '\n'.join((p.get('text') or '') for p in hw_data['ocr']).strip()
        record('scanned document OCR', len(scan_ocr_text) > 20, f'chars={len(scan_ocr_text)}')
        record('handwritten note OCR (best effort)', len(hw_ocr_text) > 15, f'chars={len(hw_ocr_text)}')

        presc_blocks = sum(len((p.get('layout_json') or {}).get('blocks') or []) for p in presc_data['ocr'])
        lab_blocks = sum(len((p.get('layout_json') or {}).get('blocks') or []) for p in lab_data['ocr'])
        record('layout preservation for PDFs', (presc_blocks + lab_blocks) > 0, f'prescription_blocks={presc_blocks}, lab_blocks={lab_blocks}')

        search_payload = {
            'query': 'metformin and abnormal lab values',
            'top_k': 10,
            'document_ids': doc_ids,
        }
        search = post_json(client, f'{API}/search', search_payload)
        result['workflow']['search'] = search
        record('vector + hybrid search', len(search.get('results', [])) > 0, f"results={len(search.get('results', []))}")

        qa_payload = {
            'question': 'What medications are in my uploaded documents and which lab values are outside their reference ranges?',
            'document_ids': doc_ids,
            'top_k': 10,
        }
        qa = post_json(client, f'{API}/qa/query', qa_payload)
        result['workflow']['qa'] = qa
        record('grounded medical QA response', bool(qa.get('answer')), f"model={qa.get('model')}")
        record('QA citations/evidence linking', len(qa.get('citations', [])) > 0, f"citations={len(qa.get('citations', []))}")

        summary_payload = {
            'document_ids': doc_ids,
            'summary_type': 'plain',
            'length': 'medium',
        }
        summary = post_json(client, f'{API}/summaries', summary_payload)
        result['workflow']['summary'] = summary
        record('summaries generation', bool(summary.get('content')), f"citations={len(summary.get('citations', []))}")

        timeline_payload = {
            'document_ids': doc_ids,
            'event_types': [],
        }
        timeline = post_json(client, f'{API}/timelines', timeline_payload)
        result['workflow']['timeline'] = timeline
        record('timeline generation', len(timeline.get('events', [])) > 0, f"events={len(timeline.get('events', []))}")

        report_payload = {
            'document_ids': doc_ids,
            'title': 'Doctor Visit Preparation - Live Verification',
        }
        report = post_json(client, f'{API}/reports/generate', report_payload)
        report_export = get_json_with_retry(
            client,
            f"{API}/reports/{report['report_id']}/export",
            params={'format': 'markdown'},
        )
        result['workflow']['report'] = report
        result['workflow']['report_export'] = report_export
        record('doctor report generation', bool(report.get('markdown')), f"report_id={report.get('report_id')}")
        record('report export', bool(report_export.get('content')), f"format={report_export.get('format')}")

        disclaimer_text = str(disclaimer.get('disclaimer', ''))
        qa_disclaimer = 'Educational use only' in str(qa.get('answer', ''))
        safety_ok = (
            qa.get('safety', {}).get('educational_use_only') is True
            and summary.get('safety', {}).get('educational_use_only') is True
            and report.get('safety', {}).get('educational_use_only') is True
        )
        record('educational-only disclaimer endpoint', 'Educational use only' in disclaimer_text, disclaimer_text[:140])
        record('educational-only disclaimer in QA answer', qa_disclaimer, qa.get('answer', '')[:180])
        record('safety envelope enforced', safety_ok, json.dumps({'qa': qa.get('safety'), 'summary': summary.get('safety'), 'report': report.get('safety')}))

        result['workflow']['real_chain'] = {
            'document_id': uploaded['lab_report']['id'],
            'steps': {
                'upload': True,
                'process': lab_data['process'].get('status') == 'completed',
                'ocr_pages': len(lab_data['ocr']),
                'entities': len(lab_data['entities']),
                'retrieval_hits': len(search.get('results', [])),
                'qa_citations': len(qa.get('citations', [])),
                'summary_generated': bool(summary.get('content')),
                'timeline_events': len(timeline.get('events', [])),
                'report_id': report.get('report_id'),
            },
        }

        frontend_routes = [
            '/', '/upload-center', '/medical-documents', '/ai-chat', '/ocr-viewer', '/timeline',
            '/medication-history', '/laboratory-results', '/reports', '/search', '/memory',
            '/agent-activity', '/settings', '/model-manager', '/system-monitoring'
        ]
        fr = {}
        for route in frontend_routes:
            r = client.get(f'{FRONTEND}{route}', timeout=60.0)
            fr[route] = {'status_code': r.status_code, 'contains_title': 'Medical Document Intelligence Assistant' in r.text}
        result['frontend']['routes'] = fr
        record('frontend usability/routes', all(v['status_code'] == 200 and v['contains_title'] for v in fr.values()), json.dumps(fr))

    db_path = ROOT / 'e2e_live.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    ids = [result['docs'][k]['upload']['id'] for k in result['docs']]
    placeholders = ','.join('?' for _ in ids)

    def q1(sql: str, params: tuple):
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0]) if row else 0

    db_counts = {
        'documents': q1(f'SELECT COUNT(*) FROM documents WHERE id IN ({placeholders})', tuple(ids)),
        'ocr_pages': q1(f'SELECT COUNT(*) FROM ocr_pages WHERE document_id IN ({placeholders})', tuple(ids)),
        'entities': q1(f'SELECT COUNT(*) FROM medical_entities WHERE document_id IN ({placeholders})', tuple(ids)),
        'labs': q1(f'SELECT COUNT(*) FROM lab_results WHERE document_id IN ({placeholders})', tuple(ids)),
        'medications': q1(f'SELECT COUNT(*) FROM medication_history WHERE document_id IN ({placeholders})', tuple(ids)),
        'timeline_events': q1(f'SELECT COUNT(*) FROM timeline_events WHERE document_id IN ({placeholders})', tuple(ids)),
        'chunks': q1(f'SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({placeholders})', tuple(ids)),
        'embeddings_non_null': q1(
            f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({placeholders}) AND embedding IS NOT NULL",
            tuple(ids),
        ),
    }
    result['db']['counts'] = db_counts
    conn.close()

    record('database persistence', db_counts['documents'] == len(ids) and db_counts['ocr_pages'] > 0 and db_counts['chunks'] > 0, json.dumps(db_counts))
    record('vector store persistence', db_counts['embeddings_non_null'] > 0, json.dumps(db_counts))

    passed = sum(1 for c in checks if c.passed)
    failed = len(checks) - passed

    result['checks'] = [c.__dict__ for c in checks]
    result['summary'] = {
        'total': len(checks),
        'passed': passed,
        'failed': failed,
        'status': 'pass' if failed == 0 else 'fail',
    }

    OUT_JSON.write_text(json.dumps(result, indent=2), encoding='utf-8')

    lines = []
    lines.append('# Live Verification Report')
    lines.append('')
    lines.append(f"- Status: **{result['summary']['status'].upper()}**")
    lines.append(f"- Total checks: {len(checks)}")
    lines.append(f"- Passed: {passed}")
    lines.append(f"- Failed: {failed}")
    lines.append('')
    lines.append('## Checks')
    for c in checks:
        marker = 'PASS' if c.passed else 'FAIL'
        lines.append(f"- {marker}: {c.name} — {c.detail}")
    lines.append('')
    lines.append('## Safety')
    lines.append('- Educational-use disclaimer verified in endpoint and response behavior.')
    lines.append('- System is for document analysis and organization only; not diagnosis/treatment.')
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')

    print(json.dumps({'status': result['summary']['status'], 'passed': passed, 'failed': failed, 'artifact': str(OUT_JSON)}))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
