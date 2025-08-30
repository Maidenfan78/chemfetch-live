from pathlib import Path
import sys

# Ensure project root is on the import path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from ocr_service.sds_parser_new.sds_extractor import parse_pdf


def test_scanned_sds_parsing():
    pdf_path = Path("test-data/sds-pdfs/sds_4.pdf")
    result = parse_pdf(pdf_path)

    assert result["product_name"]["value"] == "Armor All Original Protectant - Spray"
    assert result["manufacturer"]["value"] == "Energizer Manufacturing, Inc."
    assert result["dangerous_goods_class"]["value"] == "Not subject to transport regulations: UN RTDG"
    assert result["packing_group"]["value"] == "not assigned"
    assert result["issue_date"]["value"] == "2011-09-03"
