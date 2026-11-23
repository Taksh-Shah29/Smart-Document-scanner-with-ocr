import unittest
import numpy as np
from scanner import perspective_transform, enhance_document, prepare_for_ocr, detect_document

class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.img=np.full((500,400,3),255,dtype=np.uint8)
    def test_transform(self):
        pts=np.array([[10,10],[390,10],[390,490],[10,490]],dtype=np.float32)
        out=perspective_transform(self.img,pts)
        self.assertGreater(out.shape[0],400); self.assertGreater(out.shape[1],300)
    def test_enhancement_modes(self):
        for mode in ["Color","Grayscale","Black & White"]:
            out=enhance_document(self.img,mode)
            self.assertEqual(out.shape,self.img.shape)
    def test_detection_output(self):
        result=detect_document(self.img)
        self.assertTrue(result is None or result.shape==(4,2))
    def test_ocr_preprocessing(self):
        out=prepare_for_ocr(self.img)
        self.assertEqual(out.dtype,np.uint8); self.assertEqual(out.ndim,2)

if __name__=="__main__": unittest.main()


class TestAIClassifier(unittest.TestCase):
    def test_invoice_classification(self):
        from ai_classifier import classify_document
        result = classify_document("TAX INVOICE Invoice No 123 GSTIN subtotal grand total")
        self.assertEqual(result["label"], "Invoice")
        self.assertGreater(result["confidence"], 0)

    def test_bank_statement_classification(self):
        from ai_classifier import classify_document
        result = classify_document("BANK STATEMENT opening balance closing balance debit credit")
        self.assertEqual(result["label"], "Bank Statement")

    def test_empty_text(self):
        from ai_classifier import classify_document
        self.assertEqual(classify_document("")["label"], "Unknown")
