This project automates the collection of HVAC product information from manufacturer websites and technical specification PDFs.

It extracts product URLs and detailed technical parameters, including cooling capacity, electrical characteristics, refrigerant data, and equipment weight.

The project uses Python libraries such as Selenium, Requests, BeautifulSoup, pdfplumber, and Pandas.



procedure of Data analysis:

1-Discover product categories

Scrape daikincomfort.com/products with Requests and BeautifulSoup to identify all available product category links.

2-Explore nested product pages

Use Selenium to scroll through category pages and collect nested product links. Leaf pages without child products are treated as individual products.

3-Scrape product information

Parse each URL into its category hierarchy and product slug. Then fetch each product page with retry handling to extract the official product name and the relevant Specification Sheet PDF link using a scoped search strategy.

4-Clean and build the product catalog

Remove duplicate products that appear through multiple category paths, flag suspicious non-.pdf links, and save the resulting catalog to product_specification_sheets.csv.

5-Extract specification tables from PDFs

Download each Specification Sheet PDF with caching to avoid repeated requests. On the Product Specifications page, identify the largest table and split multi-line category and parameter cells into clean, structured rows.

6-Save product-level datasets

Remove blank and duplicate rows, then export one cleaned CSV file per product to:
product_csvs





