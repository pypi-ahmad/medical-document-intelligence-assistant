# Live Verification Report

- Status: **PASS**
- Total checks: 32
- Passed: 32
- Failed: 0

## Checks
- PASS: backend health ok — {'status': 'ok'}
- PASS: backend ready endpoint reachable — {'http_status': 503, 'status': 'degraded', 'checks': {'llm_providers': {'ok': False, 'ready': 0}, 'ocr_providers': {'ok': True, 'ready': 2}, 'ollama_url_safe': {'ok': True}}}
- PASS: glm ocr enabled — {'paddleocr': False, 'glm_ocr': True}
- PASS: gpu visible to backend — {'available': True, 'name': 'NVIDIA GeForce RTX 4060 Laptop GPU', 'driver_version': '595.71.05', 'cuda_version': '13.2', 'memory_total_mib': 8188, 'memory_used_mib': 6775, 'utilization_gpu_percent': 6}
- PASS: prescription upload — id=edfc9145449e43e2bde7834e988f5a61, type=pdf
- PASS: lab_report upload — id=6f67d3d746a942789e3f0fd879333094, type=pdf
- PASS: scanned_document upload — id=25c0a4ac2dc9456d8dc745dd0e57a8bb, type=png
- PASS: handwritten_note upload — id=9da32c482d20436cb307dbf3d9e61c49, type=png
- PASS: prescription process completed — ok
- PASS: lab_report process completed — ok
- PASS: scanned_document process completed — ok
- PASS: handwritten_note process completed — ok
- PASS: medical entity extraction — entities_total=79
- PASS: medication extraction — prescription_medications=3
- PASS: lab value extraction — lab_results=6
- PASS: lab out-of-range flagging — [{'test_name': 'hemoglobin', 'value_text': '10.8', 'unit': 'g/dL', 'reference_range': '13.0-17.0', 'is_out_of_range': True, 'event_date': '2026-06-25', 'page_number': 1}, {'test_name': 'white blood cell count', 'value_text': '12.2', 'unit': 'K/uL', 'reference_range': '4.0-11.0', 'is_out_of_range': True, 'event_date': '2026-06-25', 'page_number': 1}, {'test_name': 'creatinine', 'value_text': '1.4', 'unit': 'mg/dL', 'reference_range': '0.7-1.3', 'is_out_of_range': True, 'event_date': '2026-06-25', 'page_number': 1}, {'test_name': 'glucose', 'value_text': '168', 'unit': 'mg/dL', 'reference_range': '70-99', 'is_out_of_range': True, 'event_date': '2026-06-25', 'page_number': 1}, {'test_name': 'sodium', 'value_text': '138', 'unit': 'mmol/L', 'reference_range': '135-145', 'is_out_of_range': False, 'event_date': '2026-06-25', 'page_number': 1}, {'test_name': 'potassium', 'value_text': '4.6', 'unit': 'mmol/L', 'reference_range': '3.5-5.1', 'is_out_of_range': False, 'event_date': '2026-06-25', 'page_number': 1}]
- PASS: scanned document OCR — chars=181
- PASS: handwritten note OCR (best effort) — chars=1705
- PASS: layout preservation for PDFs — prescription_blocks=3, lab_blocks=2
- PASS: vector + hybrid search — results=1
- PASS: grounded medical QA response — model=qwen3.5:4b
- PASS: QA citations/evidence linking — citations=1
- PASS: summaries generation — citations=0
- PASS: timeline generation — events=47
- PASS: doctor report generation — report_id=4a99226da0014312bc359342b4dc2ece
- PASS: report export — format=markdown
- PASS: educational-only disclaimer endpoint — Educational use only. This assistant organizes and explains uploaded documents, but does not diagnose conditions, recommend treatments, pres
- PASS: educational-only disclaimer in QA answer — Extracted Information From Uploaded Documents:
City Care Medical Center Prescription Patient Name: Ahmad Khan Patient ID: MRN-88421 Age: 34 Sex: Male Visit Date: 2026-06-21 Doctor:
- PASS: safety envelope enforced — {"qa": {"disclaimer": "Educational use only. This assistant organizes and explains uploaded documents, but does not diagnose conditions, recommend treatments, prescribe medication, or replace licensed healthcare professionals.", "educational_use_only": true, "prohibited_actions": ["No diagnosis", "No treatment recommendation", "No medication prescribing", "Not a substitute for licensed clinicians"]}, "summary": {"disclaimer": "Educational use only. This assistant organizes and explains uploaded documents, but does not diagnose conditions, recommend treatments, prescribe medication, or replace licensed healthcare professionals.", "educational_use_only": true, "prohibited_actions": ["No diagnosis", "No treatment recommendation", "No medication prescribing", "Not a substitute for licensed clinicians"]}, "report": {"disclaimer": "Educational use only. This assistant organizes and explains uploaded documents, but does not diagnose conditions, recommend treatments, prescribe medication, or replace licensed healthcare professionals.", "educational_use_only": true, "prohibited_actions": ["No diagnosis", "No treatment recommendation", "No medication prescribing", "Not a substitute for licensed clinicians"]}}
- PASS: frontend usability/routes — {"/": {"status_code": 200, "contains_title": true}, "/upload-center": {"status_code": 200, "contains_title": true}, "/medical-documents": {"status_code": 200, "contains_title": true}, "/ai-chat": {"status_code": 200, "contains_title": true}, "/ocr-viewer": {"status_code": 200, "contains_title": true}, "/timeline": {"status_code": 200, "contains_title": true}, "/medication-history": {"status_code": 200, "contains_title": true}, "/laboratory-results": {"status_code": 200, "contains_title": true}, "/reports": {"status_code": 200, "contains_title": true}, "/search": {"status_code": 200, "contains_title": true}, "/memory": {"status_code": 200, "contains_title": true}, "/agent-activity": {"status_code": 200, "contains_title": true}, "/settings": {"status_code": 200, "contains_title": true}, "/model-manager": {"status_code": 200, "contains_title": true}, "/system-monitoring": {"status_code": 200, "contains_title": true}}
- PASS: database persistence — {"documents": 4, "ocr_pages": 4, "entities": 79, "labs": 6, "medications": 17, "timeline_events": 47, "chunks": 5, "embeddings_non_null": 5}
- PASS: vector store persistence — {"documents": 4, "ocr_pages": 4, "entities": 79, "labs": 6, "medications": 17, "timeline_events": 47, "chunks": 5, "embeddings_non_null": 5}

## Safety
- Educational-use disclaimer verified in endpoint and response behavior.
- System is for document analysis and organization only; not diagnosis/treatment.