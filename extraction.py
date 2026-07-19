import io
import os
import re
import requests
import pdfplumber
import pandas as pd


#data loading from website

INPUT_CSV = "product_specification_sheets.csv"
OUTPUT_FOLDER = "product_csvs"
os.makedirs(OUTPUT_FOLDER,exist_ok=True)


products_df = pd.read_csv(INPUT_CSV)# READ INPUT CSV
PDF_COLUMN = "specification_sheet_url"
headers = {"User-Agent":"Mozilla/5.0"}

def safe_filename(name):
    name = str(name)
    name = re.sub(r'[<>:"/\\|?*]',"_",name)
    return name.strip()

def extract_table_from_pdf(pdf_url):               #extract product specification table

    print(f"\nDownloading:\n{pdf_url}")
    response = requests.get(pdf_url,headers=headers,timeout=60)
    response.raise_for_status()
    pdf_file = io.BytesIO(response.content)


    tables_found = []


    with pdfplumber.open(pdf_file) as pdf:
        for page_number, page in enumerate(
            pdf.pages,
            start=1):
            text = page.extract_text() or ""
            if "Product Specifications" in text:
                print("Product Specifications found on page:",page_number)

                tables = page.extract_tables(
                    table_settings={
                        "text_y_tolerance": 1})

                for table in tables:
                    if table:
                        tables_found.append(table)

    if not tables_found:
        print("No table found")
        return None


# clean table
    table = tables_found[0]
    cleaned_table = []
    for row in table:
        cleaned_row = []
        for cell in row:
            if cell is None:
                cell = ""
            cell = "\n".join(
                line.strip()
                for line in cell.split("\n"))
            cleaned_row.append(cell)
        cleaned_table.append(cleaned_row)
    return cleaned_table

# CONVERT TABLE TO DATAFRAME
def convert_table_to_dataframe(table):
    models = [
        model.replace("\n","")
        for model in table[0][1:]]

    clean_data = []
    # Header
    clean_data.append(["Parameter"] + models)
    for row in table[1:]:
        if not row:
            continue
        parameter_text = row[0]
        parameters = parameter_text.split("\n")
        model_values = [value.split("\n")for value in row[1:]]
        # CATEGORY + PARAMETERS
        if len(parameters) > 1:
            clean_data.append(
                [parameters[0]]+[ ""]*len(models))

# Parameters

            for parameter_index, parameter in enumerate(parameters[1:]):
                values_for_models = []
                for model_value in model_values:
                    if parameter_index < len(model_value):
                        values_for_models.append(model_value[parameter_index])
                    else:
                        values_for_models.append("")
                clean_data.append(
                    [parameter]+values_for_models)


# NORMAL SINGLE PARAMETER ROW
        else:
            clean_data.append(
                [parameters[0]]+[values[0]
                    if len(values) > 0
                    else ""
                    for values in model_values])
    return pd.DataFrame(clean_data)

# PROCESS EVERY PDF IN INPUT CSV
for index, product in products_df.iterrows():
    print("\n")
    print("=" * 100)
    print(f"PRODUCT {index + 1} / {len(products_df)}")
    print("=" * 100)
    # GET PDF URL
    pdf_url = product[PDF_COLUMN]

    if pd.isna(pdf_url):
        print("PDF URL is empty")
        continue
    pdf_url = str(pdf_url).strip()
    # EXTRACT PDF TABLE
    try:
        table = extract_table_from_pdf(pdf_url)
        if table is None:
            continue

        # CONVERT TO DATAFRAME
        product_df = convert_table_to_dataframe(table)
        # CREATE OUTPUT PATH FROM CATEGORY + PRODUCT SLUG
        category_levels = [str(product.get(f"category_level_{level}", "")).strip()for level in range(1, 5)]
        category_levels = [

            c for c in category_levels

            if c and c.lower() != "nan"]

        category_folder = safe_filename(
        category_levels[-1]) if category_levels else ""
        product_slug = str(product.get("product_slug", "")).strip()
        if not product_slug or product_slug.lower() == "nan":

            pdf_filename = pdf_url.split("/")[-1]
            pdf_filename = pdf_filename.split("?")[0]
            pdf_filename = os.path.splitext(pdf_filename)[0]
            product_slug = safe_filename(pdf_filename)
        else:
            product_slug = safe_filename(product_slug)


        # OUTPUT FILE
        if category_folder:
            output_dir = os.path.join(OUTPUT_FOLDER,category_folder)
        else:
            output_dir = OUTPUT_FOLDER
        os.makedirs(output_dir,exist_ok=True)
        output_file = os.path.join(output_dir,f"{product_slug}.csv")



        # SAVE CSV
        product_df.to_csv(output_file,index=False,encoding="utf-8-sig")
        print(f"\nSaved:\n{output_file}")
    except Exception as error:
        print("\nERROR:")
        print(error)

print("\n")
print("=" * 100)
print("FINISHED")
print("=" * 100)
