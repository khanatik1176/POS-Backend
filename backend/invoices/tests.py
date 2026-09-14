from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .mobile_money_field_mapping import extract_fields as extract_mobile_money_fields

User = get_user_model()


class MobileMoneyFieldMappingTests(TestCase):
    def test_history_list_layout(self):
        lines = [
            'Send Money', '01966033384', '- ৳300.00', '06:20pm 10/09/26', 'TrxID : DIA1D1BOVB',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertEqual(result['transaction_id']['value'], 'DIA1D1BOVB')
        self.assertEqual(result['phone_number']['value'], '01966033384')
        self.assertEqual(result['transaction_datetime']['value'], '10/09/26 06:20pm')
        self.assertEqual(result['amount']['value'], '300.00')

    def test_english_success_page_table_layout(self):
        lines = [
            'Send Money Successful', '01966-033384', 'Transaction ID   75YVHC5A',
            'Amount   300 Tk.', 'Charge   5 Tk.', 'Total   305 Tk.',
            'Time   10 September 2026, 06:13 PM',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertEqual(result['transaction_id']['value'], '75YVHC5A')
        self.assertEqual(result['amount']['value'], '300')
        self.assertEqual(result['charge']['value'], '5')
        self.assertEqual(result['total_amount']['value'], '305')
        self.assertEqual(result['transaction_datetime']['value'], '10 September 2026, 06:13 PM')

    def test_no_charge_and_recipient_name(self):
        lines = [
            'Your Send Money is successful', 'Monimul', '01748513313', 'Call',
            'Time  06:40pm 10/09/26', 'Transaction ID  DIA4D27AF2',
            'Total  ৳300.00', '+ No charge', 'Reference',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertEqual(result['charge']['value'], '0')
        self.assertEqual(result['total_amount']['value'], '300.00')
        self.assertEqual(result['transaction_datetime']['value'], '10/09/26 06:40pm')
        self.assertEqual(result['reference_name']['value'], 'Monimul')
        self.assertEqual(result['transaction_id']['value'], 'DIA4D27AF2')

    def test_bengali_stacked_label_layout(self):
        lines = [
            'সেন্ড মানি', 'Netflix Soykon', '01748513313', 'সময়', '07:26pm 19/08/26',
            'ট্রানজেকশন আইডি', 'DHJ4LVGD1C', 'পরিমাণ', '৳480.00', 'রেফারেন্স',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertEqual(result['transaction_id']['value'], 'DHJ4LVGD1C')
        self.assertEqual(result['transaction_datetime']['value'], '19/08/26 07:26pm')
        self.assertEqual(result['amount']['value'], '480.00')
        self.assertEqual(result['reference_name']['value'], 'Netflix Soykon')

    def test_bengali_popup_table_layout(self):
        lines = [
            'ইনবক্স', 'সেন্ড মানি', '-৳480.00', '01966033384', '11:49am 09/07/26',
            'একাউন্ট', '01966033384', 'সময়', '11:49am 09/07/26', 'পরিমাণ', '৳480.00',
            'চার্জ', '৳5.00', 'ট্রানজেকশন আইডি', 'DG907FG2PK', 'রেফারেন্স', 'Nafisha', 'শেয়ার',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertEqual(result['transaction_id']['value'], 'DG907FG2PK')
        self.assertEqual(result['transaction_datetime']['value'], '09/07/26 11:49am')
        self.assertEqual(result['charge']['value'], '5.00')
        self.assertEqual(result['reference_name']['value'], 'Nafisha')

    def test_garbled_trxid_label_and_unlabeled_fallback(self):
        # OCR commonly turns "TrxID" into "TrxlD"; bare IDs without a label
        # must still be recovered from the history-list layout.
        garbled = extract_mobile_money_fields([
            {'text': t, 'confidence': 90} for t in ['Send Money', '01966033384', 'TrxlD : DIA1D1BOVB']
        ])
        self.assertEqual(garbled['transaction_id']['value'], 'DIA1D1BOVB')

        bare = extract_mobile_money_fields([
            {'text': t, 'confidence': 44} for t in ['Send Money', '01966033384', 'DIA1D1BOVB']
        ])
        self.assertEqual(bare['transaction_id']['value'], 'DIA1D1BOVB')
        # Pattern-validated IDs are boosted above the UI threshold.
        self.assertGreaterEqual(bare['transaction_id']['confidence'], 75)

    def test_stacked_value_keeps_label_confidence(self):
        lines = [
            {'text': 'ট্রানজেকশন আইডি', 'confidence': 92},
            {'text': 'DHJ4LVGD1C', 'confidence': 55},
        ]
        result = extract_mobile_money_fields(lines)
        self.assertEqual(result['transaction_id']['value'], 'DHJ4LVGD1C')
        self.assertGreaterEqual(result['transaction_id']['confidence'], 92)

    def test_bengali_popup_shared_value_row_reads_reference(self):
        # Upscaled OCR of the Bengali bottom-sheet often merges TrxID +
        # Reference onto one value row under a shared label row.
        lines = [
            'একাউন্ট সময়', '01966033384 11:49am 09/07/26',
            'পরিমাণ চার্জ', '%480.00 %5.00',
            'ট্রানজেকশন আইডি রেফারেন্স', 'DG907FG2PK [Fj Nafisha',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 80} for t in lines])
        self.assertEqual(result['transaction_id']['value'], 'DG907FG2PK')
        self.assertEqual(result['reference_name']['value'], 'Nafisha')
        self.assertEqual(result['amount']['value'], '480.00')
        self.assertEqual(result['charge']['value'], '5.00')
        self.assertEqual(result['transaction_datetime']['value'], '09/07/26 11:49am')

    def test_reference_strips_copy_icon_ocr_junk(self):
        result = extract_mobile_money_fields([
            {'text': 'ট্রানজেকশন আইডি রেফারেন্স', 'confidence': 80},
            {'text': 'DG907FG2PK [Fj Nafisha', 'confidence': 74},
        ])
        self.assertEqual(result['transaction_id']['value'], 'DG907FG2PK')
        self.assertEqual(result['reference_name']['value'], 'Nafisha')

    def test_taka_symbol_misread_as_leading_digit(self):
        result = extract_mobile_money_fields([
            {'text': 'পরিমাণ', 'confidence': 90},
            {'text': '6480.00', 'confidence': 72},
        ])
        self.assertEqual(result['amount']['value'], '480.00')

    def test_bengali_success_grid_reads_id_beside_datetime(self):
        lines = [
            'সেন্ড মানি', 'Netflix Soykon', '01748513313',
            'সময় ট্রানজেকশন আইডি', '07:26pm 19/08/26 DHJ4LVGD1C',
            'পরিমাণ রেফারেন্স', '%480.00',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertEqual(result['transaction_id']['value'], 'DHJ4LVGD1C')
        self.assertEqual(result['transaction_datetime']['value'], '19/08/26 07:26pm')
        self.assertEqual(result['amount']['value'], '480.00')
        self.assertEqual(result['reference_name']['value'], 'Netflix Soykon')

    def test_reference_does_not_leak_a_merged_neighbouring_label(self):
        # A tight two-column grid can get OCR-merged onto one line, pairing
        # a blank "Reference" cell with a neighbouring row's label (e.g.
        # "Transaction ID"). The leftover label text must not be mistaken
        # for the reference value.
        lines = [
            'ট্রানজেকশন আইডি', 'DIAID1BOVB', '01748513313',
            'Amount   300', 'Charge   0', 'Total   305',
            'Time   10 September 2026, 06:13 PM',
            'রেফারেন্স ট্রানজেকশন আইডি',
        ]
        result = extract_mobile_money_fields([{'text': t, 'confidence': 90} for t in lines])
        self.assertNotIn('reference_name', result)
        self.assertEqual(result['transaction_id']['value'], 'DIAID1BOVB')


class InvoiceRecordApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='api_test_user', password='irrelevant-for-test', email='api_test_user@example.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_field_template_endpoint_returns_both_types(self):
        response = self.client.get('/api/invoices/field-template/')
        self.assertEqual(response.status_code, 200)
        templates = response.data['templates']
        self.assertIn('invoice', templates)
        self.assertIn('mobile_money_receipt', templates)
        mobile_money_keys = {item['key'] for item in templates['mobile_money_receipt']}
        self.assertEqual(
            mobile_money_keys,
            {'transaction_id', 'phone_number', 'transaction_datetime', 'amount', 'charge', 'total_amount', 'reference_name'},
        )

    def test_create_mobile_money_receipt_record(self):
        payload = {
            'record_type': 'mobile_money_receipt',
            'fields': {
                'transaction_id': {'value': 'DG907FG2PK', 'origin': 'auto', 'confidence': 91},
                'phone_number': {'value': '01966033384', 'origin': 'auto', 'confidence': 91},
                'amount': {'value': '480.00', 'origin': 'auto', 'confidence': 91},
            },
            'images': [],
        }
        response = self.client.post('/api/invoices/records/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['record_type'], 'mobile_money_receipt')
        self.assertEqual(response.data['fields']['transaction_id']['value'], 'DG907FG2PK')
        self.assertEqual(response.data['fields']['reference_name']['value'], '')

    def test_create_invoice_record_still_works(self):
        payload = {
            'record_type': 'invoice',
            'fields': {
                'vendor_name': {'value': 'Acme Corp', 'origin': 'manual'},
            },
            'images': [],
        }
        response = self.client.post('/api/invoices/records/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['record_type'], 'invoice')
        self.assertEqual(response.data['fields']['vendor_name']['value'], 'Acme Corp')

    def test_mobile_money_fields_rejected_on_invoice_type(self):
        payload = {
            'record_type': 'invoice',
            'fields': {
                'transaction_id': {'value': 'DG907FG2PK', 'origin': 'auto'},
            },
            'images': [],
        }
        response = self.client.post('/api/invoices/records/', payload, format='json')
        self.assertEqual(response.status_code, 400)
