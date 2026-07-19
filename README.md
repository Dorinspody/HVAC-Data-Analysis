This project automates the collection of HVAC product information from manufacturer websites and technical specification PDFs.

It extracts product URLs and detailed technical parameters, including cooling capacity, electrical characteristics, refrigerant data, and equipment weight.

The project uses Python libraries such as Selenium, Requests, BeautifulSoup, pdfplumber, and Pandas.

procedure of Data analysis:

Discover categories: scrape daikincomfort.com/products for all /products/ links (requests + BeautifulSoup).
Expand into product pages: Selenium scrolls each category page and collects nested product links; leaf pages with no children are kept as products themselves.
Parse & scrape each product: split the URL into category levels + product slug, then fetch each page for its real name and Specification Sheet PDF link, using a scoped search that won't grab the wrong document.
Clean & save the catalog: dedupe products reachable via multiple category paths, flag suspicious links, and write product_specification_sheets.csv.
Extract each PDF's table: download each spec PDF, pick the largest table on the "Product Specifications" page.cells into clean rows.
Save per-product CSVs: drop black and duplicate rows, then write one CSV per product into product_csvs.
