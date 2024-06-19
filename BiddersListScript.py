import os
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch  # For specifying widths in inches
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
# Database connection parameters
config = {
    'user': os.getenv('db_userid'),
    'password': os.getenv('db_password'),
    'host': os.getenv('db_host'),
    'database': os.getenv('db_database'),
    'port': os.getenv('db_port')
}

# Connect to the database
conn = mysql.connector.connect(**config)
cursor = conn.cursor(dictionary=True)

# Set the timestamp to check
# Define advert_deadline
advert_deadline = '2024-05-24'
product_code = ['3.05.09']

# Convert advert_deadline to a datetime object
advert_deadline_dt = datetime.strptime(advert_deadline, '%Y-%m-%d')

# Calculate the next day at midnight
next_day_midnight = advert_deadline_dt + timedelta(days=1)
next_day_midnight_str = next_day_midnight.strftime('%Y-%m-%d 00:00:00')

check_timestamp = advert_deadline_dt + timedelta(hours=23, minutes=59, seconds=59)

# Convert product_code list to a string for the SQL query
product_code_str = ', '.join(f"'{code}'" for code in product_code)

# Retrieve the relevant data from the database
# 1. Retrieve all suppliers with the specified product code and date constraints
query_suppliers = f"""
SELECT sp.sup_id, sp.PROD_CODE, s.sup_name, s.SUP_Email, ss.date_expiration
FROM tblsupplierprodcode_prequal sp
JOIN tblsupplier s ON sp.sup_id = s.sup_id
JOIN tblsupplierstatus ss ON sp.sup_id = ss.sup_id
WHERE sp.PROD_CODE IN ({product_code_str})
  AND sp.date_addition < '{next_day_midnight_str}'
  AND ss.date_expiration >= '{advert_deadline}'
  ORDER BY s.sup_name ASC
"""
cursor.execute(query_suppliers)
suppliers = cursor.fetchall()

# Convert to the format 'YYYYMMDD'
formatted_date = advert_deadline_dt.strftime('%Y%m%d')

#convert from dictionary to tuple
suppliers = [(supplier['sup_id'], supplier['PROD_CODE'], supplier['sup_name'], supplier['SUP_Email'], supplier['date_expiration'].date() if isinstance(supplier['date_expiration'], datetime) else supplier['date_expiration'] ) for supplier in suppliers]


# 2. Retrieve the status log for all suppliers
query_status_log = """
SELECT SUP_ID, SUP_Status, date_update, date_expiration
FROM tblsupplierstatus_log
WHERE date_update <= %s
"""
# # Debugging step: print the query and parameter
# print("Executing query:", query_status_log)
# print("With parameter:", check_timestamp)

cursor.execute(query_status_log, (check_timestamp,))
status_logs = cursor.fetchall()



#convert from dictionary to tuple
status_logs = [(log['SUP_ID'], log['SUP_Status'], log['date_update'], log['date_expiration']) for log in status_logs]

# Close the database connection
conn.close()

title = f"NipeX Prequalified Suppliers List for {product_code[0]} as at {formatted_date}"
# Process the status logs to determine if a supplier was live at the given timestamp

def is_supplier_live(sup_id, check_timestamp, status_logs):
   

    # Filter logs for the given supplier
    logs = [log for log in status_logs if log[0] == sup_id]

    # print(f"Checking supplier ID {sup_id}")
    # print(f"Logs for supplier {sup_id}: {logs}")

    # Sort logs by date_update descending
    logs.sort(key=lambda x: x[2], reverse=True)
    for log in logs:
        # if log[3] >= check_timestamp.date():  # date_expiration is after the check date
        #     return log[1] == 'LIVE'
        # if log[2] <= check_timestamp:  # date_update is before or at the check date
        #     return log[1] == 'LIVE'
         # Check if both conditions are true



        if log[3] >= check_timestamp.date():
            return True
    return False
# sup1='12508'
# print(f'{is_supplier_live(sup1, check_timestamp, status_logs)}')
#Filter suppliers to find those who are currently 'LIVE'
live_suppliers = [
    (sup_id, sup_name, prod_code, date_expiration, sup_email)
    for sup_id, prod_code, sup_name, sup_email, date_expiration in suppliers
    if is_supplier_live(sup_id, check_timestamp, status_logs)
]
live_suppliers = [(i + 1, *supplier) for i, supplier in enumerate(live_suppliers)]

# # is_supplier_in_list = any(supplier[1] == '12508' for supplier in live_suppliers)
# print(f"Supplier 12508 in suppliers list: {is_supplier_in_list}")


# Convert the result to a DataFrame
df = pd.DataFrame(live_suppliers, columns=['SN','Supplier ID', 'Name', 'Product Code', 'Expiration Date', 'Email'])
# Write DataFrame to Excel with a header

# Output the result to an Excel file
output_file = f"NipeX Prequalified Suppliers List for {product_code[0]} as at {formatted_date}.xlsx"

with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Sheet1', index=False, startrow=1)

    # Access the XlsxWriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['Sheet1']

    # Write the title at the top of the sheet
    worksheet.write(0, 0, title)

print(f"Output written to {output_file}")

# # Define the PDF header and footer
# def add_page_number(canvas, doc):
#     page_num = canvas.getPageNumber()
#     text = f"Page {page_num}"
#     canvas.drawRightString(200 * mm, 15 * mm, text)

# #generate pdf file
# def create_supplier_pdf(pdf_path, live_suppliers):
    
#     doc = SimpleDocTemplate(pdf_path, pagesize=letter)
#     elements = []
    
#     # Add the title
#     styles = getSampleStyleSheet()
#     title_style = ParagraphStyle(
#         'title',
#         fontName='Helvetica-Bold',
#         fontSize=12,
#         leading=14,
#         alignment=1,
#         spaceAfter=12
#     )
#     title_para = Paragraph(title, title_style)
#     elements.append(title_para)
#     elements.append(Spacer(1, 12))

#     table_data = [('SN','Supplier ID', 'Name', 'Product Code', 'Expiration Date', 'Email')] + live_suppliers

#     # Define table style to mimic the image
#     style = TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.skyblue),  # Light blue header
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Black header text
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Center alignment
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Bold header
#         ('FONTSIZE', (0, 0), (-1, -1), 5),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
#         ('GRID', (0, 0), (-1, -1), 1, colors.black)
#     ])

#     # Adjust column widths (optional)
#     col_widths = [
#         0.5 * inch,  # S/N
#         0.5 * inch,  # Supplier ID
#         2.5 * inch,  # Supplier Name
#         1 * inch,    # Product Code
#         1 * inch,    # Expiration
#         2 * inch     # Supplier Email
#     ]

#     row_heights = 0.2 * inch
#     # Create the table
#     table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)  # Apply column widths (optional)
    

#     # Add alternating row colors
#     for i in range(1, len(table_data)):
#         bg_color = colors.lightblue if i % 2 == 0 else colors.whitesmoke
#         style.add('BACKGROUND', (0, i), (-1, i), bg_color)

#         table.setStyle(style)

#     elements.append(table)
#     elements.append(PageBreak())
#     doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)



# # Generate the PDF
# pdf_filename = f"{title}.pdf"
# create_supplier_pdf(pdf_filename, live_suppliers)

# print(f"PDF report '{pdf_filename}' generated successfully!")
    

# Export the necessary variables and functions for other scripts
__all__ = ['config', 'live_suppliers']